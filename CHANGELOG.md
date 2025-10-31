# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GitHub Actions workflow for automated PyPI publishing ([#26](https://github.com/wende/cicada/pull/26))
- MIT License file for PyPI compliance ([#26](https://github.com/wende/cicada/pull/26))
- Enhanced pyproject.toml with complete package metadata for PyPI ([#26](https://github.com/wende/cicada/pull/26))

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

[Unreleased]: https://github.com/wende/cicada/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/wende/cicada/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/wende/cicada/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/wende/cicada/releases/tag/v0.1.0
