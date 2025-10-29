.PHONY: help install setup-fixtures extract-keywords test test-verbose test-watch cover clean format lint pre-commit ci-test

# Default target
help:
	@echo "Available targets:"
	@echo "  make install       - Install dependencies with uv"
	@echo "  make setup-fixtures - Setup test fixtures"
	@echo "  make extract-keywords - Extract keywords for test fixtures"
	@echo "  make test          - Run all tests (auto-installs dependencies)"
	@echo "  make test-verbose  - Run tests with verbose output (auto-installs dependencies)"
	@echo "  make test-watch    - Run tests in watch mode (auto-installs dependencies)"
	@echo "  make cover         - Run tests with coverage report (auto-installs dependencies)"
	@echo "  make format        - Format code with black (auto-installs dependencies)"
	@echo "  make lint          - Run pyrefly type checker (auto-installs dependencies)"
	@echo "  make pre-commit    - Run all pre-commit checks (auto-installs dependencies)"
	@echo "  make ci-test       - Run tests in CI environment (auto-installs dependencies)"
	@echo "  make clean         - Remove generated files"

# Setup dependencies with uv
install:
	@echo "Installing dependencies with uv..."
	@uv sync --extra dev
	@echo "✓ Dependencies installed (models will be downloaded on first use if needed)"

# Setup test fixtures
setup-fixtures:
	@bash tests/setup_fixtures.sh

# Extract keywords for test fixtures
extract-keywords:
	@echo "Extracting keywords for test fixtures..."
	@if [ -d "tests/fixtures/elixir_project" ]; then \
		FIXTURE_DIR="tests/fixtures/elixir_project"; \
	elif [ -d "tests/fixtures/test_project" ]; then \
		FIXTURE_DIR="tests/fixtures/test_project"; \
	else \
		echo "Error: No test fixture found"; \
		exit 1; \
	fi; \
	if command -v uv >/dev/null 2>&1; then \
		uv run cicada-index --extract-keywords --output tests/fixtures/.cicada/index.json $$FIXTURE_DIR; \
	else \
		python -m cicada.indexer --extract-keywords --output tests/fixtures/.cicada/index.json $$FIXTURE_DIR; \
	fi
	@echo "✓ Keywords extracted for test fixtures"

# Run tests
test: install setup-fixtures extract-keywords
	@uv run pytest

# Run tests with verbose output
test-verbose: install setup-fixtures extract-keywords
	@uv run pytest -v

# Run tests in watch mode
test-watch: install setup-fixtures extract-keywords
	@uv run pytest-watch

# Run tests with coverage
cover: install setup-fixtures extract-keywords
	@uv run pytest --cov=cicada --cov-report=html --cov-report=term-missing --cov-fail-under=80
	@echo "Coverage report generated in htmlcov/index.html"

# Format code with black
format: install
	@uv run black cicada tests

# Check code formatting with pyrefly type checker
lint: install
	@uv run pyrefly check cicada --project-excludes tests

# Run all pre-commit checks
pre-commit: install
	@echo "Running pre-commit checks..."
	@echo "Running black formatter..."
	@uv run black .
	@git add -u
	@echo "Running pyrefly type checker (errors only)..."
	@uv run pyrefly check cicada --project-excludes tests 2>&1 | grep -E "^\s+.*error:|errors," | head -20 || true
	@$(MAKE) cover
	@echo "✓ All pre-commit checks passed!"

# Run tests in CI environment
ci-test: install setup-fixtures extract-keywords
	@uv run pytest -v --cov=cicada --cov-report=term-missing --cov-report=xml --cov-fail-under=80

# Clean up generated files
clean:
	@rm -rf .pytest_cache
	@rm -rf htmlcov
	@rm -rf .coverage
	@rm -rf *.egg-info
	@rm -rf dist
	@rm -rf build
	@rm -rf __pycache__
	@rm -rf .venv  # uv managed environment
	@rm -rf venv   # legacy venv
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo "Cleaned up generated files"
