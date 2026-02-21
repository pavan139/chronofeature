# Feature query and serving flow

```mermaid
flowchart LR
  E[Events and immutable revisions] --> I[Atomic ingestion generation]
  I --> X[Entity and event-time index]
  Q[Entity, label time, observation cutoff] --> A[ASOF visible-revision query]
  X --> A
  A --> W[Prefix-sum window aggregates and TTL]
  W --> J[Target-separated offline training join]
  W --> M[Immutable feature-version materialization]
  M --> P[Atomic active-version pointer]
  P --> S[Versioned serving and expiry]
  O[Independent full-history scan] --> C[Parity and leakage checks]
  J --> C
  S --> C
```

`feature_store.py` owns validated events, specifications, point-in-time SQL, offline joins and atomic online versions. `oracle.py` independently resolves visible revisions by full scan and aggregates each window separately. `experiments.py` generates late observations, corrections, tombstones and backfills, then checks feature/serving parity.

The ingestion boundary changes source generation atomically. Offline joins pin a generation and read snapshot. Materialization publishes entity rows and the active pointer together. The target is never passed to the query function. SQL values are bound parameters, not interpolated expressions.
