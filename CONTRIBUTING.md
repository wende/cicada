# Contributing to Cicada

Thank you for your interest in contributing to Cicada! This guide will help you get started.

---

## Quick Links

- **[Testing Guide](TESTING.md)** - Running tests, test organization, multi-editor testing
- **[Architecture Overview](ARCHITECTURE.md)** - Project structure and design decisions
- **[Publishing Guide](PUBLISHING.md)** - Distribution and release process (maintainers only)
- **[Installation Guide](codebook/INSTALLATION.md)** - User-facing installation documentation

---

## Development Setup

### Prerequisites

- Python 3.10+
- `uv` package manager
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/wende/cicada.git
cd cicada

# Install in development mode
make dev

# Verify installation
cicada --version
```

---

## Making Changes

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes

- Follow the code style guidelines below
- Add tests for new features
- Update documentation as needed

### 3. Run Tests

**IMPORTANT:** Always use `make test`, never `pytest` directly.

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_indexer.py

# Run with coverage
pytest --cov=cicada tests/
```

See [TESTING.md](TESTING.md) for comprehensive testing guidelines including:
- Test organization and structure
- Multi-editor testing scenarios
- Coverage requirements
- Manual testing checklist

### 4. Submit a Pull Request

- Write a clear PR description
- Reference any related issues
- Ensure all tests pass
- Respond to review feedback

---

## Code Style Guidelines

### Python Code

- **Formatter:** Use `black` for consistent formatting
- **Type Hints:** Include type hints where appropriate
- **Docstrings:** Use Google-style docstrings for functions and classes

```bash
# Format code
black cicada/ tests/

# Check formatting
black --check cicada/ tests/

# Type checking
mypy cicada/
```

### Commit Messages

- Use clear, descriptive commit messages
- Start with a verb in present tense (e.g., "Add", "Fix", "Update")
- Reference issue numbers when applicable

**Examples:**
```
Add support for Erlang language parsing
Fix incremental indexing for large files
Update CLI help text for clarity
```

---

## Project Architecture

Understanding Cicada's architecture will help you contribute more effectively.

### Core Concepts

- **Hybrid Parsing:** Tree-sitter (Elixir, Erlang) + SCIP (13 other languages)
- **Incremental Indexing:** Only reindex changed files using SHA-256 hashing
- **Optional Dependencies:** cicada-core (required) + cicada-scip (optional)
- **MCP Protocol:** JSON-RPC server for AI coding assistants

### Project Structure

```
cicada/
├── cicada/                    # Main package
│   ├── mcp/                   # MCP server implementation
│   ├── languages/             # Language-specific parsers
│   ├── git/                   # Git history & PR indexing
│   └── utils/                 # Shared utilities
├── packages/                  # Monorepo packages
├── codebook/                  # User documentation
├── tests/                     # Test suite
└── Makefile                   # Development commands
```

For detailed architecture information, see [ARCHITECTURE.md](ARCHITECTURE.md) and [codebook/ARCHITECTURE.md](codebook/ARCHITECTURE.md).

---

## Testing Requirements

### Test Coverage

Minimum coverage targets:
- Core indexer: 80%
- MCP handlers: 75%
- Language parsers: 70%
- Overall project: 70%

### Test Categories

| Category | Location | Focus | Speed |
|----------|----------|-------|-------|
| **Unit** | `tests/*/test_*.py` | Individual functions | Fast (<1s) |
| **Integration** | `tests/integration/` | Multiple components | Medium (1-5s) |
| **Acceptance** | `tests/acceptance/` | CLI commands | Medium (2-10s) |
| **Benchmark** | `tests/benchmark/` | Performance | Slow (>10s) |

For complete testing documentation, see [TESTING.md](TESTING.md).

---

## Documentation

### Where to Add Documentation

- **User-facing features:** Add to `codebook/` directory
- **Development guides:** Add to root-level (e.g., TESTING.md, ARCHITECTURE.md)
- **API documentation:** Include in code docstrings

### Documentation Style

- Use clear, concise language
- Include code examples where appropriate
- Link to related documentation
- Keep README.md indexes up to date

---

## Adding Language Support

### Tree-sitter Languages

For languages without SCIP indexers:

1. Add tree-sitter grammar to `cicada/languages/`
2. Implement parser in `cicada/languages/<language>/parser.py`
3. Extract modules, functions, and documentation
4. Add tests in `tests/<language>/`

### SCIP Languages

For languages with existing SCIP indexers:

1. Verify SCIP indexer quality with sample projects
2. Add language detection to `cicada/languages/scip/converter.py`
3. Test with real-world codebases
4. Document in `codebook/LANGUAGE_SUPPORT.md`

**Estimated effort:**
- Tree-sitter: 12-17 days (custom parser implementation)
- SCIP: 4-6 days (universal converter + testing)

---

## Publishing (Maintainers Only)

For information on publishing releases to PyPI and other distribution channels, see [PUBLISHING.md](PUBLISHING.md).

### Release Checklist

Before publishing a new version:

- [ ] Run full test suite: `make test`
- [ ] Update `CHANGELOG.md` with changes
- [ ] Bump version in `pyproject.toml`
- [ ] Test installation in clean environment
- [ ] Verify all links in README work

---

## Getting Help

- **Questions:** Open a GitHub issue with the `question` label
- **Bug Reports:** Use the bug report template
- **Feature Requests:** Use the feature request template
- **Security Issues:** Email security@cicada-mcp.dev (if applicable) or open a private security advisory

---

## License

By contributing to Cicada, you agree that your contributions will be licensed under the same license as the project.

---

## Code of Conduct

Be respectful and constructive in all interactions. We're here to build great software together.

---

Thank you for contributing to Cicada! 🎉
