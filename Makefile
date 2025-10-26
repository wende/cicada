.PHONY: help install setup-fixtures test test-verbose test-watch coverage clean format lint pre-commit ci-test

# Default target
help:
	@echo "Available targets:"
	@echo "  make install       - Install dependencies in venv"
	@echo "  make setup-fixtures - Setup test fixtures"
	@echo "  make test          - Run all tests"
	@echo "  make test-verbose  - Run tests with verbose output"
	@echo "  make test-watch    - Run tests in watch mode (requires pytest-watch)"
	@echo "  make coverage      - Run tests with coverage report (min 80%)"
	@echo "  make format        - Format code with black"
	@echo "  make lint          - Check code formatting"
	@echo "  make pre-commit    - Run all pre-commit checks"
	@echo "  make ci-test       - Run tests in CI environment (no venv activation)"
	@echo "  make clean         - Remove generated files"

# Setup virtual environment and install dependencies
install:
	@if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv venv; \
	fi
	@echo "Installing dependencies..."
	@. venv/bin/activate && pip install -e ".[dev]"

# Setup test fixtures
setup-fixtures:
	@bash tests/setup_fixtures.sh

# Run tests
test: setup-fixtures
	@. venv/bin/activate && pytest

# Run tests with verbose output
test-verbose: setup-fixtures
	@. venv/bin/activate && pytest -v

# Run tests in watch mode
test-watch: setup-fixtures
	@. venv/bin/activate && pytest-watch

# Run tests with coverage
coverage: setup-fixtures
	@. venv/bin/activate && pytest --cov=cicada --cov-report=html --cov-report=term-missing --cov-fail-under=80
	@echo "Coverage report generated in htmlcov/index.html"

# Format code with black
format:
	@. venv/bin/activate && black cicada tests

# Check code formatting
lint:
	@. venv/bin/activate && black --check cicada tests

# Run all pre-commit checks
pre-commit:
	@echo "Running pre-commit checks..."
	@echo "Running black formatter..."
	@. venv/bin/activate && black .
	@git add -u
	@$(MAKE) coverage
	@echo "✓ All pre-commit checks passed!"

# Run tests in CI environment (without venv activation)
ci-test: setup-fixtures
	@pytest -v --cov=cicada --cov-report=term-missing --cov-report=xml --cov-fail-under=80

# Clean up generated files
clean:
	@rm -rf .pytest_cache
	@rm -rf htmlcov
	@rm -rf .coverage
	@rm -rf *.egg-info
	@rm -rf dist
	@rm -rf build
	@rm -rf __pycache__
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo "Cleaned up generated files"
