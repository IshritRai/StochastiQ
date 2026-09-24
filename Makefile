.PHONY: seed fetch-vuln-intel run run-api run-dashboard test lint

seed:
	python -m app.data.seed.seed

fetch-vuln-intel:
	python -c "from app.data.ingest.vuln_intel import import_vuln_intel; print(import_vuln_intel())"

run-api:
	uvicorn app.api.main:app --reload --port 8000

run-dashboard:
	streamlit run dashboard/Home.py

run: run-api

test:
	pytest -q

lint:
	ruff check app tests dashboard
