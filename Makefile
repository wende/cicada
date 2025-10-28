.PHONY: help install setup-fixtures extract-keywords test test-verbose test-watch cover clean reset format lint pre-commit ci-test

# Default target
help:
	@echo "Available targets:"
	@echo "  make install       - Install dependencies with uv"
	@echo "  make setup-fixtures - Setup test fixtures"
	@echo "  make extract-keywords - Extract keywords for test fixtures"
	@echo "  make test          - Run all tests"
	@echo "  make test-verbose  - Run tests with verbose output"
	@echo "  make test-watch    - Run tests in watch mode (requires pytest-watch)"
	@echo "  make cover         - Run tests with coverage report (min 80%)"
	@echo "  make format        - Format code with black"
	@echo "  make lint          - Check code formatting"
	@echo "  make pre-commit    - Run all pre-commit checks"
	@echo "  make ci-test       - Run tests in CI environment"
	@echo "  make clean         - Remove generated files"
	@echo "  make reset         - Full reset (cache, models, .cicada dirs)"

# Setup dependencies with uv
install:
	@echo "Installing dependencies with uv..."
	@uv sync --all-extras
	@echo "✓ Dependencies installed. SpaCy models will be downloaded on first use."

# Setup test fixtures
setup-fixtures:
	@bash tests/setup_fixtures.sh

# Extract keywords for test fixtures
extract-keywords:
	@echo "Extracting keywords for test fixtures..."
	@if command -v uv >/dev/null 2>&1; then \
		uv run cicada-index --extract-keywords --output tests/fixtures/.cicada/index.json tests/fixtures/test_project; \
	else \
		python -m cicada.indexer --extract-keywords --output tests/fixtures/.cicada/index.json tests/fixtures/test_project; \
	fi
	@echo "✓ Keywords extracted for test fixtures"

# Run tests
test: setup-fixtures extract-keywords
	@uv run pytest -n auto

# Run tests with verbose output
test-verbose: setup-fixtures extract-keywords
	@uv run pytest -n auto -v

# Run tests in watch mode
test-watch: setup-fixtures extract-keywords
	@uv run pytest-watch

# Run tests with coverage
cover: setup-fixtures extract-keywords
	@uv run pytest -n auto --cov=cicada --cov-report=html --cov-report=term-missing --cov-fail-under=80
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
	@echo "Running basedpyright type checker (errors only)..."
	@uv run basedpyright cicada tests 2>&1 | grep -E "^\s+.*error:|errors," | head -20 || true
	@$(MAKE) cover
	@echo "✓ All pre-commit checks passed!"

# Run tests in CI environment
ci-test: setup-fixtures extract-keywords
	@uv run pytest -n auto -v --cov=cicada --cov-report=term-missing --cov-report=xml --cov-fail-under=80

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

# Full reset: clean everything including cache, models, and cicada directories
reset: clean
	@echo "Performing full cicada reset..."
	@echo "1. Clearing uv cache..."
	@uv cache clean 2>&1 || true
	@echo "2. Uninstalling spaCy models from tool environment..."
	@if [ -d ~/.local/share/uv/tools/cicada ]; then \
		uv pip uninstall --python ~/.local/share/uv/tools/cicada/bin/python3 \
			en-core-web-sm en-core-web-md en-core-web-lg 2>&1 || true; \
	else \
		echo "   No cicada tool environment found, skipping model uninstall"; \
	fi
	@echo "3. Removing .cicada directories..."
	@rm -rf .cicada
	@rm -rf tests/fixtures/.cicada
	@rm -rf tests/fixtures/test_project/.cicada
	@rm -rf tests/fixtures/elixir_project/.cicada
	@echo "4. Removing .mcp.json..."
	@rm -f .mcp.json
	@echo "✓ Full reset complete!"
	@echo ""
	@echo "To reinstall cicada:"
	@echo "  uv tool install --editable . --force"
