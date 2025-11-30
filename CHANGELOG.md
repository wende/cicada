# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.2] - 2025-11-30

### Fixed

**Incremental Indexing Race Conditions (#206)**
- Add reindex lock to prevent concurrent indexing in watcher
- Fix hash path format mismatch (accept both dir and file paths)
- Compute hashes once at start to fix pending reindex race condition
- Prevent concurrent repository reindex operations with lock release on errors
- Eliminate race conditions by computing file hashes once at start and reusing them

**Co-change Analysis Performance (#200)**
- Fix performance explosion in co-change analysis
- Optimized algorithm to prevent exponential time complexity

**Legacy Path References (#197)**
- Fix legacy .cicada/index.json path references
- Update indexer.py CLI to use get_index_path() for centralized storage

**Watcher Language Detection (#199)**
- Fix watcher to use LanguageRegistry.get_indexer() based on detected project language
- Remove forced version mismatch reindexing

### Improvements

**Partial SCIP Indexing (#206)**
- Add --target-only support for partial SCIP indexing on changed directories
- Skip keyword extraction and timestamp computation for unchanged modules
- Copy existing keywords/timestamps from previous index for unchanged files
- Compute minimal common target directory for changed Python files
- Add verbose logging for incremental indexing with reused data statistics

**Test Infrastructure (#201, #204)**
- Sandbox test targets to avoid modifying global cicada installation
- Clean up long-running tests to improve CI performance
- Update and extend Python indexer tests for hash-based change detection

**Automatic Fallback Searches (#198)**
- When a function search fails, automatically try relaxed searches
- Without module qualifier, without arity constraint, or private function variant
- Results include notes explaining which fallback was used
- Improved semantic search suggestions by splitting function names into keywords

### Features

**Erlang Language Support (#183)**
- Full Erlang code indexing via tree-sitter parsing
- Extract modules, functions, arity, line numbers, and visibility
- EDoc extraction with keyword search support (@doc, @param, @returns tags)
- Erlang notation formatting (module:func/arity)
- Automatic language detection via rebar.config, erlang.mk, or src/*.erl
- Tested on PURITY and cowboy

**CLI Tool Execution (#202)**
- Add `cicada run [tool]` command to execute all MCP tools from CLI
- Tools can be run identically to their MCP behavior directly from command line

**Universal Visibility Field (#205)**
- Add normalized 'visibility' field ('public'/'private') separate from language-specific 'type' field
- Enables consistent public/private classification across all supported languages
- Backward compatible with existing indexes

**Language-Specific Function Formatters (#203)**
- Add format_function_name() to language formatter interface
- Elixir: show args if available, otherwise /arity notation
- Python: show args filtering out self/cls/arg0 implicit params
- Erlang: use /arity notation (module:func/arity)

**Multithreaded Indexing (#195)**
- Parallel file processing during indexing for significant performance improvements
- Faster index builds especially on larger codebases

**Language-Agnostic Watcher (#199)**
- Watcher now uses LanguageRegistry to detect project language automatically
- Renamed ElixirFileEventHandler to SourceFileEventHandler with configurable extensions
- Added fallback to index_repository() for indexers without incremental support
- Shows detected language and watched file extensions in output

### Improvements

**Code Refactoring (#196)**
- Extract shared helpers for keyword extraction, git timestamps, and module building
- Refactor indexer to use shared helpers, eliminating ~200 lines of duplication
- Extract handler methods from route_tool for better maintainability
- Net reduction: -670 lines of code

### Fixed (from v0.5.1)

**Graceful Shutdown for Ctrl+C (#193)**
- Fixed graceful shutdown during indexing when interrupted with Ctrl+C

**Duplicate Git Helper Initialization (#196)**
- Fix duplicate git_helper initialization bug in incremental indexer

## [0.5.1] - 2025-11-28

### Features

**Stats and Usage Tracking (#189)**
- Add `cicada stats` command to display per-project usage statistics
- Track all MCP tool executions with accurate token counting
- Support multiple output formats: summary (default), detailed, time-series, JSON
- Add filtering by tool, date range, and time period
- Include project statistics (modules, functions, keywords) in output
- Add reset functionality to manage log files

**CLI Tool Execution (#187)**
- Add `cicada run [tool]` command to execute all 7 MCP tools from CLI
- Tools can be run identically to their MCP behavior directly from command line

**Agent Installation (#188)**
- Add `cicada agents install` command to programmatically install Claude Code agents
- Installs agents locally to `./.claude/` directory (project-scoped)
- Starts with cicada-code-explorer agent

**Link Status Tracking (#182)**
- Add bidirectional link tracking: `cicada link` now registers reverse links
- Add "LINK STATUS" section to `cicada status` showing:
  - Forward links (repos this one links to)
  - Reverse links (repos linking to this one)
  - Stale link detection with reasons

**Automatic Index Refresh (#185)**
- Add automatic background index refresh for MCP server
- Add `refresh_index` tool for manual index refresh
- Add debouncing (2s) and cooldown (15s) to prevent excessive refreshes
- Add graceful shutdown to stop pending refresh operations

**Graceful Ctrl+C Shutdown (#191)**
- Ctrl+C during indexing now exits cleanly instead of crashing
- Python indexer saves partial progress when interrupted during enrichment phases
- Elixir saves partial progress, Python saves after SCIP conversion completes

### Improvements

**Co-change Analysis Optimization (#190)**
- 15-20x faster co-change analysis (60-120s → ~1s for typical repos)
- Now enabled by default during indexing
- Add `--no-cochange` CLI flag to disable if needed
- Display "Often Changed With" section in module search output

**Compact Output Mode (#186)**
- Add compact output mode for all MCP tools to reduce token usage
- `query`: Compact keyword indicators (d)/(s)/(d+s), confidence only in verbose mode
- `search_module`: Hide moduledoc and specs by default, add verbose parameter
- `search_function`: Hide docs and specs by default, add verbose parameter
- `git_history`: Compact PR output (single line), descriptions only when requested
- `expand_result`: Auto-enables verbose mode for full details

**CLI Progress Reporting (#192)**
- CLI index/watch commands now show progress by default
- Add `--quiet` flag for background watch processes
- Separate keyword extraction phase for better timing visibility

**Output Verbosity Reduction (#194)**
- Replace verbose relevance labels with percentages (labels in verbose mode)
- Compact match indicators: `auth(d)`, `login(s)` instead of `"Matched: *auth*, *login*"`
- Convert ASCII box-drawing tier headers to markdown in dead code output
- Shorten error messages to one-liners with actionable suggestions
- Add return types to function listings (full specs in verbose mode)
- Reduce suggestions from 5 to 2, co-change entries from 5 to 3
- Change timestamp format from "Modified: X ago" to "X old"

### Fixed

**Graceful Shutdown for Ctrl+C (#191)**
- Add KeyboardInterrupt handling in CLI commands for clean exit (code 130)
- Python indexer now saves partial progress when interrupted during enrichment phases
- Add interruptible enrichment phases helper for consistent interrupt handling

## [0.5.0] - 2025-11-25

### Added

- **🎉 Python Language Support** ([#135](https://github.com/wende/cicada/pull/135))
  - Full Python code indexing via SCIP (Source Code Intelligence Protocol)
  - Complete Python code analysis: modules, classes, functions, call sites
  - Python-specific formatting (Class.method() notation)
  - Class display in search_module showing public/private method counts
  - Language detection with multi-language project support
  - 128+ tests for Python/SCIP functionality

- **Language-Agnostic Architecture** ([#135](https://github.com/wende/cicada/pull/135))
  - SCIP layer for universal code intelligence (111KB)
  - Protobuf-based SCIP protocol support
  - Language-specific formatters and indexers
  - Unified index format supporting Python, Elixir, TypeScript
  - Language detection: Python, Elixir, TypeScript/JavaScript
  - Enhanced utilities: lookup_module, lookup_function, get_call_sites, etc.

- **MCP Server Modular Architecture** ([#135](https://github.com/wende/cicada/pull/135))
  - Refactored into separate handler modules for better maintainability
  - Dedicated handlers: module, function, git, PR, analysis
  - Improved code organization and testability

- **Verbose flag** ([#154](https://github.com/wende/cicada/pull/154)) - Added `--verbose` flag for detailed logging and debugging
- **PR comments command** ([#144](https://github.com/wende/cicada/pull/144)) - New `make pr-comments` command for viewing and analyzing PR discussion
- **Keyword context display** ([#158](https://github.com/wende/cicada/pull/158)) - Enhanced search results with keyword match context showing where keywords were found
- **Multiple keyword weighting** ([#159](https://github.com/wende/cicada/pull/159)) - Support for multiple keyword weights in search scoring
- **Graceful shutdown** ([#153](https://github.com/wende/cicada/pull/153)) - Added signal handlers (SIGINT/SIGTERM) for clean MCP server shutdown
- **Coverage delta reporting** ([#149](https://github.com/wende/cicada/pull/149)) - CodeCov comments now show coverage deltas
- **Local scip-python installation** ([#178](https://github.com/wende/cicada/pull/178)) - Auto-installs scip-python to `~/.cicada/node/` avoiding global npm pollution

### Changed

- **Project Structure Reorganization** ([#135](https://github.com/wende/cicada/pull/135))
  - `cicada/elixir/` → `cicada/languages/elixir/`
  - `cicada/elixir/format/` → `cicada/format/`
  - Language-specific code now under `cicada/languages/{lang}/`
  - All import paths updated across codebase

- **Dependencies Schema** ([#132](https://github.com/wende/cicada/pull/132))
  - Module dependencies format changed from dict to list[dict]
  - Added automatic truncation for large dependency results

- **Python support refactoring** ([#160](https://github.com/wende/cicada/pull/160)) - Removed auto-install of scip-python and improved file handling safety
- **Test output improvements** - Made test output more concise and less verbose ([#142](https://github.com/wende/cicada/pull/142))
- **Markdown formatting** ([#167](https://github.com/wende/cicada/pull/167), [#169](https://github.com/wende/cicada/pull/169)) - Improved spacing after signatures and code blocks in usage output
- **Non-TTY output** ([#170](https://github.com/wende/cicada/pull/170)) - Use asterisk keyword highlights in non-TTY output
- **Documentation** ([#177](https://github.com/wende/cicada/pull/177)) - Refactored CLAUDE.md into modular documentation structure
- **Documentation updates** - Revised installation and command usage in README

### Fixed

- **Search Query Tokenization** ([#131](https://github.com/wende/cicada/pull/131))
  - Fixed query tokenization to properly handle wildcard patterns
  - Improved pattern matching for module-qualified searches
  - Better handling of OR patterns with spaces

- **Dependency Analysis Output** ([#132](https://github.com/wende/cicada/pull/132))
  - Fixed missing `detailed_dependencies` output in dependency analysis
  - Added truncation to prevent token overflow on large results

- **Gemini CLI Configuration** ([#130](https://github.com/wende/cicada/pull/130))
  - Fixed config path to use `settings.json` instead of `.gemini/config.json`

- **Class docstring display** ([#136](https://github.com/wende/cicada/pull/136)) - Fixed class docstring display in `expand_result` tool
- **Wildcard matching** ([#137](https://github.com/wende/cicada/pull/137)) - Fixed wildcard match confidence scoring and z-score tier grading
- **Python MCP tools** ([#139](https://github.com/wende/cicada/pull/139), [#151](https://github.com/wende/cicada/pull/151)) - Fixed critical bugs including dependency crashes and pattern matching issues
- **Python recent filter** ([#141](https://github.com/wende/cicada/pull/141)) - Fixed `recent=true` filter now works correctly for Python code
- **Private function suggestions** ([#140](https://github.com/wende/cicada/pull/140)) - Fixed incorrect private function suggestions in `search_function`
- **Dunder method search** ([#152](https://github.com/wende/cicada/pull/152)) - Fixed search for Python dunder methods by matching function names correctly
- **First-time linked repo bug** ([#176](https://github.com/wende/cicada/pull/176)) - Fixed bug when using cicada with a newly linked repository
- **Agent files detection** ([#179](https://github.com/wende/cicada/pull/179)) - Fixed cicada agent files detection and tag insertion

### Performance

- **Python SCIP conversion optimization** ([#175](https://github.com/wende/cicada/pull/175)) - Optimized from O(n²) to O(n) complexity, **71x faster** indexing

### Internal

- **Test Coverage Improvements** ([#128](https://github.com/wende/cicada/pull/128), [#145](https://github.com/wende/cicada/pull/145), [#146](https://github.com/wende/cicada/pull/146), [#147](https://github.com/wende/cicada/pull/147), [#148](https://github.com/wende/cicada/pull/148), [#150](https://github.com/wende/cicada/pull/150))
  - Boosted test coverage for low-coverage files
  - Added comprehensive test suites for Python support
  - Added comprehensive tests for index lookup and reference utilities
  - Added validation coverage for query MCP tool
  - Added edge case tests for filter_utils and pattern_utils
  - Overall test coverage increased to 84%
  - 1750+ tests passing across Python and Elixir
- **SCIP tests enforcement** ([#178](https://github.com/wende/cicada/pull/178)) - Tests now fail instead of skip when SCIP indexes are missing
- **CI/CD improvements**
  - Added dev branch to CI test workflow
  - Updated pull request trigger types in workflow

## [0.4.2] - 2025-11-20

### Added

- **Test Macro Keyword Indexing** ([#127](https://github.com/wende/cicada/pull/127))
  - Test descriptions (`test "description" do ... end`) now indexed and searchable by keywords

- **Git History Filter Feedback** ([#125](https://github.com/wende/cicada/pull/125))
  - Shows clear messages when date/author filters exclude all results with suggestions to adjust
  - Configurable recent cutoff via `recent_days` parameter (default: 14)

### Changed

- **Compact Query Result Formatting** ([#124](https://github.com/wende/cicada/pull/124))
  - Restored tier labels and confidence percentiles for better relevance indication
  - Added last modified timestamp with commit hash and PR number
  - Keyword source indicators show where matches came from: `(in docs)`, `(in strings)`, `(in docs+strings)`

### Fixed

- **PR Indexer Error Recovery** ([#126](https://github.com/wende/cicada/pull/126))
  - Saves partial progress when HTTP errors occur; next run resumes automatically
  - Prevents permanent gaps in PR index from transient failures

## [0.4.0] - 2025-11-19

### Added

- **Query Tool & Orchestrator** ([#120](https://github.com/wende/cicada/pull/120), [#111](https://github.com/wende/cicada/pull/111))
  - New `query` CLI command and MCP tool for smart code discovery (replaces `search_by_features`)
  - Tier-based scoring and filtering for better result relevance
  - Match detail tracking showing WHERE keywords matched (name, docs, strings)
  - Path pattern glob matching with brace expansion (`{ex,heex}`) and negation (`!**/test/**`)
  - Automatic timestamp tracking with PR number extraction from git history
  - Smart result suggestions when searches return too many or too few results
  - JSON and text output formats with configurable snippet display

- **Co-occurrence Analysis** ([#112](https://github.com/wende/cicada/pull/112))
  - Keyword suggestions based on actual codebase patterns (not generic language models)
  - New `suggest_keywords` MCP tool with expand/narrow modes
  - Expand mode: suggests related keywords when searches return no/few results
  - Narrow mode: suggests filtering keywords when searches return too many results
  - Automatic co-occurrence matrix building during indexing
  - Tracks pre-expansion keywords to reflect actual code content

- **Co-change Analysis** ([#115](https://github.com/wende/cicada/pull/115))
  - Tracks files and functions frequently modified together in git history
  - Co-change boost factor applied to search scores (default: 0.5)
  - Related files/functions shown in search results with commit counts
  - File-level and function-level co-change tracking
  - Now enabled by default during indexing

- **Unified Git History Tool** ([#120](https://github.com/wende/cicada/pull/120))
  - Single `git_history` MCP tool with smart routing based on parameters
  - Replaces 4 separate tools: `get_blame`, `get_commit_history`, `find_pr_for_line`, `get_file_pr_history`
  - Single line analysis: git blame + PR lookup for specific lines
  - Line range analysis: grouped authorship with code snippets
  - Function tracking: precise function evolution with git log -L
  - File-level history: PR index with fallback to git commits
  - Time filtering with `recent` parameter (last 14 days)
  - Author filtering for contributor-specific history

- **JQ Query Support** ([#110](https://github.com/wende/cicada/pull/110))
  - New `query_jq` MCP tool for querying index data with JQ expressions
  - Size estimation and automatic truncation to prevent token overflow
  - Compact (single-line) and pretty (formatted) output modes
  - Query validation with bracket nesting and string escaping checks
  - Direct access to index structure for advanced queries

- **Dependency Tool Refactoring** ([#120](https://github.com/wende/cicada/pull/120))
  - Clearer parameter naming for relationship directionality:
    - `what_calls_it`: shows call sites (what calls this function/module)
    - `what_it_calls`: shows dependencies (what this function/module calls)
    - `show_function_usage`: granular function-level usage
    - `include_code_context`: include code snippets at call sites
  - Integrated into `search_module` and `search_function` tools
  - Removed standalone `get_module_dependencies` and `get_function_dependencies`

### Changed

- **Co-change extraction now enabled by default** - Co-change analysis (tracking files and functions modified together) now runs automatically during indexing. This provides better search relevance but may increase initial indexing time by 10-30%.
- **Query API simplified** - Split `scope` parameter into orthogonal filters:
  - `scope` now only controls visibility: 'all', 'public', 'private' (removed 'recent')
  - Added separate `recent` boolean parameter for time-based filtering
  - Enables new combinations like `scope='public', recent=True` (recent public functions only)
- **Test filtering improved** - Replaced `include_tests` boolean with path pattern negation:
  - OLD: `include_tests=False`
  - NEW: `path_pattern='!**/test/**'`
  - More flexible - can exclude any path pattern, not just tests
- **query_jq default format changed** - Default output format changed from 'json' to 'compact' (single-line JSON) to reduce token usage. Use `format='pretty'` for readable formatting.
- **CLI and MCP parameter alignment** ([#122](https://github.com/wende/cicada/pull/122))
  - CLI `--show-snippets` flag now matches MCP tool parameter naming
  - Consistent parameter names across CLI and MCP interfaces
- **Git timestamp computation enabled by default** ([#120](https://github.com/wende/cicada/pull/120))
  - Timestamps automatically computed during indexing to support `recent` filtering
  - Makes `scope='recent'` useful out of the box
  - Batched computation for performance

### Removed

- **Removed CLI flags:**
  - `--extract-cochange` flag (feature now always enabled)
  - `--no-tests` flag (use `--path-pattern='!**/test/**'` instead)
- **Removed MCP tools:** ([#122](https://github.com/wende/cicada/pull/122))
  - `search_by_features` (replaced by `query` tool)
  - `search_by_keywords` (replaced by `query` tool)
  - `search_module_usage` (merged into `search_module` with `what_calls_it=True` parameter)
  - `get_module_dependencies` (merged into `search_module` with `what_it_calls=True` parameter)
  - `get_function_dependencies` (merged into `search_function` with `what_it_calls=True` parameter)
  - `get_blame` (replaced by `git_history` with `start_line` and `end_line` parameters)
  - `get_commit_history` (replaced by `git_history` with `function_name` parameter)
  - `find_pr_for_line` (replaced by `git_history` with `start_line` parameter)
  - `get_file_pr_history` (replaced by `git_history` with file path only)
- **Removed internal handler:** `DependencyHandler` class (functionality merged into `ModuleSearchHandler` and `FunctionSearchHandler`)
- **Removed legacy code:** ([#117](https://github.com/wende/cicada/pull/117))
  - Legacy `.cicada/` references and backward compatibility code
  - Cleaned up deprecated code paths

### Fixed

- **File watcher threading error** ([#119](https://github.com/wende/cicada/pull/119)) - Graceful handling when reindexing triggered from background thread
- **Keyword search for undocumented code** ([#118](https://github.com/wende/cicada/pull/118)) - Fixed crashes when searching modules/functions without documentation
- **Force flag for tier changes** ([#114](https://github.com/wende/cicada/pull/114)) - `--force` flag now allows tier changes during reindexing
- **Version hash merge conflicts** ([#113](https://github.com/wende/cicada/pull/113)) - Excluded `_version_hash.py` from git to prevent merge conflicts
- **Git index corruption in parallel tests** ([#120](https://github.com/wende/cicada/pull/120)) - Serialized tests using `os.chdir()` to prevent race conditions
- **Naive datetime comparison** ([#112](https://github.com/wende/cicada/pull/112)) - Fixed timezone-aware datetime handling for consistent comparisons
- **JSON output for module usage** ([#122](https://github.com/wende/cicada/pull/122)) - Fixed missing usage data in JSON format when `what_calls_it=True`
- **Path pattern glob matching** ([#120](https://github.com/wende/cicada/pull/120))
  - Fixed `**` wildcard corruption during regex conversion
  - Added brace expansion support for patterns like `{ex,heex}`
  - Fixed `*` wildcard to not match across directory separators
  - Fixed `/**` pattern to match zero or more directories

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

[Unreleased]: https://github.com/wende/cicada/compare/v0.5.2...HEAD
[0.5.2]: https://github.com/wende/cicada/compare/v0.5.1...v0.5.2
[0.5.1]: https://github.com/wende/cicada/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/wende/cicada/compare/v0.4.2...v0.5.0
[0.4.2]: https://github.com/wende/cicada/compare/v0.4.0...v0.4.2
[0.4.0]: https://github.com/wende/cicada/compare/v0.3.2...v0.4.0
[0.3.2]: https://github.com/wende/cicada/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/wende/cicada/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/wende/cicada/compare/v0.2.3...v0.3.0
[0.2.3]: https://github.com/wende/cicada/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/wende/cicada/compare/v0.2.0...v0.2.2
[0.2.0]: https://github.com/wende/cicada/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/wende/cicada/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/wende/cicada/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/wende/cicada/releases/tag/v0.1.0
