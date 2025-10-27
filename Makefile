.PHONY: help install setup-fixtures test test-verbose test-watch coverage clean format lint pre-commit ci-test

# Default target
help:
	@echo "Available targets:"
	@echo "  make install       - Install dependencies with uv"
	@echo "  make setup-fixtures - Setup test fixtures"
	@echo "  make test          - Run all tests"
	@echo "  make test-verbose  - Run tests with verbose output"
	@echo "  make test-watch    - Run tests in watch mode (requires pytest-watch)"
	@echo "  make coverage      - Run tests with coverage report (min 80%)"
	@echo "  make format        - Format code with black"
	@echo "  make lint          - Check code formatting"
	@echo "  make pre-commit    - Run all pre-commit checks"
	@echo "  make ci-test       - Run tests in CI environment"
	@echo "  make clean         - Remove generated files"

# Setup dependencies with uv
install:
	@echo "Installing dependencies with uv..."
	@uv sync --all-extras

# Setup test fixtures
setup-fixtures:
	@bash tests/setup_fixtures.sh

# Run tests
test: setup-fixtures
	@uv run pytest

# Run tests with verbose output
test-verbose: setup-fixtures
	@uv run pytest -v

# Run tests in watch mode
test-watch: setup-fixtures
	@uv run pytest-watch

# Run tests with coverage
coverage: setup-fixtures
	@uv run pytest --cov=cicada --cov-report=html --cov-report=term-missing --cov-fail-under=80
	@echo "Coverage report generated in htmlcov/index.html"

# Format code with black
format:
	@uv run black cicada tests

# Check code formatting
lint:
	@uv run black --check cicada tests

# Run all pre-commit checks
pre-commit:
	@echo "Running pre-commit checks..."
	@echo "Running black formatter..."
	@uv run black .
	@git add -u
	@$(MAKE) coverage
	@echo "✓ All pre-commit checks passed!"

# Run tests in CI environment
ci-test: setup-fixtures
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
	@rm -rf venv
	@rm -rf .venv
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo "Cleaned up generated files"
