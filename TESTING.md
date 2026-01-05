# Testing Guide

Comprehensive testing guide for Cicada contributors and maintainers.

## Quick Start

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_indexer.py

# Run with coverage
pytest --cov=cicada tests/

# Run only fast tests (skip slow integration tests)
pytest -m "not slow"
```

**IMPORTANT:** Always use `make test`, never `pytest` directly, as the Makefile sets up the correct environment.

---

## Test Organization

### Test Categories

| Category | Location | Focus | Speed |
|----------|----------|-------|-------|
| **Unit** | `tests/*/test_*.py` | Individual functions/classes | Fast (<1s) |
| **Integration** | `tests/integration/` | Multiple components | Medium (1-5s) |
| **Acceptance** | `tests/acceptance/` | CLI commands | Medium (2-10s) |
| **Benchmark** | `tests/benchmark/` | Performance measurement | Slow (>10s) |

---

## Running Tests

### Local Development

```bash
# Quick test run during development
pytest tests/elixir/test_parser.py -v

# Test specific function
pytest tests/elixir/test_parser.py::test_parse_module -v

# Run with output (don't capture stdout)
pytest -s tests/mcp/test_server.py

# Run fast tests only
pytest -m "not slow"
```

### Pre-Commit Testing

Before committing:

```bash
# Run full test suite
make test

# Check code style
black --check cicada/ tests/

# Type checking
mypy cicada/
```

### CI/CD Testing

GitHub Actions automatically runs:
1. Full test suite on all Python versions (3.10, 3.11, 3.12)
2. Code coverage reporting
3. Integration tests with real SCIP indexers
4. Multi-editor setup tests

---

## Test Requirements

### Language-Specific Tests

#### Elixir Tests
- **Fixture:** `tests/fixtures/sample_*.ex`
- **Parser:** Tree-sitter based
- **Coverage:** Module extraction, function parsing, dependency tracking

#### Python Tests
- **Fixture:** `tests/fixtures/sample_python/`
- **Parser:** SCIP based
- **Requirements:** `scip-python` indexer (auto-installed)

#### Other SCIP Languages
- **Fixtures:** `tests/fixtures/sample_{go,rust,typescript,java,etc}/`
- **Requirements:** External SCIP indexers (tested in Docker)

### Docker Testing

For comprehensive language testing:

```bash
# Test all SCIP languages
make test-scip-docker

# Test specific language
docker build -f tests/docker/Dockerfile.python -t cicada-test-python .
docker run cicada-test-python
```

---

## Multi-Editor Testing

### Test Scenarios

#### Scenario 1: Sequential Setup (Claude → Cursor)

**Purpose:** Verify multiple editors can coexist

```bash
# Setup for Claude Code
cd tests/fixtures/example_project
cicada claude

# Verify .mcp.json created
test -f .mcp.json || echo "FAIL: .mcp.json missing"

# Setup for Cursor
cicada cursor

# Verify .cursor/mcp.json created
test -f .cursor/mcp.json || echo "FAIL: .cursor/mcp.json missing"

# Verify both use same storage
CLAUDE_STORAGE=$(jq -r '.mcpServers.cicada.env.CICADA_CONFIG_DIR' .mcp.json)
CURSOR_STORAGE=$(jq -r '.mcpServers.cicada.env.CICADA_CONFIG_DIR' .cursor/mcp.json)
test "$CLAUDE_STORAGE" = "$CURSOR_STORAGE" || echo "FAIL: Different storage"
```

#### Scenario 2: Complete Setup (All Three Editors)

**Purpose:** Verify all editors work simultaneously

```bash
cicada claude
cicada cursor
cicada vs

# Verify all configs exist
test -f .mcp.json && echo "✓ Claude Code"
test -f .cursor/mcp.json && echo "✓ Cursor"
test -f .vscode/settings.json && echo "✓ VS Code"
```

#### Scenario 3: Re-run Safety

**Purpose:** Verify idempotent setup (safe to run multiple times)

```bash
cicada claude
cicada claude  # Should not duplicate or corrupt

# Verify config still valid
jq empty .mcp.json || echo "FAIL: Invalid JSON"
```

### Test Coverage Matrix

| Test Case | Claude | Cursor | VS Code | Storage | Config Preserved |
|-----------|--------|--------|---------|---------|---------------------|
| Sequential Setup | ✅ | ✅ | - | ✅ | ✅ |
| All Three Editors | ✅ | ✅ | ✅ | ✅ | ✅ |
| Re-run Same Editor | ✅ | ✅ | ✅ | ✅ | ✅ |
| Preserve Other MCP | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## Manual Testing Checklist

### Before Each Release

#### Setup & Installation
- [ ] `cicada` - Interactive setup works
- [ ] `cicada .` - Current directory setup
- [ ] `cicada /path/to/project` - Different directory setup

#### Indexing
- [ ] `cicada index` - First-time indexing completes
- [ ] `cicada index` - Incremental indexing (run twice, second is faster)
- [ ] Modify 1-2 files, run `cicada index` - Only changed files reprocessed

#### PR Indexing
- [ ] `cicada index-pr` - PR indexing works (requires `gh` CLI)
- [ ] `cicada index-pr --clean` - Clean rebuild

#### MCP Server
Test via Claude Code or compatible MCP client:
- [ ] `search_module` - Find module works
- [ ] `search_function` - Find function with call sites
- [ ] `query` - Keyword search returns results
- [ ] `git_history` - File history shows PRs

#### Edge Cases
- [ ] Empty directory - Handles gracefully
- [ ] Non-git repository - Warns appropriately
- [ ] Large repository (>1000 files) - Completes successfully

---

## Test Fixtures

### Managing Test Data

```bash
# Create new test fixture
mkdir tests/fixtures/new_fixture
# Add sample files...

# Generate SCIP index for fixture
cd tests/fixtures/sample_python
scip-python index
# Creates index.scip

# Add to .gitignore if too large
echo "tests/fixtures/*/index.scip" >> .gitignore
```

### Fixture Organization

| Fixture | Purpose | Language | Size |
|---------|---------|----------|------|
| `sample.ex` | Basic Elixir | Elixir | Tiny |
| `sample_python/` | Python SCIP | Python | Small |
| `sample_typescript/` | TS/JS SCIP | TypeScript | Small |
| `sample_go/` | Go SCIP | Go | Small |
| `sample_rust/` | Rust SCIP | Rust | Small |

---

## Performance Benchmarking

### Benchmark Tool Usage

```bash
# Test specific prompt
python tests/benchmark/benchmark_mcp_tool_calls.py \
  --prompt "Show me the User module"

