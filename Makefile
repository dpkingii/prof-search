.PHONY: venv db migrate ingest api test lint embed label eval

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

embed:
	.venv/bin/python -m index.embed

label:
	.venv/bin/python -m eval.label

eval:
	.venv/bin/python -m eval.run_eval --out eval/results.md
