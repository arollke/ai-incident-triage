.PHONY: test demo eval

PYTHON ?= python3

test:
	$(PYTHON) -m pytest

demo:
	$(PYTHON) -m app.cli ingest seed_data/incidents/payment_outage.md

eval:
	$(PYTHON) -m app.evals
