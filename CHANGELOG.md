# Changelog

All notable changes to CICADA will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-10-29

### Added

- **AI Keyword Extraction Enhancements**: Production-ready semantic search with improved NLP keyword extraction
  - BERT-based keyword extraction with KeyBERT integration for higher-quality semantic understanding
  - Configurable model tiers (`fast`, `regular`, `large`) to balance speed vs. accuracy
  - Wildcard pattern support in keyword search (`create*`, `*_user`)
  - Enhanced relevance scoring with confidence levels
- **Incremental Indexing System**: Smart change detection for lightning-fast reindexing
  - MD5-based file change detection - only processes modified files
  - 15-25x faster reindexing for typical workflows (5 files changed in 200-file codebase)
  - Especially valuable with keyword extraction: 2.1s instead of 48.7s (23.2x speedup)
  - Automatic hash computation and storage in `.cicada/hashes.json`
  - Graceful handling of new, modified, and deleted files
- **Interrupt Safety**: Production-grade Ctrl-C handling
  - Signal handlers (SIGINT, SIGTERM) for graceful shutdown
  - Saves partial progress automatically when interrupted
  - Resume capability - continue from where you left off
  - Double Ctrl-C for force quit when needed

- **Model Configuration Tracking**: Automatic detection and warning for model changes during incremental indexing
  - Tracks keyword extraction method (spaCy vs KeyBERT) and model tier in index metadata
  - Detects configuration changes and prompts user before proceeding
  - Interactive menu to choose: reindex with new model or keep existing index
  - Prevents inconsistent indexes with mixed model configurations
  - Falls back to text input when terminal menus unavailable
  - Fully backward compatible with existing indexes

### Changed

- Indexing workflow now uses incremental mode by default
  - First run: Full index with hash computation
  - Subsequent runs: Process only changed files
  - Use `--full` flag to force complete reindexing
- Keyword extraction now preserves method consistency across full/incremental runs
  - When switching between spaCy and BERT, use `--full` flag for consistent results

### Performance

- **Incremental indexing benchmarks** (200-file Phoenix app, 5 files changed):
  - Full index: 12.3s → Incremental: 0.8s (15.4x faster)
  - With keyword extraction: 48.7s → 2.1s (23.2x faster)
- Hash computation overhead: ~100ms for typical codebases (negligible)
- Interrupt and resume: No performance penalty for graceful shutdowns

## [0.1.1] - 2025-10

### Added

- **Core Search Features**:
  - Module and function search with AST-aware parsing
  - Call site tracking with intelligent alias resolution
  - Function signatures with full type specs and documentation
  - Public/private function filtering
  - Multiple output formats (Markdown, JSON)

- **Git History & Attribution**:
  - PR attribution via git blame integration + GitHub API
  - Line-level PR discovery with `find_pr_for_line` tool
  - File PR history with review comments and line mapping
  - Git commit history tracking with precise function-level tracking
  - Function evolution metadata (creation date, modification frequency)
  - Git blame integration with line-by-line authorship

- **Advanced Features**:
  - NLP-powered keyword search (EXPERIMENTAL) with spaCy integration
  - Semantic documentation search with relevance scoring
  - Dead code detection with three confidence levels (high, medium, low)
  - Smart callback and behavior detection
  - Test file filtering for focused usage analysis

- **Infrastructure & Tooling**:
  - Model Context Protocol (MCP) server integration
  - GraphQL-based PR indexing (30x faster than REST API)
  - Intelligent `.mcp.json` auto-configuration
  - `uv tool install` support for optimal installation
  - Automatic version update checking
  - Comprehensive CLI tools: `cicada`, `cicada-index`, `cicada-index-pr`, `cicada-find-dead-code`

- **Developer Experience**:
  - Function usage examples with actual code snippets
  - Module dependency and relationship mapping
  - Tree-sitter AST parsing for accurate code analysis
  - GitHub CLI integration for PR features

### Documentation

- Complete MCP Tools Reference documentation
- PR Indexing guide with GitHub CLI setup
- Extended Git History documentation
- Comprehensive README with installation and quick start guides

## [0.1.0] - Initial Release

### Added

- Initial release of CICADA
- Elixir-only support (Python and TypeScript planned)
- Basic module and function indexing
- Tree-sitter based AST parsing
- MCP server implementation

---

## Version Naming Scheme

- **Major versions (1.0, 2.0)**: Breaking changes, major architectural shifts
- **Minor versions (0.1, 0.2)**: New features, significant enhancements, backward compatible
- **Patch versions (0.1.1, 0.1.2)**: Bug fixes, minor improvements, documentation updates

## Links

- [GitHub Repository](https://github.com/wende/cicada)
- [Issues](https://github.com/wende/cicada/issues)
- [MCP Documentation](https://modelcontextprotocol.io)
