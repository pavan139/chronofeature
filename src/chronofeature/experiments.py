from dataclasses import asdict, replace
from pathlib import Path
import random
import tempfile

from .feature_store import Event, FeatureError, FeatureStore, InjectedCrash, Label, Query, Spec, digest
from .oracle import scan


def evaluate(seed=17):
    if type(seed) is not int:
        raise FeatureError("Seed must be an integer")
    rng = random.Random(seed)
    events = [
        Event(f"event-{i}", f"entity-{rng.randrange(8)}", i, i + rng.randrange(21), rng.randrange(-20, 200))
        for i in range(100)
    ]
    cases = []
    spec = Spec()
    with tempfile.TemporaryDirectory() as directory:
        store = FeatureStore(Path(directory) / "features.sqlite")
        for start in range(0, 100, 20):
            store.ingest(events[start : start + 20])
        corrections = [
            replace(event, revision=1, observed_at=event.event_time + 30, value=event.value + 50)
            for event in events[::13]
        ]
        store.ingest(corrections)
        tombstones = [
            replace(event, revision=2, observed_at=event.event_time + 50, value=None, deleted=True)
            for event in events[::29]
        ]
        store.ingest(tombstones)
        replay = store.ingest(events[:3])
        cases.append(
            {
                "id": "duplicate-ingest-stable-generation",
                "passed": replay["inserted"] == 0 and replay["generation"] == 7,
            }
        )
        history = store.export_events()
        for generation in (1, 3, 7):
            for entity in range(8):
                for label_time in (10, 30, 60, 100, 140):
                    query = Query(f"entity-{entity}", label_time, label_time - 5)
                    result = store.query(query, spec, source_generation=generation)
                    cases.append(
                        {
                            "id": f"oracle-g{generation}-e{entity}-t{label_time}",
                            "passed": result == scan(history, query, spec, generation),
                        }
                    )
        labels = [Label(f"label-{entity}", f"entity-{entity}", 100, entity % 2) for entity in range(8)]
        joined = store.offline_join(labels, spec)
        changed = store.offline_join([replace(label, target=1 - label.target) for label in labels], spec)
        cases.append(
            {
                "id": "target-never-enters-features",
                "passed": [row["features"] for row in joined["rows"]] == [row["features"] for row in changed["rows"]],
            }
        )
        entities = [label.entity for label in labels]
        store.materialize("snapshot-1", entities, 100, spec)
        for label in labels:
            cases.append(
                {
                    "id": f"online-offline-{label.entity}",
                    "passed": store.serve(label.entity, 100)["features"]
                    == store.query(Query(label.entity, 100), spec, source_generation=7),
                }
            )
        previous = store.serve("entity-0", 100)
        store.ingest([Event("late-observation", "entity-0", 95, 150, 999)])
        cases.append(
            {
                "id": "late-observation-not-label-leak",
                "passed": store.query(Query("entity-0", 100), spec)["windows"] == previous["features"]["windows"],
            }
        )
        store.ingest([Event("historical-backfill", "entity-0", 94, 95, 1111)])
        cases.append({"id": "old-online-version-immutable", "passed": store.serve("entity-0", 100) == previous})
        store.materialize("snapshot-2", entities, 100, spec)
        cases.append(
            {
                "id": "backfill-new-version-parity",
                "passed": store.serve("entity-0", 100)["features"] == store.query(Query("entity-0", 100), spec),
            }
        )
        before = store.serve("entity-0", 100)
        try:
            store.materialize("crashed", entities, 105, spec, crash_before_commit=True)
        except InjectedCrash:
            pass
        cases.append({"id": "atomic-materialization-pointer", "passed": store.serve("entity-0", 100) == before})
        store.materialize("crashed", entities, 105, spec)
        cases.append(
            {"id": "restart-materialization", "passed": store.serve("entity-0", 105)["version_id"] == "crashed"}
        )
        replay = store.materialize("snapshot-1", entities, 100, spec)
        cases.append(
            {
                "id": "replay-does-not-roll-pointer-back",
                "passed": replay["replayed"] and store.serve("entity-0", 105)["version_id"] == "crashed",
            }
        )
        expired = store.serve("entity-0", 200)
        cases.append(
            {
                "id": "expired-values-withheld",
                "passed": all(row["sum"] is None for row in expired["features"]["windows"].values()),
            }
        )
        try:
            Query("entity-0", 100, 101)
            denied = False
        except FeatureError:
            denied = True
        cases.append({"id": "future-observation-cutoff-denied", "passed": denied})
    return {
        "schema_version": 1,
        "experiment": "synthetic_point_in_time_features_vs_independent_scan",
        "seed": seed,
        "input_sha256": digest([asdict(event) for event in events]),
        "base_events": len(events),
        "source_revisions": len(history),
        "oracle_comparisons": 120,
        "checks": len(cases),
        "passed": sum(row["passed"] for row in cases),
        "cases": cases,
        "example_training_row": joined["rows"][0],
        "example_expired_serving": expired,
        "limitations": [
            "Availability timestamps are declared source provenance, not externally attested clocks.",
            "Local SQLite snapshots and integer-valued signals; no distributed online store or throughput claim.",
            "Online values retain their materialization feature time; they are not recomputed at serving time.",
        ],
    }
