.PHONY: venv db migrate ingest api test lint

venv:
	python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt

db:
	docker compose up -d --wait

migrate:
	.venv/bin/python -m migrate

ingest:
	.venv/bin/python -m ingest.load

api:
	.venv/bin/uvicorn api.main:app --reload

test:
	.venv/bin/pytest

lint:
	.venv/bin/ruff check .
