# Temporal regression cases

The review examined observation-versus-event clock filtering, revision/tombstone ordering, open/closed window boundaries, TTL, ingestion generations, target separation, offline snapshot consistency and online publication.

## Concrete issues found and corrected during implementation

- TTL alone cannot establish validity of a cached rolling aggregate. A cached sum can become wrong when its oldest event exits the window while its newest event is still fresh. The engine records the earliest membership boundary and expires cached values before that boundary.
- Empty cached windows originally lacked expiry, which could leave a zero feature indefinitely. Missing-window snapshots now have a cache TTL and withhold values after expiry.
- Reusing a query cache object for multiple labels exposed mutable aliases. Offline joins now copy each result so changing one returned training row cannot alter another.
- Feature definitions are registered under immutable name/version identities for queries as well as materialization, preventing accidental offline/online definition drift.
- Source generation is separate from observation time, permitting reproduction of historical materializations after backfill ingestion.

## Meaningful tests

The suite passed **21/21 test methods**. It checks late observations excluded from earlier labels, future corrections/deletes, out-of-order revisions, exact boundaries/ties, TTL inclusivity, rolling membership expiry, empty-cache expiry, duplicate/conflicting ingestion, immutable event identity, generation pinning, target isolation, alias isolation, an interleaved concurrent ingest during offline join, immutable specs/versions, atomic publish failure/retry and pointer replay behavior.

The independent scan comparison tests resolve revisions and aggregate without SQL/prefix-sum helpers. The end-to-end experiment is also exercised at seeds 17, 23 and 101.

Commands executed:

```bash
PYTHONPATH=src python -m unittest discover -s test -v
PYTHONPATH=src python -m chronofeature evaluate --config feature_specs/experiment.json --output worked_examples/evaluation.json
PYTHONPATH=src python -m chronofeature demo --output worked_examples/demo.json
```

Ruff checks and formatting passed. Standalone verifier output records package build/install checks separately, with a source hash.

## Remaining limits

The engine trusts declared source availability timestamps; it cannot detect a caller backdating them. Cached serving reports its materialization timestamp and does not automatically incorporate new events. Revision history remains stored up to the explicit cap; there is no compaction or distributed cache. Integer signals are deliberate; arbitrary continuous values require a separately defined numeric contract. Synthetic parity does not establish production performance or predictive model accuracy. Failure tests simulate exceptions and restart, not certified hardware/power loss.
