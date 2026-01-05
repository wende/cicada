# Performance

This guide explains Cicada's performance characteristics, optimization strategies, and best practices for large codebases.

## Quick Reference

| Operation | Small Project (<1000 files) | Large Project (>1000 files) | Very Large (>10,000 files) |
|-----------|----------------------------|----------------------------|----------------------------|
| **Initial Index** | 5-10 seconds | 30-60 seconds | 2-5 minutes |
| **Incremental Index** | <5 seconds | 5-15 seconds | 15-30 seconds |
| **Query Response** | <1 second | <1 second | <2 seconds |
| **Disk Space** | 5-10 MB | 10-50 MB | 50-200 MB |

---

## Indexing Performance

### Initial Indexing

First-time indexing parses all files in your project:

```bash
cd /path/to/project
cicada index
```

**Performance by Language:**

| Language | Approach | Speed | Notes |
|----------|----------|-------|-------|
| Elixir | Tree-sitter | Fast | ~200-300 files/sec |
| Erlang | Tree-sitter | Fast | ~200-300 files/sec |
| Python | SCIP | Medium | Requires scip-python external tool |
| TypeScript | SCIP | Medium | Requires scip-typescript |
| Go | SCIP | Medium | Requires scip-go |
| Rust | SCIP | Medium | Requires rust-analyzer |
| Other SCIP | SCIP | Medium | External indexer required |

**Factors Affecting Speed:**
- File count and size
- Language backend (tree-sitter vs SCIP)
- External tool availability
- CPU and disk I/O

### Incremental Indexing

Subsequent indexes only process changed files:

```bash
cicada index  # Auto-detects changes via SHA-256 hashing
```

**How it Works:**
1. Hash each file (SHA-256)
2. Compare against `hashes.json`
3. Re-index only modified files
4. Merge with existing index

**Typical Performance:** <5 seconds for small changes

**Watch Mode:**
Automatically reindex on file changes:
```bash
cicada watch
```

---

## Query Performance

### Response Times

Cicada queries are optimized for AI agent workflows:

| Query Type | Typical Response | Token Count |
|------------|-----------------|-------------|
| `search_module` | <500ms | 200-600 tokens |
| `search_function` | <500ms | 300-800 tokens |
| `query` (keyword) | <1s | 150-500 tokens |
| `git_history` | 1-2s | 300-1200 tokens |

### Index Lookup

All queries use in-memory index for instant access:
- Module lookups: O(1) hash table
- Function searches: O(n) with early termination
- Keyword matching: O(n) with pre-computed scores

---

## Token Optimization

### Understanding Token Usage

MCP tool responses consume tokens in AI conversations. Cicada provides controls to optimize token usage:

### Output Modes

**Compact Mode (Default):**
```python
# Minimal output - identifiers and file:line only
search_module("MyApp.User", verbose=False)
# ~200-400 tokens
```

**Verbose Mode:**
```python
# Full documentation, specs, examples
search_module("MyApp.User", verbose=True)
# ~600-1200 tokens
```

### Git History Optimization

**Brief Format (Recommended for AI agents):**
```python
git_history("lib/auth.ex", include_pr_description=False)
```

Output:
```markdown
## History for lib/auth.ex (5 commits)

- 589000d (2025-11-25) Optimize password hashing (#175)
- 0885638 (2025-11-24) Add 2FA support (#178)
- e68df27 (2025-11-23) Refactor session management (#160)
```
**Token count:** ~120 tokens

**Standard Format:**
```python
git_history("lib/auth.ex", include_pr_description=True)
```

Includes:
- PR titles and URLs
- Authors
- PR descriptions (truncated)

**Token count:** ~400-800 tokens

**Verbose Format:**
```python
git_history(
    "lib/auth.ex",
    include_pr_description=True,
    include_review_comments=True
)
```

Includes everything plus review comments.

**Token count:** ~1200-2000 tokens

### Search Result Pagination

For large result sets, use pagination to control token usage:

```python
# First 10 results
search_function("create*", head_limit=10)

# Next 10 results
search_function("create*", head_limit=10, offset=10)
```

### Best Practices for Token Efficiency

1. **Start with compact output**
   ```python
   # Query first
   query("authentication")  # 150-300 tokens

   # Then get details for specific matches
   search_function("authenticate/2")  # 300-500 tokens
   ```

2. **Use filters to narrow results**
   ```python
   # Instead of
   search_function("*")  # Returns hundreds of functions

   # Do
   search_function("*", glob="lib/auth/**")  # Focused results
   ```

3. **Disable unused features**
   ```python
   # If you don't need usage examples
   search_function("authenticate", include_usage_examples=False)
   ```

4. **Request specific information**
   ```python
   # Instead of
   git_history("lib/auth.ex")  # Full history

   # Do
   git_history("lib/auth.ex", recent=True, max_results=5)  # Last 5 recent changes
   ```

---

## Disk Usage

### Index Storage

All indexes stored in `~/.cicada/projects/<repo_hash>/`:

```
~/.cicada/projects/<hash>/
├── index.json         # 2-50 MB (main code index)
├── config.yaml        # <1 KB (project config)
├── hashes.json        # 100-500 KB (file tracking)
├── pr_index.json      # 500 KB-5 MB (PR attribution)
└── index.scip         # 5-50 MB (SCIP languages only)
```