# Run test suite
python tests/benchmark/benchmark_mcp_tool_calls.py --test-suite

# List available test suites
python tests/benchmark/benchmark_mcp_tool_calls.py --list-suites
```

### Metrics Tracked

- Total tool calls per query
- Tool call breakdown by type
- Response duration
- Token usage estimation

---

## Coverage Requirements

### Minimum Coverage Targets

| Component | Target | Current |
|-----------|--------|---------|
| Core indexer | 80% | ✅ |
| MCP handlers | 75% | ✅ |
| Language parsers | 70% | ✅ |
| Overall project | 70% | ✅ |

### Viewing Coverage

```bash
# Generate coverage report
pytest --cov=cicada --cov-report=html tests/

# Open in browser
open htmlcov/index.html
```

---

## Continuous Integration

### GitHub Actions Workflows

#### Test Workflow (`.github/workflows/test.yml`)
- Runs on: Push, Pull Request
- Python versions: 3.10, 3.11, 3.12
- Tests: Full suite with coverage

#### SCIP Language Tests (`.github/workflows/test-scip-languages.yml`)
- Runs on: Pull Request
- Tests: All 13 SCIP languages in Docker
- Purpose: Verify external indexers work

### Running CI Tests Locally

```bash
# Simulate CI environment
docker run -it --rm \
  -v $(pwd):/workspace \
  python:3.11 \
  bash -c "cd /workspace && pip install -e . && make test"
```

---

## Debugging Tests

### Common Issues

#### Issue: Tests fail with "index.json not found"

**Cause:** Test ran without indexing fixture

**Solution:**
```bash
# Index the fixture first
cd tests/fixtures/sample_project
cicada index
cd -
pytest tests/integration/test_e2e.py
```

#### Issue: SCIP language tests skip

**Cause:** SCIP indexer not installed

**Solution:**
```bash
# Install required SCIP indexer
npm install -g @sourcegraph/scip-python

# Or run in Docker
make test-scip-docker
```

#### Issue: Tests hang or timeout

**Cause:** External process not terminating

**Solution:**
```bash
# Check for hung processes
ps aux | grep cicada-mcp

# Kill if needed
pkill -f cicada-mcp
```

---

## Adding New Tests

### Test Template

```python
def test_new_feature(tmp_path):
    """Test description following Google style.

    Args:
        tmp_path: Pytest fixture for temporary directory
    """
    # Arrange
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Act
    result = cicada.index(project_dir)

    # Assert
    assert result.success
    assert result.modules_count > 0
```

### Test Best Practices

1. **Use fixtures** for common setup
2. **Clean up** temporary files in teardown
3. **Mock external services** (GitHub API, npm, etc.)
4. **Test edge cases** explicitly
5. **Add docstrings** explaining test purpose

---

## Related Documentation

- [CONTRIBUTING.md](CONTRIBUTING.md) - Contributing guidelines
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [codebook/PERFORMANCE.md](codebook/PERFORMANCE.md) - Performance benchmarks

---

## Questions?

For testing-related questions:
- Check existing test files for examples
- Open GitHub issue with `[testing]` prefix
- Contact: @wende
