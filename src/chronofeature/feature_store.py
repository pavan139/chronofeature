"""Indexed ASOF feature computation with explicit event and availability clocks."""

from bisect import bisect_right
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import sqlite3


class FeatureError(ValueError):
    pass


class InjectedCrash(RuntimeError):
    pass


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def identifier(value):
    try:
        return isinstance(value, str) and 1 <= len(value.encode("utf-8")) <= 128 and "\x00" not in value
    except UnicodeError:
        return False


def clock(value):
    return type(value) is int and 0 <= value <= 10**12


@dataclass(frozen=True)
class Event:
    event_id: str
    entity: str
    event_time: int
    observed_at: int
    value: int | None
    revision: int = 0
    deleted: bool = False

    def __post_init__(self):
        if (
            not identifier(self.event_id)
            or not identifier(self.entity)
            or not clock(self.event_time)
            or not clock(self.observed_at)
            or self.observed_at < self.event_time
        ):
            raise FeatureError("Bounded identifiers and ordered event/observation clocks required")
        if type(self.revision) is not int or not 0 <= self.revision <= 100000 or type(self.deleted) is not bool:
            raise FeatureError("Invalid revision/tombstone")
        if self.deleted:
            if self.value is not None:
                raise FeatureError("Tombstones have no value")
        elif type(self.value) is not int or abs(self.value) > 10**9:
            raise FeatureError("Feature values are bounded exact integers")


@dataclass(frozen=True)
class Spec:
    name: str = "transactions"
    version: int = 1
    windows: tuple[int, ...] = (10, 30)
    ttl: int = 20

    def __post_init__(self):
        if not identifier(self.name) or type(self.version) is not int or not 1 <= self.version <= 1000:
            raise FeatureError("Invalid feature identity/version")
        if (
            not isinstance(self.windows, tuple)
            or not 1 <= len(self.windows) <= 16
            or any(type(w) is not int or not 1 <= w <= 1000000 for w in self.windows)
            or tuple(sorted(set(self.windows))) != self.windows
        ):
            raise FeatureError("Windows must be 1..16 sorted unique durations in [1,1000000]")
        if type(self.ttl) is not int or not 1 <= self.ttl <= 1000000:
            raise FeatureError("TTL must be an integer in [1,1000000]")


@dataclass(frozen=True)
class Query:
    entity: str
    label_time: int
    observation_cutoff: int | None = None

    def __post_init__(self):
        if not identifier(self.entity) or not clock(self.label_time):
            raise FeatureError("Invalid query entity/time")
        if self.observation_cutoff is not None and (
            not clock(self.observation_cutoff) or self.observation_cutoff > self.label_time
        ):
            raise FeatureError("Observation cutoff cannot exceed decision/label time")

    @property
    def cutoff(self):
        return self.label_time if self.observation_cutoff is None else self.observation_cutoff


@dataclass(frozen=True)
class Label:
    label_id: str
    entity: str
    label_time: int
    target: int

    def __post_init__(self):
        Query(self.entity, self.label_time)
        if not identifier(self.label_id) or type(self.target) is not int or abs(self.target) > 10**9:
            raise FeatureError("Invalid label id/target")


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


