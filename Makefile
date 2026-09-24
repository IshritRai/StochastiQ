.PHONY: seed run run-api run-dashboard test lint

seed:
	python -m app.data.seed.seed

run-api:
	uvicorn app.api.main:app --reload --port 8000

run-dashboard:
	streamlit run dashboard/Home.py

run: run-api

test:
	pytest -q

lint:
	ruff check app tests dashboard
