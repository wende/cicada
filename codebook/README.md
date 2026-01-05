# Cicada Feature Reference

**CICADA** - Code Intelligence: Contextual Analysis, Discovery, and Attribution

## Getting Started
1. [Installation](INSTALLATION.md) - Step-by-step setup for all supported editors
2. [Workflows](WORKFLOWS.md) - Real-world examples of chaining tools together
3. [Architecture](ARCHITECTURE.md) - Design decisions and system overview
4. [Performance](PERFORMANCE.md) - Optimization tips and performance characteristics

## Language Support
1. [Language Support](LANGUAGE_SUPPORT.md) - Comprehensive guide to all 14 supported languages
2. Elixir Support - Full AST-level indexing with module, function, and macro extraction
3. Python Support - SCIP-based indexing with class and method detection
4. Erlang Support - Tree-sitter based parsing with EDoc extraction
5. TypeScript Support - SCIP-based indexing via TypeScript compiler
6. JavaScript Support - SCIP-based indexing for JS projects
7. Rust Support - SCIP-based indexing via rust-analyzer
8. Go Support - SCIP-based indexing via gopls
9. Java Support - SCIP-based indexing for JVM projects
10. Scala Support - SCIP-based indexing via Metals
11. C/C++ Support - SCIP-based indexing via clangd
12. Ruby Support - SCIP-based indexing
13. C# Support - SCIP-based indexing for .NET projects
14. Visual Basic Support - SCIP-based indexing for .NET projects
15. Dart Support - SCIP-based indexing

## MCP Tools
1. [MCP Tools Reference](MCP_TOOLS.md) - Comprehensive guide to all MCP tools
2. query - Smart code discovery with keyword/pattern auto-detection
3. search_module - View complete module API with dependency analysis
4. search_function - Find function definitions and all call sites
5. git_history - Unified tool for all git history queries
6. expand_result - Drill down into query results for complete details
7. refresh_index - Force refresh the index to pick up recent changes
8. query_jq - Execute custom jq queries against the index

## CLI Tools
1. [CLI Tools Reference](CLI_TOOLS.md) - Comprehensive guide to all CLI commands
2. Interactive Setup - `cicada install` with editor and model selection
3. Index Command - Index projects with customizable options
4. Watch Command - Monitor files and auto-reindex on changes
5. Status Command - Display index health, links, and configurations
6. Stats Command - View usage statistics, tool calls, and token metrics
7. Link Command - Share indexes across repositories or worktrees
8. Clean Command - Remove Cicada configuration and indexes
9. Run Command - Execute MCP tools directly from command line
10. Serve Command - Start REST API server for HTTP access to tools

## Code Indexing
1. [AST-Level Indexing](AST_INDEXING.md) - Extracts module, function, and class definitions with signatures and specs
2. [Incremental Indexing](INCREMENTAL_INDEXING.md) - Only reindexes changed files for fast updates (includes Watch Mode)
3. [Automatic Language Detection](AUTOMATIC_LANGUAGE_DETECTION.md) - Detects project type from mix.exs or pyproject.toml
4. [Keyword-Based Indexing](KEYWORD_INDEXING.md) - Keyword extraction from module names, function names, parameter names, docstrings, strings and inline comments
5. [String-Based Indexing](STRING_INDEXING.md) - Indexes string literals from function bodies (SQL, error messages, etc.)

## Semantic Search
1. [Keyword Search](KEYWORD_SEARCH.md) - Find code by matching query terms against pre-extracted keywords
2. [Pattern Search](KEYWORD_SEARCH.md#wildcard-patterns) - Find code using wildcards (*) and OR patterns (|)
3. [Mixed Queries](KEYWORD_SEARCH.md#synonym-groups) - Combine keywords and patterns in a single search
4. [Match Source Filtering](KEYWORD_SEARCH.md#match-source-filtering) - Search in docs, strings, or comments separately
5. Filtering - Filter by public/private visibility, file path using glob patterns, code recency 

## Code Analysis
1. [Code Analysis](CODE_ANALYSIS.md) - Module and function analysis with dependency tracking and call site discovery

## Git History & Attribution
1. [Git History & PR Indexing](GIT_HISTORY.md) - Comprehensive guide to git history analysis and PR attribution
2. Line Blame - Find who wrote a specific line and in which PR
3. Range Blame - Group consecutive lines by authorship with PR enrichment
4. Function Evolution - Track how a function has changed over time
5. File PR History - View all PRs that modified a file
6. Author Filtering - Filter history by author name
7. Time Filtering - View recent, older, or all-time history

## PR Indexing
1. [Git History & PR Indexing](GIT_HISTORY.md) - Unified documentation for PR indexing and git history
2. PR Index - Index GitHub pull requests for offline lookup
3. PR Descriptions - Access PR descriptions and commit messages
4. Review Comments - Access PR review comments and discussions
5. Incremental PR Updates - Only fetch new PRs since last index

## Co-Change Analysis
1. Co-Change Detection - Identify files frequently modified together
2. Function Co-Change - Identify functions that change together
3. Search Score Boosting - Boost search results based on co-change relationships
4. Adaptive Commit Analysis - Automatically adjusts analysis depth by repo size

## Editor Integration
1. Claude Code Setup - One-command setup for Claude Code editor
2. Cursor Setup - One-command setup for Cursor editor
3. VS Code Setup - One-command setup for VS Code editor
4. Gemini CLI Setup - One-command setup for Gemini CLI
5. Codex Setup - One-command setup for Codex editor
6. Zed Setup - One-command setup for Zed editor
7. MCP Server - Model Context Protocol server for AI assistants

## Output & Token Optimization
1. Compact Output - Token-efficient responses with essential info only
2. Verbose Mode - Enable full documentation, specs, and examples
3. Code Snippets - Optional code context around results
4. Pagination - Limit and offset for large result sets
5. Automatic Truncation - Large results are automatically truncated

## Advanced Features
1. jq Query Support - Execute arbitrary jq queries against the index
2. Schema Discovery - Discover available index fields with `| schema`
3. Sample Mode - Preview large datasets with automatic limiting
4. Repository Linking - Link repositories to share indexes
5. Co-occurrence Keywords - Intelligent keyword suggestions based on patterns
6. REST API Server - HTTP access to all MCP tools with OpenAPI docs

## AI Agents Integration
1. [AI Agents Integration](AI_AGENTS.md) - Pre-built agents for specialized code exploration
2. Cicada Code Explorer - Fast code discovery agent optimized with Haiku
3. Agent Installation - One-command setup via `cicada agents install`
4. Template System - Extensible agent templates with YAML configuration
5. Workflow Optimization - Task-focused tools and best practices
