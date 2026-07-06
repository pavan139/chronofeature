# Feature-store check results

Current interpreter, source digest, test counts, and build stages are recorded in [reports/verification.json](../reports/verification.json). The relocated verifier is `scripts/check_features.py`; the suite is discovered from `test/`.

[Temporal regressions](temporal-regressions.md) describes boundary and aliasing cases. [Parity runs](parity-runs.md) records the independent scan comparisons and generation/materialization scenarios. A successful package check does not establish predictive model accuracy or distributed serving behavior.
