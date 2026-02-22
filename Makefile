.PHONY: help install install-deps generate-scip-proto setup-fixtures setup-scip setup-scip-fixtures test test-verbose test-watch cover test-docker test-docker-langs test-docker-complete clean reset format lint pre-commit ci-test pr-comments dev

# Default target
help:
	@echo "Available targets:"
	@echo "  make install          - Full install (deps + cicada tool to ~/.local/bin)"
	@echo "  make install-deps     - Install dependencies only (no tool installation)"
	@echo "  make uninstall        - Uninstall cicada tool"
	@echo "  make generate-scip-proto - Generate SCIP protobuf files for local development (auto-generated during package build)"
	@echo "  make setup-fixtures   - Setup test fixtures"
	@echo "  make setup-scip       - Install SCIP indexers and generate indexes for test fixtures"
	@echo "  make test             - Run all tests (auto-installs dependencies)"
	@echo "  make test-verbose     - Run tests with verbose output (auto-installs dependencies)"
	@echo "  make test-watch       - Run tests in watch mode (auto-installs dependencies)"
	@echo "  make cover            - Run tests with coverage report (auto-installs dependencies)"
	@echo "  make test-docker      - Run all SCIP language Docker tests (fast all-in-one image)"
	@echo "  make test-docker-langs LANGS='go java' - Run specific SCIP language Docker tests"
	@echo "  make test-docker-complete - Run complete Docker test pipeline"
	@echo "  make format           - Format code with black (auto-installs dependencies)"
	@echo "  make lint             - Run ruff linter, pyrefly type checker and vulture dead code detector (auto-installs dependencies)"
	@echo "  make lint-fix         - Auto-fix issues with ruff"
	@echo "  make pre-commit       - Run all pre-commit checks (auto-installs dependencies)"
	@echo "  make ci-test          - Run tests in CI environment (auto-installs dependencies)"
	@echo "  make pr-comments [PR=<number>] - Display all comments from PR for current branch (or specify PR number)"
	@echo "  make clean            - Remove generated files"
	@echo "  make reset            - Full reset (cache, models, .cicada dirs)"
	@echo "  make dev              - Clean rebuild and install (avoids cache issues)"
	@echo "  make help             - Display this help message"

dev:
	@echo "Installing cicada tool in development mode (clean rebuild)..."
	@echo "1. Cleaning dist directory..."
	@rm -rf dist/
	@echo "2. Building package..."
	@uv build
	@echo "3. Uninstalling old version..."
	@uv tool uninstall cicada-mcp 2>/dev/null || true
	@echo "4. Clearing Python bytecode cache..."
	@find ~/.local/share/uv/tools/cicada-mcp -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find ~/.local/share/uv/tools/cicada-mcp -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "5. Installing from fresh build..."
	@uv tool install --reinstall dist/cicada_mcp-*-py3-none-any.whl
	@echo "cicada installed from fresh build"
	@echo "  Commands: cicada, cicada-mcp, cicada-server"
	@echo "  Installed from: $(PWD)/dist/"

# Install dependencies only
install-deps:
	@echo "Installing dependencies with uv..."
	@uv sync --dev
	@echo "Dependencies installed (models will be downloaded on first use if needed)"

# Full installation (deps + tool)
install: install-deps
	@echo ""
	@echo "Installing cicada tool to ~/.local/bin/..."
	@uv tool install --editable . --force
	@echo "cicada installed in editable mode"
	@echo "  Command 'cicada' now uses code from $(PWD)"


uninstall: clean
	@echo "Uninstalling cicada tool..."
	@uv tool uninstall cicada-mcp 2>/dev/null || true
	@echo "cicada uninstalled"

# Generate SCIP protobuf files
generate-scip-proto:
	@echo "Generating SCIP protobuf files..."
	@if command -v protoc >/dev/null 2>&1; then \
		cd cicada/languages/scip && protoc -I. --python_out=. --pyi_out=. scip.proto && echo "✓ SCIP protobuf files generated (via protoc)"; \
	else \
		cd cicada/languages/scip && uvx --from grpcio-tools python -m grpc_tools.protoc -I. --python_out=. --pyi_out=. scip.proto && echo "✓ SCIP protobuf files generated (via grpcio-tools)"; \
	fi

# Setup test fixtures
setup-fixtures:
	@bash tests/setup_fixtures.sh

# Setup SCIP indexers globally (for manual setup)
setup-scip:
	@echo "Setting up SCIP indexers globally..."
	@if ! command -v npm >/dev/null 2>&1; then \
		echo "Error: npm is not installed. Please install Node.js first."; \
		exit 1; \
	fi
	@echo "Installing SCIP indexers..."
	@npm install -g @sourcegraph/scip-python @sourcegraph/scip-typescript
	@$(MAKE) setup-scip-fixtures
	@echo "✓ SCIP setup complete!"

