.PHONY: test lint format verify

UV ?= uv

test:
	$(UV) run --extra dev pytest -v

lint:
	$(UV) run --extra dev ruff check src tests

format:
	$(UV) run --extra dev ruff format src tests
	$(UV) run --extra dev ruff check --fix src tests

verify: test lint
