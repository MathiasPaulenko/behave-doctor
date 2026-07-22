.PHONY: install dev lint lint-fix format format-check test test-cov clean build

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

lint:
	ruff check .
	mypy --strict behave_doctor

lint-fix:
	ruff check --fix .

format:
	ruff format .

format-check:
	ruff format --check .

test:
	pytest

test-cov:
	pytest --cov=behave_doctor --cov-report=term-missing --cov-fail-under=90

clean:
	rm -rf dist build *.egg-info
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +

build:
	python -m build
