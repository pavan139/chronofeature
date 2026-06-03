# Sharing feature specifications and results

A feature result is reproducible only with its specification, source generation, entity set, feature time, and observation cutoff. Keep those identities with any training-row or serving example.

```sh
python -m pip install -e . -r requirements-dev.txt
python scripts/check_features.py --require-lint --wheel
python -m chronofeature evaluate --config feature_specs/experiment.json --output artifacts/spec-check.json
```

Inspect both an offline row and an expired serving response. A cached value carries its materialization time; do not label it as recomputed at the serving request time. A definition change requires a new `(name, version)` contract and a new materialization.

The package contains the feature store and independent oracle. Ship bounded synthetic examples from `worked_examples/`, not a local SQLite file containing source history or targets. The CI workflow records package verification under `reports/verification.json`; remote CI execution is distinct from a local check.

Any connector must provide meaningful availability timestamps. This implementation cannot verify whether a source declared an observation honestly. [Parity runs](parity-runs.md) states the cutoffs used in the existing examples.
