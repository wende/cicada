.PHONY: help install install-deps setup-fixtures test test-verbose test-watch cover clean reset format lint pre-commit ci-test

# Default target
help:
	@echo "Available targets:"
	@echo "  make install       - Full install (deps + cicada tool to ~/.local/bin)"
	@echo "  make install-deps  - Install dependencies only (no tool installation)"
	@echo "  make setup-fixtures - Setup test fixtures"
	@echo "  make extract-keywords - Extract keywords for test fixtures"
	@echo "  make test          - Run all tests (auto-installs dependencies)"
	@echo "  make test-verbose  - Run tests with verbose output (auto-installs dependencies)"
	@echo "  make test-watch    - Run tests in watch mode (auto-installs dependencies)"
	@echo "  make cover         - Run tests with coverage report (auto-installs dependencies)"
	@echo "  make format        - Format code with black (auto-installs dependencies)"
	@echo "  make lint          - Run ruff linter, pyrefly type checker and vulture dead code detector (auto-installs dependencies)"
	@echo "  make lint-fix      - Auto-fix issues with ruff"
	@echo "  make pre-commit    - Run all pre-commit checks (auto-installs dependencies)"
	@echo "  make ci-test       - Run tests in CI environment (auto-installs dependencies)"
	@echo "  make clean         - Remove generated files"
	@echo "  make reset         - Full reset (cache, models, .cicada dirs)"

# Install dependencies only
install-deps:
	@echo "Installing dependencies with uv..."
	@uv sync --dev
	@echo "✓ Dependencies installed (models will be downloaded on first use if needed)"

# Full installation (deps + tool)
install: install-deps
	@echo ""
	@echo "Installing cicada tool to ~/.local/bin/..."
	@uv tool install --editable . --force
	@echo "✓ cicada installed in editable mode"
	@echo "  Command 'cicada' now uses code from $(PWD)"

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
	@uv run pytest -n auto

# Run tests with verbose output
test-verbose: install setup-fixtures extract-keywords
	@uv run pytest -n auto -v

# Run tests in watch mode
test-watch: install setup-fixtures extract-keywords
	@uv run pytest-watch

# Run tests with coverage
cover: install setup-fixtures extract-keywords
	@uv run pytest -n auto --cov=cicada --cov-report=html --cov-report=term-missing --cov-fail-under=80
	@echo "Coverage report generated in htmlcov/index.html"

# Format code with black
format: install
	@uv run black cicada tests

# Auto-fix issues with ruff
lint-fix: install
	@echo "Running ruff with auto-fix..."
	@uv run ruff check cicada --fix
	@echo "✓ Auto-fixable issues resolved"

# Check code formatting with ruff linter, pyrefly type checker and vulture dead code detector
lint: install
	@FAILED=0; \
	echo "Running ruff linter..."; \
	uv run ruff check cicada || FAILED=1; \
	echo ""; \
	echo "Running pyrefly type checker..."; \
	uv run pyrefly check cicada --project-excludes tests || FAILED=1; \
	echo ""; \
	echo "Running vulture dead code detector..."; \
	uv run vulture cicada --min-confidence 80 || FAILED=1; \
	exit $$FAILED

# Run all pre-commit checks
pre-commit: install
	@echo "Running pre-commit checks..."
	@echo "Running black formatter..."
	@uv run black .
	@git add -u
	@$(MAKE) lint
	@$(MAKE) cover
	@echo "✓ All pre-commit checks passed!"

# Run tests in CI environment
ci-test: install setup-fixtures extract-keywords
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
	@echo "2. Removing .cicada directories..."
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
