# Point-in-time parity runs

The default experiment used seed 17 and base-event hash `23b98b89c8db84158fb043a7d28dbf3b763481bc388e4221ba4fa9227696f6ff`. It generated 100 entity events, eight corrections and four tombstones, then tested source generations, availability cutoffs, offline joins and materialization versions. Two later backfills exercise future observation exclusion and explicit new-version refresh.

| Check | Actual result |
| --- | --- |
| Independent scan comparisons | 120/120 passed |
| Configurations | 8 entities × 5 decision times × 3 source generations |
| Additional idempotence, target isolation, parity, backfill, atomicity, replay and expiry checks | 18/18 passed |
| Total | 138/138 passed |
| Initial retained source revisions in oracle corpus | 112 |

Reproduce:

```bash
PYTHONPATH=src python -m chronofeature evaluate --seed 17 --output artifacts/evaluation.json
```

[Raw results](../worked_examples/evaluation.json) contain each invariant, one actual training row and an expired serving response. [Demo output](../worked_examples/demo.json) summarizes the same local run. Tests repeat the seeded pipeline at 23 and 101.

Observation cutoffs deliberately differ from event-time windows. A signal with event time 95 but observed at 150 is excluded from label-time 100 features. A historical backfill with declared availability before 100 changes newly recomputed features but cannot mutate an already published version; the source-generation pin reproduces that older snapshot.

These experiments verify controlled temporal/data invariants. No model is trained, no predictive accuracy is claimed, and there is no production traffic, external feature service or measured distributed latency.
