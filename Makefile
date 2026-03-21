.PHONY: check lint format test install-hooks

check: lint format test

lint:
	uv run ruff check scoped_metric_engine tests

format:
	uv run ruff format --check scoped_metric_engine tests

test:
	uv run pytest

install-hooks:
	uv run pre-commit install
