.PHONY: help install dev lint lint-fix format format-check test test-cov clean build docs docs-serve check

help: ## Show this help message
	@echo "Available targets:"
	@echo "  make install       - Editable install (no dev extras)"
	@echo "  make dev           - Editable install with dev extras"
	@echo "  make lint          - Run ruff check + mypy --strict"
	@echo "  make lint-fix      - Auto-fix lint issues with ruff"
	@echo "  make format        - Format code with ruff format"
	@echo "  make format-check  - Verify formatting without changes"
	@echo "  make test          - Run the test suite"
	@echo "  make test-cov      - Run tests with coverage (fail under 90%)"
	@echo "  make check         - Run lint + format-check + test (full pre-commit check)"
	@echo "  make build         - Build sdist + wheel into dist/"
	@echo "  make docs          - Build documentation site"
	@echo "  make docs-serve    - Serve documentation locally"
	@echo "  make clean         - Remove build artifacts and caches"

install: ## Editable install (no dev extras)
	pip install -e .

dev: ## Editable install with dev extras
	pip install -e ".[dev]"

lint: ## Run ruff check + mypy --strict
	ruff check .
	mypy --strict behave_doctor

lint-fix: ## Auto-fix lint issues
	ruff check --fix .

format: ## Format code with ruff format
	ruff format .

format-check: ## Verify formatting without changes
	ruff format --check .

test: ## Run the test suite
	pytest

test-cov: ## Run tests with coverage (fail under 90%)
	pytest --cov=behave_doctor --cov-report=term-missing --cov-fail-under=90

check: ## Run lint + format-check + test (full pre-commit check)
	ruff check .
	ruff format --check .
	mypy --strict behave_doctor
	pytest

build: ## Build sdist + wheel into dist/
	python -m build

docs: ## Build documentation site
	mkdocs build --strict

docs-serve: ## Serve documentation locally
	mkdocs serve

clean: ## Remove build artifacts and caches
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in ['dist','build','.pytest_cache','.mypy_cache','.ruff_cache','htmlcov','site'] + list(pathlib.Path('.').glob('*.egg-info'))]"
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"