# Generate SCIP index files for test fixtures (uses local install if needed)
setup-scip-fixtures:
	@if [ -f tests/fixtures/sample_python/index.scip ] && [ -f tests/fixtures/sample_typescript/index.scip ] && [ -f tests/fixtures/sample_javascript/index.scip ]; then \
		echo "SCIP fixture indexes already exist"; \
	else \
		echo "Generating SCIP fixture indexes..."; \
		if ! command -v npm >/dev/null 2>&1; then \
			echo "Warning: npm not installed, skipping SCIP fixture generation"; \
			echo "  Install Node.js and run 'make setup-scip' for full test coverage"; \
		else \
			if ! command -v scip-python >/dev/null 2>&1; then \
				echo "  Installing scip-python locally to ~/.cicada/node/..."; \
				npm install --prefix ~/.cicada/node @sourcegraph/scip-python >/dev/null 2>&1 || true; \
			fi; \
			SCIP_PYTHON=$$(command -v scip-python || echo ~/.cicada/node/node_modules/.bin/scip-python); \
			if [ -x "$$SCIP_PYTHON" ] || [ -f "$$SCIP_PYTHON" ]; then \
				echo "  Generating Python SCIP index..."; \
				(cd $(CURDIR)/tests/fixtures/sample_python && "$$SCIP_PYTHON" index . 2>/dev/null && echo "  ✓ Python SCIP index generated") || echo "  ⚠ Python SCIP index generation failed"; \
			fi; \
			if ! command -v scip-typescript >/dev/null 2>&1; then \
				echo "  Installing scip-typescript locally to ~/.cicada/node/..."; \
				npm install --prefix ~/.cicada/node @sourcegraph/scip-typescript >/dev/null 2>&1 || true; \
			fi; \
			SCIP_TS=$$(command -v scip-typescript || echo ~/.cicada/node/node_modules/.bin/scip-typescript); \
			if [ -x "$$SCIP_TS" ] || [ -f "$$SCIP_TS" ]; then \
				echo "  Generating TypeScript SCIP index..."; \
				(cd $(CURDIR)/tests/fixtures/sample_typescript && npm install --silent 2>/dev/null && "$$SCIP_TS" index . 2>/dev/null && echo "  ✓ TypeScript SCIP index generated") || echo "  ⚠ TypeScript SCIP index generation failed"; \
				echo "  Generating JavaScript SCIP index..."; \
				(cd $(CURDIR)/tests/fixtures/sample_javascript && npx --yes @sourcegraph/scip-typescript index 2>/dev/null && echo "  ✓ JavaScript SCIP index generated successfully") || echo "  ⚠ JavaScript SCIP index generation failed"; \
			fi; \
		fi; \
	fi

# Run tests
test: install-deps generate-scip-proto setup-fixtures setup-scip-fixtures
	@set -o pipefail; uv run pytest -n auto --dist loadgroup --disable-warnings --tb=short --no-header -q 2>&1 | tail -30

# Run tests with verbose output
test-verbose: install-deps generate-scip-proto setup-fixtures setup-scip-fixtures
	@uv run pytest -n auto --dist loadgroup -v

# Run tests in watch mode
test-watch: install-deps generate-scip-proto setup-fixtures setup-scip-fixtures
	@uv run pytest-watch

# Run tests with coverage
cover: install-deps generate-scip-proto setup-fixtures setup-scip-fixtures
	@uv run pytest -n auto --dist loadgroup --cov=cicada --cov-report=html --cov-report=term-missing --cov-fail-under=80
	@echo "Coverage report generated in htmlcov/index.html"

# Run all SCIP language Docker tests (recommended - fast all-in-one image)
test-docker:
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "Error: docker is not installed. Please install Docker first."; \
		exit 1; \
	fi
	@cd tests/docker && ./test-scip-languages.sh

# Run specific SCIP language Docker tests (usage: make test-docker-langs LANGS="go java")
test-docker-langs:
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "Error: docker is not installed. Please install Docker first."; \
		exit 1; \
	fi
	@if [ -z "$(LANGS)" ]; then \
		echo "Error: Please specify LANGS variable (e.g., make test-docker-langs LANGS='go java')"; \
		exit 1; \
	fi
	@cd tests/docker && ./test-scip-languages.sh $(LANGS)

# Run complete Docker test pipeline
test-docker-complete:
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "Error: docker is not installed. Please install Docker first."; \
		exit 1; \
	fi
	@cd tests/docker && ./test-complete.sh

# Format code with black
format: install-deps
	@uv run black cicada tests

# Auto-fix issues with ruff
lint-fix: install-deps
	@echo "Running ruff with auto-fix..."
	@uv run ruff check cicada --fix
	@echo "Auto-fixable issues resolved"