class FeatureStore:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value INTEGER NOT NULL);
                INSERT OR IGNORE INTO metadata VALUES('generation',0);
                CREATE TABLE IF NOT EXISTS events(event_id TEXT,revision INTEGER,entity TEXT,event_time INTEGER,observed_at INTEGER,value INTEGER,deleted INTEGER,event_hash TEXT,generation INTEGER,PRIMARY KEY(event_id,revision));
                CREATE INDEX IF NOT EXISTS entity_time ON events(entity,event_time,observed_at,event_id,revision);
                CREATE TABLE IF NOT EXISTS specs(name TEXT,version INTEGER,body TEXT NOT NULL,PRIMARY KEY(name,version));
                CREATE TABLE IF NOT EXISTS versions(version_id TEXT PRIMARY KEY,spec_name TEXT,spec_version INTEGER,body TEXT NOT NULL,input_hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS online(version_id TEXT,entity TEXT,body TEXT NOT NULL,PRIMARY KEY(version_id,entity));
                CREATE TABLE IF NOT EXISTS active(spec_name TEXT PRIMARY KEY,version_id TEXT NOT NULL);
            """)

    def connect(self):
        connection = sqlite3.connect(self.path, timeout=5, factory=ClosingConnection)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    def ingest(self, events):
        if (
            not isinstance(events, (list, tuple))
            or not 1 <= len(events) <= 2048
            or not all(isinstance(event, Event) for event in events)
        ):
            raise FeatureError("Ingest requires 1..2048 typed events")
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            generation = connection.execute("SELECT value FROM metadata WHERE key='generation'").fetchone()[0] + 1
            inserted = duplicates = 0
            for event in events:
                fingerprint = digest(asdict(event))
                old = connection.execute(
                    "SELECT event_hash FROM events WHERE event_id=? AND revision=?", (event.event_id, event.revision)
                ).fetchone()
                if old:
                    if old[0] != fingerprint:
                        raise FeatureError("Conflicting payload for immutable event revision")
                    duplicates += 1
                    continue
                identity = connection.execute(
                    "SELECT entity,event_time FROM events WHERE event_id=? LIMIT 1", (event.event_id,)
                ).fetchone()
                if identity and identity != (event.entity, event.event_time):
                    raise FeatureError("An event's entity/time identity cannot change across revisions")
                connection.execute(
                    "INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        event.event_id,
                        event.revision,
                        event.entity,
                        event.event_time,
                        event.observed_at,
                        event.value,
                        int(event.deleted),
                        fingerprint,
                        generation,
                    ),
                )
                inserted += 1
            if connection.execute("SELECT count(*) FROM events").fetchone()[0] > 100000:
                raise FeatureError("Store exceeds 100000-revision experiment budget")
            if inserted:
                connection.execute("UPDATE metadata SET value=? WHERE key='generation'", (generation,))
            else:
                generation -= 1
            return {"inserted": inserted, "duplicates": duplicates, "generation": generation}

    @staticmethod
    def _register(connection, spec):
        if not isinstance(spec, Spec):
            raise FeatureError("Typed feature specification required")
        body = encoded(asdict(spec))
        previous = connection.execute(
            "SELECT body FROM specs WHERE name=? AND version=?", (spec.name, spec.version)
        ).fetchone()
        if previous and previous[0] != body:
            raise FeatureError("Feature version identity cannot be redefined")
        connection.execute("INSERT OR IGNORE INTO specs VALUES(?,?,?)", (spec.name, spec.version, body))

    @staticmethod
    def _generation(connection, requested=None):
        head = connection.execute("SELECT value FROM metadata WHERE key='generation'").fetchone()[0]
        if requested is None:
            return head
        if type(requested) is not int or not 0 <= requested <= head:
            raise FeatureError("Source generation must be an existing nonnegative snapshot")
        return requested

    def _query(self, connection, query, spec, source_generation=None):
        if not isinstance(query, Query) or not isinstance(spec, Spec):
            raise FeatureError("Typed query and feature specification required")
        generation = self._generation(connection, source_generation)
        rows = connection.execute(
            """
            WITH known AS (
              SELECT event_id,event_time,value,deleted,
                     ROW_NUMBER() OVER(PARTITION BY event_id ORDER BY revision DESC) AS position
              FROM events
              WHERE entity=? AND event_time>? AND event_time<=? AND observed_at<=? AND generation<=?
            ) SELECT event_id,event_time,value FROM known WHERE position=1 AND deleted=0 ORDER BY event_time,event_id
        """,
            (query.entity, query.label_time - max(spec.windows), query.label_time, query.cutoff, generation),
        ).fetchall()
        times = [row[1] for row in rows]
        prefix = [0]
        for _, _, value in rows:
            prefix.append(prefix[-1] + value)
        windows = {}
        for duration in spec.windows:
            start = bisect_right(times, query.label_time - duration)
            count = len(rows) - start
            if not count:
                windows[str(duration)] = {
                    "count": 0,
                    "sum": 0,
                    "mean": None,
                    "last": None,
                    "last_event_time": None,
                    "status": "missing",
                    "valid_before": query.label_time + spec.ttl + 1,
                }
                continue
            last_time, latest_value = rows[-1][1], rows[-1][2]
            valid_before = min(last_time + spec.ttl + 1, rows[start][1] + duration)
            fresh = query.label_time - last_time <= spec.ttl
            total = prefix[-1] - prefix[start]
            windows[str(duration)] = {
                "count": count if fresh else None,
                "sum": total if fresh else None,
                "mean": total / count if fresh else None,
                "last": latest_value if fresh else None,
                "last_event_time": last_time,
                "status": "fresh" if fresh else "stale",
                "valid_before": valid_before,
            }
        return {
            "entity": query.entity,
            "feature_time": query.label_time,
            "observation_cutoff": query.cutoff,
            "source_generation": generation,
            "spec_name": spec.name,
            "spec_version": spec.version,
            "spec_sha256": digest(asdict(spec)),
            "windows": windows,
        }

    def query(self, query, spec=Spec(), *, source_generation=None):
        with self.connect() as connection:
            self._register(connection, spec)
            connection.commit()
            connection.execute("BEGIN")
            return self._query(connection, query, spec, source_generation)

    def offline_join(self, labels, spec=Spec(), *, source_generation=None):
        if (
            not isinstance(labels, (list, tuple))
            or not 1 <= len(labels) <= 2048
            or not all(isinstance(label, Label) for label in labels)
        ):
            raise FeatureError("Offline join requires 1..2048 typed labels")
        if len({label.label_id for label in labels}) != len(labels):
            raise FeatureError("Label IDs must be unique")
        with self.connect() as connection:
            self._register(connection, spec)
            connection.commit()
            connection.execute("BEGIN")
            generation = self._generation(connection, source_generation)
            cache, rows = {}, []
            for label in labels:
                key = (label.entity, label.label_time)
                if key not in cache:
                    cache[key] = self._query(connection, Query(*key), spec, generation)
                rows.append(
                    {"label_id": label.label_id, "target": label.target, "features": json.loads(encoded(cache[key]))}
                )
            return {"source_generation": generation, "count": len(rows), "rows": rows}

    def materialize(
        self, version_id, entities, as_of, spec=Spec(), *, observation_cutoff=None, crash_before_commit=False
    ):
        if not isinstance(spec, Spec):
            raise FeatureError("Typed feature specification required")
        if (
            not identifier(version_id)
            or not isinstance(entities, (list, tuple))
            or not 1 <= len(entities) <= 2048
            or any(not identifier(value) for value in entities)
            or len(set(entities)) != len(entities)
        ):
            raise FeatureError("Unique bounded materialization identity/entities required")
        Query(entities[0], as_of, observation_cutoff)
        request = {"entities": sorted(entities), "as_of": as_of, "cutoff": observation_cutoff, "spec": asdict(spec)}
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._register(connection, spec)
            old = connection.execute(
                "SELECT body,input_hash FROM versions WHERE version_id=?", (version_id,)
            ).fetchone()
            if old:
                if old[1] != digest(request):
                    raise FeatureError("Immutable materialization version reused with different inputs")
                return {**json.loads(old[0]), "replayed": True}
            generation = self._generation(connection)
            metadata = {
                "version_id": version_id,
                "feature_time": as_of,
                "observation_cutoff": as_of if observation_cutoff is None else observation_cutoff,
                "source_generation": generation,
                "spec_name": spec.name,
                "spec_version": spec.version,
                "spec_sha256": digest(asdict(spec)),
                "entity_count": len(entities),
                "replayed": False,
            }
            for entity in sorted(entities):
                body = self._query(connection, Query(entity, as_of, observation_cutoff), spec, generation)
                connection.execute("INSERT INTO online VALUES(?,?,?)", (version_id, entity, encoded(body)))
            connection.execute(
                "INSERT INTO versions VALUES(?,?,?,?,?)",
                (version_id, spec.name, spec.version, encoded(metadata), digest(request)),
            )
            connection.execute(
                "INSERT INTO active VALUES(?,?) ON CONFLICT(spec_name) DO UPDATE SET version_id=excluded.version_id",
                (spec.name, version_id),
            )
            if crash_before_commit:
                raise InjectedCrash("Feature rows and active pointer rolled back together")
            return metadata

    def serve(self, entity, now, feature_name="transactions"):
        if not identifier(entity) or not clock(now):
            raise FeatureError("Invalid serving entity/time")
        with self.connect() as connection:
            connection.execute("BEGIN")
            active = connection.execute("SELECT version_id FROM active WHERE spec_name=?", (feature_name,)).fetchone()
            if not active:
                return {"status": "unavailable", "entity": entity, "reason": "no_active_version"}
            metadata = json.loads(
                connection.execute("SELECT body FROM versions WHERE version_id=?", active).fetchone()[0]
            )
            if now < metadata["feature_time"]:
                raise FeatureError("Online snapshots cannot serve requests before their feature time")
            row = connection.execute(
                "SELECT body FROM online WHERE version_id=? AND entity=?", (active[0], entity)
            ).fetchone()
            if not row:
                return {
                    "status": "unavailable",
                    "entity": entity,
                    "version_id": active[0],
                    "reason": "entity_not_materialized",
                }
            body = json.loads(row[0])
            for values in body["windows"].values():
                if values["status"] in {"fresh", "missing"} and now >= values["valid_before"]:
                    values.update(count=None, sum=None, mean=None, last=None, status="expired")
            return {"version_id": active[0], "served_at": now, "features": body, "status": "available"}

    def export_events(self):
        with self.connect() as connection:
            return [
                (Event(event_id, entity, event_time, observed_at, value, revision, bool(deleted)), generation)
                for event_id, revision, entity, event_time, observed_at, value, deleted, generation in connection.execute(
                    "SELECT event_id,revision,entity,event_time,observed_at,value,deleted,generation FROM events ORDER BY event_id,revision"
                )
            ]
