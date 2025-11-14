# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.2] - 2025-11-14

### Added

- **String-based keyword indexing** ([#108](https://github.com/wende/cicada/pull/108)) - Index and search string literals from function bodies
  - New `match_source` parameter for `search_by_keywords` tool ('all', 'docs', 'strings')
  - Visual indicators in results (📄 for docs, 💬 for strings, 📄💬 for both)
  - 1.3x keyword weight boost for string literals vs documentation
  - Search SQL queries, error messages, log statements, and other string content
- **Repository linking system** ([#93](https://github.com/wende/cicada/pull/93)) - Share indices between repositories
  - `cicada link <source>` - Link current repo to source repo's index
  - `cicada link --to <target> <source>` - Link target to source
  - `cicada unlink` - Remove link from repository
  - `cicada dir` - Shows link info if repository is linked
  - Useful for monorepos, testing, and development scenarios
  - Circular link detection and broken link validation
- **Status command** ([#104](https://github.com/wende/cicada/pull/104)) - New `cicada status` command for diagnostic information
  - Shows index status (tier/models, build date, file size)
  - Shows PR index status
  - Lists agent files with cicada references
  - Lists MCP config files
- **Quick initialization flag** ([#102](https://github.com/wende/cicada/pull/102)) - New `--default` flag for `cicada index` command
  - Non-interactive initialization with default values
  - Equivalent to `--force --fast`
  - Uses REGULAR extraction + LEMMI expansion

### Changed

- **MCP tool API enhancement** ([#109](https://github.com/wende/cicada/pull/109)) - Added `module_path` parameter to `search_function` tool
  - Supports both qualified and separate module/function calling conventions
  - Handles OR patterns correctly with automatic qualification

### Fixed

- **MCP server reconnection issues** ([#106](https://github.com/wende/cicada/pull/106)) - Added signal handlers for clean shutdown
  - Prevents zombie process accumulation
  - Clears Python bytecode cache to avoid stale .pyc issues
- **PR count accuracy** ([#103](https://github.com/wende/cicada/pull/103)) - Use exact GraphQL query instead of approximation
  - Now includes OPEN, CLOSED, and MERGED PRs
  - Fixes incorrect partial fetch detection in incremental updates
- **Setup UX** ([#106](https://github.com/wende/cicada/pull/106)) - Removed confusing "Step 1/4" label from editor selection

## [0.3.1] - 2025-11-11

### Added

- **Automatic output truncation** ([#97](https://github.com/wende/cicada/pull/97)) - Intelligent truncation across MCP tools to prevent token overflow
  - Conservative thresholds: 30 line numbers, 20 call sites, 50-line code blocks, 300-char commit messages
  - Automatic indicators like "... (47 more)" for truncated content
  - 52 comprehensive unit tests with >90% coverage
- **Automatic index reloading** ([#91](https://github.com/wende/cicada/pull/91)) - MCP server now detects and reloads indexes when files change
  - Eliminates need to restart server after reindexing
  - Graceful handling of concurrent reindexing operations
- **OpenCode editor support** ([#92](https://github.com/wende/cicada/pull/92)) - Support for OpenCode editor integration
- **Enhanced interactive setup menu** ([#94](https://github.com/wende/cicada/pull/94)) - Added Gemini CLI and Codex editor options to setup workflow

### Changed

- **MCP server architecture refactored** ([#96](https://github.com/wende/cicada/pull/96)) - Modular handler architecture for better maintainability
  - Split monolithic server.py into separate handler modules
  - New modules: config_manager.py, index_manager.py, router.py, handlers/
  - Improved testability and code organization
- **Enhanced MCP output formatting** ([#97](https://github.com/wende/cicada/pull/97)) - Improved readability and usability
  - Compact module format for wildcard searches (4+ results)
  - Restructured module usage display with calling function context
  - Compact git history format without full commit messages
  - Compact git blame format (`:150-156 • author • sha • date`)
  - Improved function search output with triple-quoted docs
  - 20-module limit for wildcard searches with helpful messaging
- **Parameter standardization** ([#97](https://github.com/wende/cicada/pull/97))
  - Renamed `private_functions` to `visibility` across module search operations
  - New values: "public" (default), "private", "all" (was "exclude", "only", "include")
  - Replaced `test_files_only` boolean with `usage_type` enum (all/tests/source)
  - Source files now default filter (excluding tests)
  - Backward compatibility maintained for deprecated parameters
- **Code cleanup** ([#97](https://github.com/wende/cicada/pull/97), [#95](https://github.com/wende/cicada/pull/95)) - Reduced ~110 lines of duplicated code
  - Extracted helper functions for common operations
  - Removed all emojis from output messages
  - Fixed linter warnings and improved code consistency

### Fixed

- **Index caching issue** ([#91](https://github.com/wende/cicada/pull/91)) - Server was using stale data after reindexing until restart
- **Race condition during concurrent reindexing** ([#91](https://github.com/wende/cicada/pull/91)) - Graceful handling when index is being written
- **OpenCode configuration path** - Fixed OpenCode to use `.mcp.json` instead of `.opencode.json` to match Claude Code convention

## [0.3.0] - 2025-11-10

### Search & Filtering Enhancements

- **Time-based function filtering** ([#88](https://github.com/wende/cicada/pull/88), [#90](https://github.com/wende/cicada/pull/90)) - Find functions modified within a specific timeframe
- **Wildcard and OR pattern support** ([#73](https://github.com/wende/cicada/pull/73)) - Search using patterns like wildcards and OR operators
- **Score threshold filtering** ([#90](https://github.com/wende/cicada/pull/90)) - Filter keyword search results by minimum relevance score
- **Usage type filtering** ([#90](https://github.com/wende/cicada/pull/90)) - Filter module usage by all/test_only/production_only
- **Time and author filters for commit history** ([#90](https://github.com/wende/cicada/pull/90)) - Filter commits by date range and author

### Dependency & Relationship Analysis

- **Module and function dependency tools** ([#87](https://github.com/wende/cicada/pull/87)) - Discover what modules and functions depend on
- **Transitive dependency analysis** ([#87](https://github.com/wende/cicada/pull/87)) - Trace dependencies across multiple levels
- **Inline relationship display** ([#90](https://github.com/wende/cicada/pull/90)) - View relationships directly in search results
- **Granular module dependencies** ([#90](https://github.com/wende/cicada/pull/90)) - Track dependencies at the function level

### Developer Experience & Tooling

- **Watch mode for automatic reindexing** ([#52](https://github.com/wende/cicada/pull/52)) - Automatically reindex when files change
- **Redesigned interactive setup** ([#81](https://github.com/wende/cicada/pull/81)) - Streamlined setup with tier-based selection
- **Enhanced MCP tool discoverability** ([#70](https://github.com/wende/cicada/pull/70)) - Smart error messages and staleness warnings
- **Enhanced proactive PR suggestions** ([#88](https://github.com/wende/cicada/pull/88), [#90](https://github.com/wende/cicada/pull/90)) - Contextual prompts when information is unavailable

### Editor & CLI Integration

- **Gemini CLI and Codex editor support** ([#82](https://github.com/wende/cicada/pull/82)) - Support for two additional code editors
- **CLI entrypoint consolidation** ([#83](https://github.com/wende/cicada/pull/83)) - Unified command structure across all CLI commands

### Removed

- **CICADA_REPO_PATH environment variable** ([#85](https://github.com/wende/cicada/pull/85)) - Simplified to use only CICADA_CONFIG_DIR for configuration

### Fixed

- **Git blame parsing with repeated commits** ([#88](https://github.com/wende/cicada/pull/88), [#90](https://github.com/wende/cicada/pull/90)) - Fixed errors when consecutive lines from same commit
- **Dependency analysis null safety** ([#90](https://github.com/wende/cicada/pull/90)) - Prevent errors when call sites have missing line numbers

## [0.2.3] - 2025-11-03

### Fixed

- **CLAUDE.md Update Functionality**
  - Restored `update_claude_md()` function that was removed when `install.py` was deleted
  - Function now integrated into `cicada/setup.py` and called during Claude Code setup
  - Auto-generates tool descriptions from `get_tool_definitions()` in `cicada/mcp/tools.py`
  - Handles three cases: replaces existing `<cicada>` tags, skips if "cicada" already mentioned, or appends new section
  - Added comprehensive test coverage (13 new tests in `tests/test_claude_md_update.py` and `tests/test_setup.py`)

- **Version Tracking Improvements**
  - Removed git command fallback from version_check functions for more reliable version detection
  - Added cicada version tracking and mismatch detection between installed and available versions
  - Fixed version reporting for `cicada-mcp` command to properly display version, tag, and commit hash

## [0.2.2] - 2025-11-02

### Added

- **Result Type Filtering for `search_by_keywords`**
  - New `filter_type` parameter: `'all'` (default), `'modules'`, or `'functions'`
  - Allows users to filter semantic search results to only modules or only functions
  - Useful for narrowing searches when looking for specific code patterns

### Changed

- Updated all user-facing documentation to use new CLI flag names (`--fast`, `--regular`, `--max`)
  - Replaced outdated `--nlp` and `--rag` references across 5 documentation files
  - Clarified extraction method names in INCREMENTAL_INDEXING.md, MODEL_CHANGE_DETECTION.md, CLI_MIGRATION.md, FEATURE_MODEL_TRACKING.md, and BERT_KEYWORD_EXTRACTOR.md

### Fixed

- Improved documentation consistency across all keyword extraction and model tier references

## [0.2.0] - 2025-11-01

### Added

- **Unified CLI Interface** ([#18](https://github.com/wende/cicada/pull/18))
  - Consolidated all CLI commands into single `cicada` command with subcommands
  - New commands: `cicada index`, `cicada index-pr`, `cicada find-dead-code`
  - Backward compatibility maintained for `cicada` and `cicada ./path` setup
  - Added comprehensive CLI migration guide (docs/CLI_MIGRATION.md)

- **Simplified Tier-Based Model Selection** ([#49](https://github.com/wende/cicada/pull/49), [#14](https://github.com/wende/cicada/pull/14))
  - Three-tier system: `--fast` (no downloads), `--regular` (128MB, default), `--max` (958MB+)
  - Fast tier: Regular extraction + lemminflect expansion (zero downloads)
  - Regular tier: KeyBERT small + GloVe expansion (balanced quality/size)
  - Max tier: KeyBERT large + FastText expansion (maximum quality)
  - BERT-based keyword extraction with KeyBERT integration for higher-quality semantic understanding
  - Lazy model downloads - only download when needed
  - Model caching for faster subsequent runs

- **Configurable Search Thresholds** ([#49](https://github.com/wende/cicada/pull/49))
  - `--extraction-threshold` (default: 0.3) for semantic similarity filtering
  - `--min-score` (default: 0.5) for minimum keyword quality
  - `--expansion-threshold` (default: 0.2) for keyword expansion sensitivity
  - Wildcard pattern support in keyword search (`create*`, `*_user`)
  - Enhanced relevance scoring with confidence levels

- **Interactive Keyword Testing Modes**
  - `cicada index --test` for testing keyword extraction
  - `cicada index --test-expansion` for testing keyword expansion
  - Fine-tune parameters before full indexing

- **Enhanced Clean Command**
  - Granular cleanup: `--index` (main index), `--pr-index` (PR index only)
  - `--all` flag to remove all Cicada storage across all projects
  - `-f/--force` flag to skip confirmation prompts

- **PR Index Rebuild Support**
  - `cicada index-pr --clean` flag for full PR index rebuild
  - Complements incremental update mode with clean slate option

- **Two-Stage Keyword Extraction System** ([#43](https://github.com/wende/cicada/pull/43), [#42](https://github.com/wende/cicada/pull/42))
  - Separate extraction and expansion methods for better semantic search
  - Improved compound word handling in semantic lookups
  - Reorganized codebase into cleaner package structure

- **Version Tracking** (807108f)
  - `--version` / `-v` flag to display version, git tag, and commit hash
  - Helps distinguish PyPI releases from development builds

- **Acceptance Testing Framework** ([#45](https://github.com/wende/cicada/pull/45))
  - Automated acceptance test suite for MCP tools and CLI commands

- GitHub Actions workflow for automated PyPI publishing ([#26](https://github.com/wende/cicada/pull/26))
- MIT License file for PyPI compliance ([#26](https://github.com/wende/cicada/pull/26))

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

- **Improved Search Result Formatting** ([#47](https://github.com/wende/cicada/pull/47))
  - More compact and scannable keyword search results
  - Cleaner documentation previews

- **Setup Workflow Improvements**
  - Streamlined setup UX with condensed output
  - Config.yaml created before indexing for proper method selection
  - Reduced redundant technical messages during setup
  - Improved progress reporting and status messages
  - Better handling of existing indexes (reuse without verbose output)

- **BREAKING: Removed legacy `.cicada/` directory structure** - All indexes and hashes now stored in centralized `~/.cicada/projects/<repo_hash>/` location
  - Removed `cicada .` and `cicada <path>` direct indexing commands
  - Use `cicada claude`, `cicada cursor`, or `cicada vs` for setup
  - MCP server no longer supports old `.cicada/` path fallback

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

- Test infrastructure improvements preventing unwanted test artifacts ([#47](https://github.com/wende/cicada/pull/47))
- Type checking and API consistency improvements ([#43](https://github.com/wende/cicada/pull/43))

### Removed

- Legacy `.cicada/` directory structure and backward compatibility
- `--model-tier` and `--extract-keywords` flags (replaced by `--fast`/`--regular`/`--max` tier system)

### Documentation

- **New Documentation**
  - docs/CLI_MIGRATION.md - Complete guide for unified CLI transition
  - docs/BERT_KEYWORD_EXTRACTOR.md - BERT keyword extraction guide
  - docs/FEATURE_MODEL_TRACKING.md - Model tracking feature documentation
  - docs/MODEL_CHANGE_DETECTION.md - Model change detection guide
  - MCP_TOOLS_REFERENCE.md - MCP tools reference documentation
  - OBJECTIVE_MERGE.md - Merge investigation documentation

- **Updated Documentation**
  - README.md - Updated all commands to use unified CLI syntax
  - docs/INCREMENTAL_INDEXING.md - Updated with new command structure
  - extensions/claude-code/INSTALL.md - Updated installation instructions
  - All examples now use `cicada index` instead of `cicada-index`

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

## [0.1.2] - 2025-10-30

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

## [0.1.1] - 2025-10-26

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

## [0.1.0] - 2025-10-25

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

[Unreleased]: https://github.com/wende/cicada/compare/v0.3.2...HEAD
[0.3.2]: https://github.com/wende/cicada/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/wende/cicada/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/wende/cicada/compare/v0.2.3...v0.3.0
[0.2.3]: https://github.com/wende/cicada/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/wende/cicada/compare/v0.2.0...v0.2.2
[0.2.0]: https://github.com/wende/cicada/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/wende/cicada/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/wende/cicada/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/wende/cicada/releases/tag/v0.1.0
