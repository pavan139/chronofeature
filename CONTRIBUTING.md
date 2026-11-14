# Changing a feature definition or time rule

Start with a concrete event time, observation time, decision cutoff, and source generation. Write the expected feature by hand before comparing SQL and the scan oracle. A correction or tombstone should have cases on both sides of its availability boundary.

Keep targets outside feature queries. For offline joins, test repeated entity/time rows for independent output objects as well as numerical equality. For online materialization, test the active pointer, version identity, and expiry at a rolling-window boundary.

The implementation lives in `src/chronofeature/feature_store.py`; behavior checks are in `test/test_features.py`. Run `python -m unittest discover -s test -v`, Ruff, and then `python scripts/check_features.py --require-lint --wheel`.

A changed window or TTL needs a new specification identity. Record the feature-spec hash, ingestion generation, and observation cutoff in experiment results. The [point-in-time rules](reference/point-in-time-rules.md) and [parity runs](reference/parity-runs.md) explain the existing boundaries. Do not update an old materialization in place to make a parity comparison pass.