# Check code formatting with ruff linter, pyrefly type checker and vulture dead code detector
lint: install-deps
	@FAILED=0; \
	echo "Running ruff linter..."; \
	uv run ruff check cicada || FAILED=1; \
	echo ""; \
	echo "Running pyrefly type checker..."; \
	uv run pyrefly check cicada --project-excludes tests --project-excludes cicada/languages/scip || FAILED=1; \
	echo ""; \
	echo "Running vulture dead code detector..."; \
	uv run vulture cicada --min-confidence 80 || FAILED=1; \
	exit $$FAILED

# Run all pre-commit checks
pre-commit: install-deps
	@echo "Running pre-commit checks..."
	@echo "Fetching latest tags..."
	@git fetch --tags --quiet 2>/dev/null || true
	@echo "Updating version hash (local only, not committed)..."
	@set -e; \
	GIT_HASH=$$(git rev-parse --short HEAD 2>/dev/null || echo "unknown"); \
	GIT_TAG=$$(git describe --tags --abbrev=0 2>/dev/null || echo "unknown"); \
	{ \
		echo '"""Auto-generated file containing build-time git tag and hash."""'; \
		echo ''; \
		echo "GIT_TAG = \"$$GIT_TAG\""; \
		echo "GIT_HASH = \"$$GIT_HASH\""; \
	} > cicada/_version_hash.py
	@echo "Running black formatter..."
	@uv run black .
	@git add -u
	@echo "Running linter..."
	@FAILED=0; \
	echo "Running ruff linter..."; \
	uv run ruff check cicada || FAILED=1; \
	echo ""; \
	echo "Running pyrefly type checker..."; \
	uv run pyrefly check cicada --project-excludes tests --project-excludes cicada/languages/scip || FAILED=1; \
	echo ""; \
	echo "Running vulture dead code detector..."; \
	uv run vulture cicada --min-confidence 80 || FAILED=1; \
	exit $$FAILED
	@$(MAKE) generate-scip-proto
	@echo "Running tests..."
	@bash tests/setup_fixtures.sh
	@set -o pipefail; uv run pytest -n auto --dist loadgroup --disable-warnings --tb=line --no-header -q 2>&1 | tail -20
	@echo "✓ All pre-commit checks passed!"

# Run tests in CI environment
ci-test: install-deps generate-scip-proto setup-fixtures setup-scip-fixtures
	@uv run pytest -n auto --dist loadgroup -v --cov=cicada --cov-report=term-missing --cov-report=xml --cov-fail-under=80

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
	@rm -f cicada/languages/scip/scip_pb2.py cicada/languages/scip/scip_pb2.pyi
	@echo "Cleaned up generated files"

# Full reset: clean everything including cache, models, and cicada directories
reset: clean
	@echo "Performing full cicada reset..."
	@echo "1. Clearing uv cache..."
	@uv cache clean 2>&1 || true
	@echo "2. Removing .mcp.json..."
	@rm -f .mcp.json
	@echo "✓ Full reset complete!"
	@echo ""
	@echo "Note: Cicada now uses centralized storage at ~/.cicada/projects/"
	@echo "To clean all cicada data: cicada clean --all"
	@echo ""
	@echo "To reinstall cicada:"
	@echo "  uv tool install --editable . --force"

