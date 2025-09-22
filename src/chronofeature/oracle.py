"""Independent full-history scan; no SQL, prefix sums or engine query calls."""

from dataclasses import asdict

from .feature_store import digest


def scan(events, query, spec, generation):
    winners = {}
    for event, ingested in events:
        if (
            ingested > generation
            or event.entity != query.entity
            or event.observed_at > query.cutoff
            or event.event_time > query.label_time
        ):
            continue
        previous = winners.get(event.event_id)
        if previous is None or event.revision > previous.revision:
            winners[event.event_id] = event
    alive = [event for event in winners.values() if not event.deleted]
    windows = {}
    for duration in spec.windows:
        selected = [event for event in alive if query.label_time - duration < event.event_time <= query.label_time]
        if not selected:
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
        latest = max(selected, key=lambda event: (event.event_time, event.event_id))
        fresh = query.label_time <= latest.event_time + spec.ttl
        total = sum(event.value for event in selected)
        windows[str(duration)] = {
            "count": len(selected) if fresh else None,
            "sum": total if fresh else None,
            "mean": total / len(selected) if fresh else None,
            "last": latest.value if fresh else None,
            "last_event_time": latest.event_time,
            "status": "fresh" if fresh else "stale",
            "valid_before": min(
                latest.event_time + spec.ttl + 1, min(event.event_time for event in selected) + duration
            ),
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
