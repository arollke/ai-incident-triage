.PHONY: test demo eval eval-llm

PYTHON ?= python3

test:
	$(PYTHON) -m pytest

demo:
	$(PYTHON) -m app.cli ingest seed_data/incidents/payment_outage.md

eval:
	$(PYTHON) -m app.evals

eval-llm:
	$(PYTHON) -m app.llm_evals
