# Point-in-time selection and immutable serving

## Three separate notions of time

1. Event time is when the measurement happened.
2. Observation time is when a particular revision became available from the source.
3. Ingestion generation identifies the database snapshot that physically contained it.

A historical query supplies entity, label/decision time, optional observation cutoff (never later than label time), and optional source generation. Revisions with later availability or ingestion are excluded before selecting the highest available revision per logical event. A late lower revision cannot override an already available higher revision. Event entity/time cannot change across revisions. Tombstones remove only the logical event visible under those cutoffs.

Observation times are declared provenance. Correctness requires callers to supply availability timestamps honestly; the engine cannot retroactively attest a source clock.

## Indexed ASOF algorithm

SQLite stores immutable `(event_id, revision)` rows and an index over `(entity,event_time,observed_at,event_id,revision)`. A `ROW_NUMBER() OVER(PARTITION BY event_id ORDER BY revision DESC)` CTE resolves visible revisions after applying entity, event-window, availability and source-generation predicates. Immutable event time/entity make filtering before revision resolution safe.

The surviving nondeleted rows are sorted by `(event_time,event_id)`. Python builds an exact integer prefix sum. Each window uses `bisect_right` to enforce its open lower boundary, then computes count/sum by suffix differences. Means are derived floats; sums remain exact integers. Latest-value ties use event ID, independent of insertion order.

## TTL and cached-window validity

For a nonempty window, source freshness is valid through `last_event_time + ttl` on the discrete integer clock. A materialized window may also change when its oldest included event leaves the open-lower-bound window. Its exclusive `valid_before` is the minimum of `last_event_time + ttl + 1` and `oldest_event_time + window`.

Serving at or beyond that boundary withholds cached numeric values and marks them expired. Empty windows use `feature_time + ttl + 1` as a cache expiry. Already stale values remain explicitly stale. This avoids continuing to serve an outdated rolling sum merely because the newest event still satisfies TTL.

These rules do not discover newly arriving events automatically. A cached feature represents its recorded materialization time and source generation; fresh ingestion can require a refresh before TTL. There is no claim that cached values equal a newly recomputed feature at every later request time.

## Offline training join

Labels contain an ID, entity, decision time and target. The query receives only entity/time; targets are copied into a separate output field. One transaction/generation covers the whole join. Repeated entity/time queries are cached, but each output row receives an independent copy to avoid aliasing mutations between training rows. Duplicate label IDs fail.

## Versioned online publication

Feature definitions register immutable `(name,version)` contracts. Materialization computes a bounded entity set inside `BEGIN IMMEDIATE`, using one source generation. It writes all entity values, version metadata and the active pointer in a single SQLite transaction. An injected pre-commit failure leaves no partial entity rows or new pointer.

A version ID binds its specification, entity set, feature time and observation cutoff. Exact replay returns the original snapshot and does not reactivate it if a newer version is active. A changed payload under an existing ID fails. Old source generations remain queryable after backfills so historical online/offline parity can be reconstructed. No remote cache is involved.

## Independent oracle

The reference scans event history, selects the maximum visible revision in dictionaries, filters each time window and sums selected values directly. It does not call the engine SQL, binary-search or prefix-sum helpers. Handwritten boundary tests additionally verify timestamps, deletion visibility, TTL, tie ordering and target isolation so shared contracts cannot conceal every semantic error.

## Complexity and resource bounds

Each ingestion batch has 1–2,048 validated revisions; the store caps retained revisions at 100,000. Feature definitions contain at most 16 sorted windows, each at most 1,000,000 clock units. Queries, labels and materializations use bounded identifiers/clocks and at most 2,048 label/entity rows.

For K visible candidate revisions of an entity in the largest window, SQL revision resolution/sorting is approximately `O(K log K)` after indexed filtering. Prefix sums cost `O(K)` and W window cutoffs `O(W log K)`. The independent oracle intentionally scans full history per query. Offline joins reuse equal entity/time requests. Materialization serializes writers while computing its snapshot. SQLite/WAL transactions provide local atomicity; no distributed consistency or throughput result is claimed.
