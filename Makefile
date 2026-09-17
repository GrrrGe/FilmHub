.PHONY: verify enrich index run-api run-ui all

verify:
	python scripts/verify_data.py

enrich:
	python scripts/enrich_official_plots.py --limit $${LIMIT:-50} $${EXTRA:-}

index:
	python scripts/build_index.py

all: verify index

run-api:
	uvicorn main:app --reload --port 8000

run-ui:
	FILMHUB_API_BASE=http://127.0.0.1:8000 python app.py
