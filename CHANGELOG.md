# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GitHub Actions workflow for automated PyPI publishing ([#26](https://github.com/wende/cicada/pull/26))
- MIT License file for PyPI compliance ([#26](https://github.com/wende/cicada/pull/26))
- Enhanced pyproject.toml with complete package metadata for PyPI ([#26](https://github.com/wende/cicada/pull/26))

### Changed
- **BREAKING: Removed legacy `.cicada/` directory structure** - All indexes and hashes now stored in centralized `~/.cicada/projects/<repo_hash>/` location
  - Removed `cicada .` and `cicada <path>` direct indexing commands
  - Use `cicada claude`, `cicada cursor`, or `cicada vs` for setup
  - MCP server no longer supports old `.cicada/` path fallback
  - All CLI commands now use centralized storage by default

### Removed
- Legacy `install.py` module and related installation functions
- Backward compatibility for old `.cicada/` directory structure in MCP server
- Default `output_path` parameters in indexing functions (now required to be explicit)

## [0.2.0] - 2025-10-31

### Added

- **Unified CLI Interface** ([#18](https://github.com/wende/cicada/pull/18))
  - Consolidated all CLI commands into single `cicada` command with subcommands
  - New commands: `cicada index`, `cicada index-pr`, `cicada find-dead-code`
  - Backward compatibility maintained for `cicada` and `cicada ./path` setup
  - Added comprehensive CLI migration guide (docs/CLI_MIGRATION.md)

- **AI Keyword Extraction Enhancements** ([#14](https://github.com/wende/cicada/pull/14)): Production-ready semantic search with improved NLP keyword extraction
  - BERT-based keyword extraction with KeyBERT integration for higher-quality semantic understanding
  - Configurable model tiers (`fast`, `regular`, `max`) to balance speed vs. accuracy
  - New CLI flags: `--nlp` (spaCy-based) and `--rag` (BERT-based) for explicit extraction method selection
  - Model tier flags: `--fast` and `--max` to specify quality level
  - Replaced `--model-tier` and `--extract-keywords` with more intuitive flag system
  - Wildcard pattern support in keyword search (`create*`, `*_user`)
  - Enhanced relevance scoring with confidence levels
  - Lazy model downloads - only download when needed
  - Model caching for faster subsequent runs

- **Interactive Setup System**
  - Rich terminal menu interface for guided setup
  - Extraction method selection (lemminflect vs KeyBERT)
  - Model tier selection with descriptions
  - Fallback to text-based input for unsupported terminals
  - Error recovery with graceful degradation
  - ASCII art branding for better CLI experience

- **Incremental Indexing System**: Smart change detection for lightning-fast reindexing
  - MD5-based file change detection - only processes modified files
  - 15-25x faster reindexing for typical workflows (5 files changed in 200-file codebase)
  - Especially valuable with keyword extraction: 2.1s instead of 48.7s (23.2x speedup)
  - Automatic hash computation and storage in `~/.cicada/projects/<repo_hash>/hashes.json`
  - Graceful handling of new, modified, and deleted files

- **Interrupt Safety**: Production-grade Ctrl-C handling
  - Signal handlers (SIGINT, SIGTERM) for graceful shutdown
  - Saves partial progress automatically when interrupted
  - Resume capability - continue from where you left off
  - Double Ctrl-C for force quit when needed

- **Model Configuration Tracking**: Automatic detection and warning for model changes during incremental indexing
  - Tracks keyword extraction method (lemminflect vs KeyBERT) and model tier in index metadata
  - Detects configuration changes and prompts user before proceeding
  - Interactive menu to choose: reindex with new model or keep existing index
  - Prevents inconsistent indexes with mixed model configurations
  - Falls back to text input when terminal menus unavailable
  - Fully backward compatible with existing indexes

### Changed

- **CLI Command Structure** ([#18](https://github.com/wende/cicada/pull/18))
  - `cicada-index` → `cicada index`
  - `cicada-index-pr` → `cicada index-pr`
  - `cicada-find-dead-code` → `cicada find-dead-code`
  - Updated all documentation to reflect new command structure

- **Setup Workflow Improvements**
  - Streamlined setup UX with condensed output
  - Config.yaml created before indexing for proper method selection
  - Reduced redundant technical messages during setup
  - Improved progress reporting and status messages
  - Better handling of existing indexes (reuse without verbose output)

- **CLI Flag Changes**
  - Removed: `--model-tier` (replaced with `--fast`/`--max`)
  - Removed: `--extract-keywords` (replaced with `--nlp`/`--rag`)
  - Added: `--nlp` for spaCy-based keyword extraction
  - Added: `--rag` for BERT-based keyword extraction (RAG-optimized)
  - Added: `--fast` for fast model tier
  - Added: `--max` for maximum quality model tier
  - Default behavior: Interactive setup when no flags provided

- Indexing workflow now uses incremental mode by default
  - First run: Full index with hash computation
  - Subsequent runs: Process only changed files
  - Use `--full` flag to force complete reindexing

- Keyword extraction now preserves method consistency across full/incremental runs
  - When switching between lemminflect and BERT, use `--full` flag for consistent results
  - Indexer reads config.yaml to determine extraction method
  - Proper selection of BERT vs lemminflect based on setup choice

### Fixed

- **Security** ([#14](https://github.com/wende/cicada/pull/14))
  - Fixed command injection vulnerability in install.py
  - Replaced shell string commands with subprocess list arguments
  - Properly escaped repo_path and output_path variables

- **Build and CI**
  - Removed redundant extract-keywords target causing CI failures
  - Fixed test infrastructure for CI/CD environments
  - All tests now passing consistently (1099 tests)

- **Code Quality**
  - Fixed 50+ linting issues (PIE810, SIM102, SIM108, B904, E722, F841, etc.)
  - Consistent code formatting with black
  - Removed unused imports and variables
  - Improved exception handling with proper exception chaining

- **CLI and UX**
  - Fixed keyword extraction method selection (KeyBERT now properly used when selected)
  - Fixed color naming inconsistency (CYAN → ORANGE to match actual color)
  - Fixed Makefile reset target for better portability
  - Fixed inconsistent stderr output handling in verbose mode

### Testing

- **Coverage Improvements**: 70% → 83.37% coverage with 400+ new tests
  - cicada/cli.py: 92.83% coverage (37 new tests)
  - signature_builder.py: 65.79% → 100% coverage (20 new tests)
  - keyword_search.py: 53.07% → 97.81% coverage (33 new tests)
  - pr_finder.py: 64.85% → 85.15% coverage (31 new tests)
  - interactive_setup.py: 46.54% → 96.86% coverage (24 new tests)
  - extractors/base.py: 44.93% → 62.32% coverage (24 new tests)
  - text_utils.py: 100% coverage (new test file)
  - lightweight_keyword_extractor.py: 96.30% coverage (new test file)

- **New Test Files**
  - tests/test_cli.py - Comprehensive CLI handler tests
  - tests/test_keyword_search.py - Keyword search functionality
  - tests/test_signature_builder.py - Signature building logic
  - tests/test_pr_finder.py - Enhanced PR finder tests
  - tests/test_text_utils.py - Text utility functions
  - tests/test_lightweight_keyword_extractor.py - Lightweight extractor tests

- **Test Infrastructure**
  - Added pytest-xdist for parallel test execution
  - Improved test fixtures and mocking
  - Enhanced error handling test coverage
  - Edge case and unicode handling tests

### Documentation

- **New Documentation**
  - docs/CLI_MIGRATION.md - Complete guide for unified CLI transition
  - docs/BERT_KEYWORD_EXTRACTOR.md - BERT keyword extraction guide
  - docs/FEATURE_MODEL_TRACKING.md - Model tracking feature documentation
  - docs/MODEL_CHANGE_DETECTION.md - Model change detection guide
  - docs/MCP_TOOLS_REFERENCE.md - MCP tools reference documentation
  - OBJECTIVE_MERGE.md - Merge investigation documentation

- **Updated Documentation**
  - README.md - Updated all commands to use unified CLI syntax
  - docs/INCREMENTAL_INDEXING.md - Updated with new command structure
  - extensions/claude-code/INSTALL.md - Updated installation instructions
  - All examples now use `cicada index` instead of `cicada-index`

### Performance

- **Incremental indexing benchmarks** (200-file Phoenix app, 5 files changed):
  - Full index: 12.3s → Incremental: 0.8s (15.4x faster)
  - With keyword extraction: 48.7s → 2.1s (23.2x faster)
- Hash computation overhead: ~100ms for typical codebases (negligible)
- Interrupt and resume: No performance penalty for graceful shutdowns
- Model caching reduces subsequent BERT extraction runs by 40-60%

### Dependencies

- **Added**
  - keybert - BERT-based keyword extraction
  - sentence-transformers - For semantic embeddings
  - simple-term-menu - Interactive terminal menus
  - pytest-xdist - Parallel test execution

- **Updated**
  - pyproject.toml restructured for uv package manager
  - Consolidated dependency groups under [dependency-groups]
  - Removed duplicate optional dependencies section

## [0.1.2] - 2025-01-XX

### Added
- `cicada-clean` command to remove repository configuration and clean up MCP settings ([#24](https://github.com/wende/cicada/pull/24))
- Automated MCP tool call benchmarking system for performance analysis ([#23](https://github.com/wende/cicada/pull/23))
- Command logging for cicada-mcp MCP operations ([#22](https://github.com/wende/cicada/pull/22))
- Auto-setup functionality to cicada-mcp for zero-config MCP usage ([#20](https://github.com/wende/cicada/pull/20))
- Simplified single-command setup workflow (`cicada claude`, `cicada cursor`, `cicada vs`) ([#20](https://github.com/wende/cicada/pull/20))
- Centralized storage structure in `~/.cicada/projects/<repo_hash>/` ([#20](https://github.com/wende/cicada/pull/20))
- Incremental indexing with hash-based change detection for faster re-indexing ([#16](https://github.com/wende/cicada/pull/16))
- Dead code analysis feature (`find_dead_code` MCP tool and CLI command) ([#8](https://github.com/wende/cicada/pull/8))
- Keyword search functionality with NLP-based semantic search (experimental) ([#11](https://github.com/wende/cicada/pull/11))
- Claude Code GitHub Workflow for CI ([#15](https://github.com/wende/cicada/pull/15))

### Changed
- Positioned `uvx` as trial option with permanent installation as recommended method ([#20](https://github.com/wende/cicada/pull/20))
- Storage structure now centralized outside repository (backward compatible with old `.cicada/` structure) ([#20](https://github.com/wende/cicada/pull/20))
- Improved error handling and test coverage across codebase ([#20](https://github.com/wende/cicada/pull/20), [#10](https://github.com/wende/cicada/pull/10), [#7](https://github.com/wende/cicada/pull/7))
- Consolidated and cleaned up Cursor-generated code ([#13](https://github.com/wende/cicada/pull/13))

### Fixed
- Test fixture directory detection in Makefile now works dynamically
- Unused imports and test failures resolved ([#12](https://github.com/wende/cicada/pull/12))
- Multiple linting issues addressed ([#13](https://github.com/wende/cicada/pull/13))

### Documentation
- Added comprehensive workflow documentation for simplified setup ([#20](https://github.com/wende/cicada/pull/20))
- Added MCP extension deployment strategy and objectives ([#19](https://github.com/wende/cicada/pull/19))
- Added executable bundling research documentation ([#21](https://github.com/wende/cicada/pull/21))
- Updated README with new setup workflow and storage structure ([#20](https://github.com/wende/cicada/pull/20))

## [0.1.1] - 2024-10-XX

### Added
- Coverage reporting to CI workflow ([#3](https://github.com/wende/cicada/pull/3))
- Comprehensive testing for multiple modules ([#10](https://github.com/wende/cicada/pull/10), [#7](https://github.com/wende/cicada/pull/7))

### Changed
- Refactored and extracted utilities from pr_indexer module ([#2](https://github.com/wende/cicada/pull/2))
- Improved project organization and code structure ([#2](https://github.com/wende/cicada/pull/2))

### Fixed
- Coverage configuration and reporting issues ([#6](https://github.com/wende/cicada/pull/6))

### Documentation
- Updated documentation for v0.1.0 release ([#9](https://github.com/wende/cicada/pull/9))
- Marketing improvements and gitignore updates ([#5](https://github.com/wende/cicada/pull/5))

## [0.1.0] - 2024-10-XX

### Added
- Initial release of CICADA
- Module and function search functionality
- Call site tracking with alias resolution
- PR attribution via git blame + GitHub integration
- PR review comments with line mapping
- File PR history with descriptions
- GraphQL-based PR indexing (30x faster than REST API)
- Function usage examples with code snippets
- Git commit history tracking with precise function tracking
- Function evolution metadata (creation, modifications, frequency)
- Git blame integration with line-by-line authorship
- Test file filtering in function searches
- Multiple output formats (markdown, JSON)
- Intelligent `.mcp.json` auto-configuration
- `uv tool install` support for modern Python tooling
- Automatic version update checking
- MCP server implementation with 9 specialized tools:
  - `search_module` - View module APIs with signatures and docs
  - `search_function` - Find function definitions and call sites
  - `search_module_usage` - Track module dependencies
  - `find_pr_for_line` - Line-level PR attribution
  - `get_file_pr_history` - Complete PR history for files
  - `get_commit_history` - Track file and function evolution
  - `get_blame` - Line-by-line code ownership
  - `search_by_keywords` - Semantic documentation search
  - `find_dead_code` - Identify unused functions
- CLI tools:
  - `cicada` - Project initialization
  - `cicada-mcp` - MCP server
  - `cicada-index` - Code indexing
  - `cicada-index-pr` - PR indexing
  - `cicada-find-dead-code` - Dead code analysis

### Documentation
- Comprehensive README with installation instructions
- MCP Tools Reference documentation
- PR Indexing documentation
- Troubleshooting guide
- Contributing guidelines

---

## Version Naming Scheme

- **Major versions (1.0, 2.0)**: Breaking changes, major architectural shifts
- **Minor versions (0.1, 0.2)**: New features, significant enhancements, backward compatible
- **Patch versions (0.1.1, 0.1.2)**: Bug fixes, minor improvements, documentation updates

## Links

- [GitHub Repository](https://github.com/wende/cicada)
- [Issues](https://github.com/wende/cicada/issues)
- [MCP Documentation](https://modelcontextprotocol.io)

[Unreleased]: https://github.com/wende/cicada/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/wende/cicada/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/wende/cicada/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/wende/cicada/releases/tag/v0.1.0
