# Manual Testing Checklist

Quick test plan before merging to main.

## Setup & Install
- [ ] `cicada` - Setup in current directory, verify `.mcp.json` created
- [ ] `cicada .` - Explicit current directory path
- [ ] `cicada /path/to/other/project` - Setup in different directory
- [ ] `cicada --skip-install` - Skip dependency installation

## Index - Basic
- [ ] `cicada index` - Interactive setup (no flags), choose nlp/rag, choose tier
- [ ] `cicada index .` - Default output path
- [ ] `cicada index --output custom.json` - Custom output path

## Index - NLP Mode
- [ ] `cicada index --nlp` - NLP with regular tier (default)
- [ ] `cicada index --nlp --fast` - NLP with fast tier
- [ ] `cicada index --nlp --max` - NLP with max tier

## Index - RAG Mode
- [ ] `cicada index --rag` - RAG with regular tier (default)
- [ ] `cicada index --rag --fast` - RAG with fast tier
- [ ] `cicada index --rag --max` - RAG with max tier

## Index - Error Cases
- [ ] `cicada index --fast` - Should error: "requires --nlp or --rag"
- [ ] `cicada index --max` - Should error: "requires --nlp or --rag"
- [ ] `cicada index --nlp --rag` - Should error: "Cannot specify both"

## Index - Incremental
- [ ] Run `cicada index --nlp` twice - Second run should be faster (incremental)
- [ ] Modify 1-2 files, run again - Only changed files reprocessed
- [ ] Ctrl-C during indexing, run again - Resume from saved progress

## PR Indexing
- [ ] `cicada index-pr` - Default incremental update
- [ ] `cicada index-pr .` - Explicit current directory
- [ ] `cicada index-pr --clean` - Clean rebuild from scratch
- [ ] `cicada index-pr --output custom_pr.json` - Custom output path
- [ ] Ctrl-C during PR indexing - Verify graceful shutdown message

## Dead Code Analysis
- [ ] `cicada find-dead-code` - Default (high confidence, markdown)
- [ ] `cicada find-dead-code --min-confidence medium` - Medium confidence
- [ ] `cicada find-dead-code --min-confidence low` - All candidates
- [ ] `cicada find-dead-code --format json` - JSON output
- [ ] `cicada find-dead-code --index custom.json` - Custom index path
- [ ] `cicada find-dead-code` before indexing - Should error with helpful message

## MCP Server (via Claude Code/Cline)
- [ ] `search_module` - Find module by name
- [ ] `search_function` - Find function with usage examples
- [ ] `search_module_usage` - Track module dependencies
- [ ] `search_by_keywords` - Semantic search (requires --nlp or --rag index)
- [ ] `find_dead_code` - MCP tool version
- [ ] `get_commit_history` - File history
- [ ] `get_blame` - Line-by-line ownership
- [ ] `find_pr_for_line` - PR attribution (requires PR index)
- [ ] `get_file_pr_history` - File PR history (requires PR index)

## Paths to Test
- [ ] Current directory (`.`)
- [ ] Test fixture directory (`tests/fixtures/example_project`)
- [ ] Absolute path (`/full/path/to/elixir/project`)
- [ ] Relative path (`../some_project`)
- [ ] Non-Elixir directory (should handle gracefully)

## Version Check
- [ ] `cicada index` - Verify version check message appears
- [ ] `cicada index-pr` - Verify version check message appears

## Edge Cases
- [ ] Empty directory - Should handle gracefully
- [ ] Non-git repository - PR features should warn appropriately
- [ ] Large repository (>500 files) - Verify performance
- [ ] Repository with no `.ex` files - Should complete without errors