# Display all comments from PR for current branch (or specify PR number with PR=<number>)
pr-comments:
	@echo "Fetching PR comments..."
	@set -e; \
	if ! command -v gh >/dev/null 2>&1; then \
		echo "Error: 'gh' (GitHub CLI) is not installed. Please install it to use this command."; \
		exit 1; \
	fi; \
	if [ -n "$(PR)" ]; then \
		PR_NUMBER=$(PR); \
		echo "Using specified PR #$$PR_NUMBER"; \
	else \
		BRANCH=$$(git rev-parse --abbrev-ref HEAD); \
		if [ "$$BRANCH" = "HEAD" ] || [ "$$BRANCH" = "main" ] || [ "$$BRANCH" = "master" ]; then \
			echo "Error: Not on a feature branch (currently on $$BRANCH)"; \
			exit 1; \
		fi; \
		echo "Current branch: $$BRANCH"; \
		echo ""; \
		PR_NUMBER=$$(gh pr list --head "$$BRANCH" --json number --jq '.[0].number'); \
		if [ -z "$$PR_NUMBER" ]; then \
			echo "Error: No PR found for branch $$BRANCH"; \
			exit 1; \
		fi; \
	fi; \
	REPO=$$(gh repo view --json nameWithOwner --jq '.nameWithOwner'); \
	CURRENT_COMMIT=$$(git rev-parse HEAD); \
	echo "PR #$$PR_NUMBER"; \
	echo ""; \
	echo "================================================================================"; \
	echo "REGULAR PR COMMENTS (unaddressed only)"; \
	echo "================================================================================"; \
	echo ""; \
	TEMP_PR_COMMENTS=$$(mktemp); \
	gh pr view $$PR_NUMBER --json comments --jq '.comments[]? // empty | select(.isMinimized == false)' > "$$TEMP_PR_COMMENTS"; \
	PR_COMMENT_COUNT=$$(jq -s 'length' "$$TEMP_PR_COMMENTS"); \
	FOUND_UNADDRESSED_PR=false; \
	for i in $$(seq 0 $$((PR_COMMENT_COUNT - 1))); do \
		COMMENT_DATE=$$(jq -r -s ".[$${i}].createdAt" "$$TEMP_PR_COMMENTS"); \
		COMMITS_SINCE=$$(git log --since="$$COMMENT_DATE" --oneline); \
		if echo "$$COMMITS_SINCE" | grep -qi "addressed"; then \
			continue; \
		fi; \
		FOUND_UNADDRESSED_PR=true; \
		jq -r -s ".[$${i}] | \"Author: \(.author.login)\nDate: \(.createdAt)\nURL: \(.url)\n\n\(.body)\n\n\" + (\"─\" * 80) + \"\\n\"" "$$TEMP_PR_COMMENTS"; \
	done; \
	if [ "$$FOUND_UNADDRESSED_PR" = "false" ]; then \
		echo "All PR comments have been addressed! 🎉"; \
	fi; \
	rm -f "$$TEMP_PR_COMMENTS"; \
	echo ""; \
	echo "================================================================================"; \
	echo "REVIEW SUMMARIES (unaddressed only)"; \
	echo "================================================================================"; \
	echo ""; \
	TEMP_REVIEWS=$$(mktemp); \
	gh pr view $$PR_NUMBER --json reviews --jq '.reviews[]? // empty | select(.body != "" and (.isMinimized == false or .isMinimized == null))' > "$$TEMP_REVIEWS"; \
	REVIEW_COUNT=$$(jq -s 'length' "$$TEMP_REVIEWS"); \
	FOUND_UNADDRESSED_REVIEW=false; \
	for i in $$(seq 0 $$((REVIEW_COUNT - 1))); do \
		REVIEW_DATE=$$(jq -r -s ".[$${i}].submittedAt" "$$TEMP_REVIEWS"); \
		COMMITS_SINCE=$$(git log --since="$$REVIEW_DATE" --oneline); \
		if echo "$$COMMITS_SINCE" | grep -qi "addressed"; then \
			continue; \
		fi; \
		FOUND_UNADDRESSED_REVIEW=true; \
		jq -r -s ".[$${i}] | \"Reviewer: \(.author.login)\nState: \(.state)\nDate: \(.submittedAt)\n\n\(.body)\n\n\" + (\"─\" * 80) + \"\\n\"" "$$TEMP_REVIEWS"; \
	done; \
	if [ "$$FOUND_UNADDRESSED_REVIEW" = "false" ]; then \
		echo "All review summaries have been addressed! 🎉"; \
	fi; \
	rm -f "$$TEMP_REVIEWS"; \
	echo ""; \
	echo "================================================================================"; \
	echo "REVIEW COMMENTS (Line-level code comments - unaddressed only)"; \
	echo "================================================================================"; \
	echo ""; \
	TEMP_COMMENTS=$$(mktemp); \
	gh api --paginate repos/$$REPO/pulls/$$PR_NUMBER/comments > "$$TEMP_COMMENTS"; \
	COMMENT_COUNT=$$(jq 'length' "$$TEMP_COMMENTS"); \
	FOUND_UNADDRESSED=false; \
	for i in $$(seq 0 $$((COMMENT_COUNT - 1))); do \
		COMMENT_DATE=$$(jq -r ".[$${i}].created_at" "$$TEMP_COMMENTS"); \
		COMMITS_SINCE=$$(git log --since="$$COMMENT_DATE" --oneline); \
		if echo "$$COMMITS_SINCE" | grep -qi "addressed"; then \
			continue; \
		fi; \
		FOUND_UNADDRESSED=true; \
		jq -r ".[$${i}] | \"File: \(.path):\(.line // \"N/A\")\nAuthor: \(.user.login)\nDate: \(.created_at)\nURL: \(.html_url)\n\nContext (last 3 lines of diff):\n\(.diff_hunk | split(\"\n\") | .[-3:] | join(\"\n\"))\n\n\(.body)\n\n\" + (\"─\" * 80) + \"\\n\"" "$$TEMP_COMMENTS"; \
	done; \
	if [ "$$FOUND_UNADDRESSED" = "false" ]; then \
		echo "All review comments have been addressed! 🎉"; \
	fi; \
	rm -f "$$TEMP_COMMENTS"
