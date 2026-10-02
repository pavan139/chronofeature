PYTHON ?= python

.PHONY: install test demo evaluate verify
install:
	$(PYTHON) -m pip install -e . --no-build-isolation
test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s test -v
demo:
	PYTHONPATH=src $(PYTHON) -m chronofeature demo --config feature_specs/experiment.json --output artifacts/demo.json
evaluate:
	PYTHONPATH=src $(PYTHON) -m chronofeature evaluate --config feature_specs/experiment.json --output artifacts/evaluation.json
verify:
	$(PYTHON) scripts/check_features.py --require-lint --wheel --output reports/verification.json