**Total Disk Usage per Project:**
- Small project: 5-10 MB
- Medium project: 10-50 MB
- Large project: 50-200 MB

### Cleanup

Remove stale indexes:
```bash
# Remove specific project index
cicada clean  # In project directory

# Or manually
rm -rf ~/.cicada/projects/<hash>/
```

---

## Optimization Tips

### For Large Codebases (>10,000 files)

1. **Exclude unnecessary directories**

   Edit `~/.cicada/projects/<hash>/config.yaml`:
   ```yaml
   exclude_patterns:
     - "deps/*"
     - "build/*"
     - "_build/*"
     - "node_modules/*"
     - "vendor/*"
     - "*.gen.ex"  # Generated files
   ```

2. **Use file extension filters**
   ```yaml
   file_extensions:
     - ".ex"
     - ".exs"
     # Don't index test files if not needed
     # - ".exs"
   ```

3. **Disable PR indexing** (if not needed)
   ```bash
   # Skip PR indexing during cicada index
   # PR indexing requires gh CLI and takes extra time
   ```

### For Slow SCIP Languages

**Python Optimization:**
The SCIP converter was optimized from O(n²) to O(n):
- Before: 60 seconds for large projects
- After: <5 seconds for same projects
- **71x faster** with recent optimizations

**TypeScript Optimization:**
Use project-specific `tsconfig.json` to exclude unnecessary files:
```json
{
  "exclude": [
    "node_modules",
    "dist",
    "build"
  ]
}
```

---

## Performance Monitoring

### Index Statistics

Check index health:
```bash
cicada stats
```

Output:
```
Project: /path/to/project
Language: elixir
Total modules: 234
Total functions: 1,842
Index size: 12.4 MB
Last indexed: 2025-01-05 10:23:14
Files tracked: 547
```

### Benchmark Tool Usage

Use the benchmarking script to measure tool call frequency:

```bash
# Test specific prompts
python tests/benchmark/benchmark_mcp_tool_calls.py \
  --prompt "Show me the User module"

# Run full test suite
python tests/benchmark/benchmark_mcp_tool_calls.py --test-suite
```

**Metrics Tracked:**
- Total tool calls per query
- Tool call breakdown
- Response duration
- Token usage estimation

---

## Architecture-Specific Performance

### Tree-sitter Backend (Elixir, Erlang)

**Pros:**
- Fast incremental parsing
- No external dependencies
- Real-time indexing (<5s)

**Cons:**
- Syntactic analysis only
- Manual AST traversal
- Per-language custom extractors

**Best for:** Languages without SCIP indexers, rapid prototyping

### SCIP Backend (Python, TypeScript, Go, Rust, etc.)

**Pros:**
- Compiler-accurate results
- Shared converter infrastructure (3x faster to add new languages)
- Type-aware analysis
- Cross-repository references

**Cons:**
- Requires external indexer
- Slower initial indexing
- Must rebuild on changes (no incremental)

**Best for:** Mainstream languages with mature tooling

---

## Troubleshooting Performance Issues

### Issue: Slow Initial Indexing

**Symptoms:** First index takes >5 minutes

**Solutions:**
1. Check excluded patterns - may be indexing unnecessary files
2. For SCIP languages, ensure external indexer is optimized
3. Check disk I/O - slow drive can impact performance
4. Reduce file count by excluding test directories

### Issue: Large Index Files

**Symptoms:** `index.json` >100 MB

**Solutions:**
1. Review exclude patterns - likely indexing generated code
2. Check for large docstrings or comments
3. Consider splitting into multiple smaller projects
4. Use `cicada clean` and reindex with tighter exclusions

### Issue: Slow Query Responses

**Symptoms:** Queries take >2 seconds

**Solutions:**
1. Check index file size - may need cleanup
2. Use more specific queries (avoid wildcards like `*`)
3. Add filters: `glob`, `path`, `recent`
4. Reduce `head_limit` for initial exploration

### Issue: Out of Memory During Indexing

**Symptoms:** Indexing crashes with memory error

**Solutions:**
1. Exclude large generated files
2. Process in batches (not currently supported - file issue)
3. Increase available RAM
4. Use SCIP for large codebases (more memory-efficient)

---

## Benchmarks & Comparisons

### Token Usage Comparison

| Task | Cicada (Compact) | Cicada (Verbose) | Raw Git Commands |
|------|------------------|------------------|------------------|
| File history (5 PRs) | 300 tokens | 1200 tokens | 800 tokens |
| Module search | 250 tokens | 800 tokens | N/A (no equivalent) |
| Function calls | 400 tokens | 1000 tokens | N/A (no equivalent) |

**Key Insight:** Compact mode optimizes for AI agents while verbose mode provides human-readable context.

### Development Effort

Adding new language support:

| Approach | Effort | Accuracy | Maintenance |
|----------|--------|----------|-------------|
| Tree-sitter | 12-17 days | Syntactic | Per-language custom code |
| SCIP | 4-6 days | Semantic | Shared converter |

**SCIP is 3x faster** for languages with existing indexers.

---

## Related Documentation

- [Architecture](ARCHITECTURE.md) - Why Cicada uses both tree-sitter and SCIP
- [MCP Tools Reference](MCP_TOOLS.md) - Available query tools and parameters
- [Installation](INSTALLATION.md) - Setup and configuration
