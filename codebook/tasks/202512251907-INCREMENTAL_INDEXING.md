# Incremental Indexing - Fast Reindexing with File Hashing

The incremental indexing system allows you to reindex your Elixir codebase efficiently by only processing files that have changed since the last run. This dramatically speeds up reindexing, especially when using keyword extraction with lemminflect.

## How It Works

1. **First Run (Full Index)**:
   - Indexes all Elixir files in your repository
   - Extracts modules, functions, documentation, dependencies
   - Optionally extracts keywords using lemminflect
   - Computes MD5 hash for each processed file
   - Saves index to `~/.cicada/projects/<repo_hash>/index.json`
   - Saves file hashes to `~/.cicada/projects/<repo_hash>/hashes.json`

2. **Subsequent Runs (Incremental)**:
   - Loads existing index and hashes
   - Finds all current Elixir files
   - Compares current file hashes with stored hashes
   - Detects three types of changes:
     - **New files**: Didn't exist in last run
     - **Modified files**: Hash changed since last run
     - **Deleted files**: Existed before but not now
   - Processes only new/modified files
   - Merges results with existing index
   - Updates hashes for processed files
   - Removes deleted files from index and hashes

3. **Interrupt Safety**:
   - Signal handlers catch Ctrl-C (SIGINT) and SIGTERM
   - Current file finishes processing gracefully
   - Partial progress is saved to disk
   - Next run continues from where you left off
   - Press Ctrl-C twice to force quit (may lose current file)

## Quick Start

### Basic Usage

```bash
# First run: full index with hash computation
cicada index --force --keywords

# Subsequent runs: automatic incremental indexing
cicada index  # Only processes changed files

# Force full reindex (ignore hashes)
cicada index --full
```

### Switching Indexing Modes

When switching between indexing modes, use `--full` to ensure consistent keywords across all files:

```bash
# Initially indexed with keywords mode
cicada index --force --keywords

# Switching modes (embeddings is not implemented yet)
cicada index --force --embeddings --full
```

**Why use `--full`?**
- Without `--full`, incremental indexing only reprocesses changed files
- Unchanged files retain keywords from the previous extraction method
- Results in mixed keyword extraction methods in a single index
- Using `--full` ensures all files use the same extraction method

### Output Example

**Incremental indexing with changes:**
```
Performing incremental index of: /Users/wende/projects/my_app
Detecting file changes...
Changes detected:
  New files: 2
  Modified files: 3
  Deleted files: 1

Processing 5 changed file(s)...

Merging with existing index...
Updating file hashes...

Incremental indexing complete!
  Total modules: 147
  Total functions: 1,243
  Files processed: 5
  Files deleted: 1

Index saved to: ~/.cicada/projects/<repo_hash>/index.json
Hashes saved to: ~/.cicada/projects/<repo_hash>/hashes.json
```

**Incremental indexing with no changes:**
```
Performing incremental index of: /Users/wende/projects/my_app
Detecting file changes...
No changes detected. Index is up to date.
```

## Interrupt Safety

### Graceful Interruption

Press **Ctrl-C once** during indexing:

```
  Processed 15/50 files...

⚠️  Interrupt received. Finishing current file and saving progress...
   Press Ctrl-C again to force quit (may lose progress)

⚠️  Interrupted after processing 15/50 files
   Saving partial progress...
Computing file hashes for incremental updates...

✓ Partial index saved!
  Processed: 15/50 files (30.0%)
  Modules: 14
  Functions: 127

💡 Run the command again to continue indexing remaining 35 file(s)
```

### Force Quit

Press **Ctrl-C twice** to immediately terminate:
- First Ctrl-C: Sets up graceful shutdown
- Second Ctrl-C: Kills process immediately (may lose current file's work)

### Resume After Interrupt

Simply run the same command again:

```bash
cicada index  # or cicada index --force --keywords
```

The incremental indexing system will:
1. Load the partial index and hashes
2. Detect which files haven't been processed yet
3. Continue indexing remaining files
4. Merge with existing partial results

## Hash Storage Structure

The hash file (`~/.cicada/projects/<repo_hash>/hashes.json`) contains:

```json
{
  "version": "1.0",
  "hashes": {
    "lib/my_app/user.ex": "5d41402abc4b2a76b9719d911017c592",
    "lib/my_app/account.ex": "7d793037a0760186574b0282f2f435e7",
    "lib/my_app/auth.ex": "098f6bcd4621d373cade4e832627b4f6",
    "test/my_app/user_test.exs": "1bc29b36f623ba82aaf6724fd3b16718"
  },
  "last_updated": "2025-10-28T20:15:42Z"
}
```

### Hash Algorithm

- **Algorithm**: MD5 (128-bit)
- **Purpose**: Change detection (not security)
- **Performance**: ~400 MB/s for typical files
- **Output**: 32-character hexadecimal string

### Why MD5?

MD5 is used for change detection because:
- ✅ Built into Python (no extra dependencies)
- ✅ Fast enough for this use case (~400 MB/s)
- ✅ Collision resistance not critical (we're detecting file changes, not preventing attacks)
- ✅ Shorter hashes than SHA256 (32 vs 64 chars)

## Technical Details

### Change Detection Algorithm

```python
def detect_file_changes(
    files: List[str],           # Current files in repo
    old_hashes: Dict[str, str], # Previous file hashes
    repo_path: str              # Repository root
) -> Tuple[List[str], List[str], List[str]]:
    """
    Returns: (new_files, modified_files, deleted_files)
    """
    # 1. Deleted = in old_hashes but not in files
    deleted_files = old_hashes.keys() - set(files)

    # 2. New = in files but not in old_hashes
    # 3. Modified = hash differs from old_hashes
    for file_path in files:
        if file_path not in old_hashes:
            new_files.append(file_path)
        else:
            current_hash = compute_file_hash(file_path)
            if current_hash != old_hashes[file_path]:
                modified_files.append(file_path)

    return new_files, modified_files, deleted_files
```

### Index Merging Algorithm

```python
def merge_indexes_incremental(
    old_index: Dict,      # Existing index
    new_index: Dict,      # Index of changed files
    deleted_files: List   # Files that were deleted
) -> Dict:
    """
    Merges old and new indexes while handling deletions.
    """
    merged = {"modules": {}, "metadata": {}}

    # 1. Keep all modules from old_index except deleted files
    for module_name, module_data in old_index["modules"].items():
        file_path = module_data["file"]
        if file_path not in deleted_files:
            merged["modules"][module_name] = module_data

    # 2. Add/update modules from new_index (overwrites old)
    merged["modules"].update(new_index["modules"])

    # 3. Recalculate metadata (counts, timestamp)
    merged["metadata"] = recalculate_stats(merged["modules"])

    return merged
```

### Interrupt Handling Flow

```
User presses Ctrl-C
        │
        ▼
SIGINT signal received
        │
        ▼
_handle_interrupt() called
        │
        ├─> Print warning message
        ├─> Set _interrupted = True
        └─> Restore default signal handlers
                │
                ▼
        Main loop checks flag
                │
                ├─> After each file: if _interrupted → break
                └─> After each error: if _interrupted → break
                        │
                        ▼
                Save partial progress
                        │
                        ├─> Build index with processed files
                        ├─> Compute hashes for processed files
                        ├─> Save index.json
                        ├─> Save hashes.json
                        └─> Print resume instructions
```

## Performance Benefits

### Benchmark: Large Codebase (Phoenix App)

**Scenario**: 200 Elixir files, changed 5 files

| Indexing Type | Time | Files Processed |
|--------------|------|-----------------|
| Full index | 12.3s | 200 files |
| Incremental | 0.8s | 5 files |
| **Speedup** | **15.4x** | **97.5% reduction** |

### Benchmark: With Keyword Extraction

**Scenario**: 200 Elixir files with documentation, changed 5 files

| Indexing Type | Time | Files Processed |
|--------------|------|-----------------|
| Full index + keywords | 48.7s | 200 files |
| Incremental + keywords | 2.1s | 5 files |
| **Speedup** | **23.2x** | **95.7% time saved** |

**Why bigger speedup with keywords?**
- Keyword extraction using lemminflect is CPU-intensive
- NLP processing adds ~0.2s per file with documentation
- Incremental indexing amortizes model load time
- Only processes changed files → huge savings

### Real-World Usage Patterns

**During active development:**
```bash
# Edit 2-3 files, reindex frequently
cicada index  # ~1-2s instead of ~50s (only reprocesses changed files)
```

**After git pull:**
```bash
# Pulled 10 changed files from main branch
cicada index  # ~3s instead of ~12s
```

**Clean build:**
```bash
# Switched to different branch with many changes
cicada index --full  # ~12s (same as before)
```

## File Patterns

### Files Always Processed
- New files (didn't exist in previous index)
- Modified files (hash changed)

### Files Never Processed
- Unchanged files (hash matches)
- Files in `.gitignore` patterns (if excluded)

### Files Handled Specially
- Deleted files: Removed from index and hashes
- Renamed files: Detected as (old deleted + new added)
- Moved files: Same as renamed

### Excluded Directories

These directories are always excluded from indexing:

```elixir
deps/           # Hex dependencies
_build/         # Compiled artifacts
node_modules/   # NPM dependencies
.git/           # Git metadata
assets/         # Static assets (typically JS/CSS)
priv/           # Private resources
```

## Troubleshooting

### Issue: Index appears corrupted after interrupt

**Symptoms:**
- Missing modules in index
- Incorrect function counts
- "Module not found" errors

**Solution:**
```bash
# Force full reindex (keywords mode)
cicada index --full
cicada index --force --keywords --full
```

### Issue: Incremental index not detecting changes

**Symptoms:**
- Modified files not being reindexed
- Old function definitions still showing

**Possible causes:**
1. Hash file out of sync
2. File timestamps unchanged (e.g., git checkout)

**Solution:**
```bash
# Delete hash file and reindex
rm ~/.cicada/projects/<repo_hash>/hashes.json
cicada index

# Or use cicada clean to remove all storage
cicada clean
```

### Issue: Incremental indexing too slow

**Symptoms:**
- Incremental index takes almost as long as full index

**Diagnosis:**
```bash
# Check which files are detected as changed
# Look for "Changes detected:" output
cicada index
```

**Common causes:**
1. Many files actually changed (e.g., after major refactor)
2. Hash file deleted or corrupted
3. File content unchanged but hash recomputed

**Solution:**
- If many files changed: This is expected behavior
- If hash file missing: First run will be slow (rebuilding hashes)
- If corruption suspected: Use `cicada clean` to remove all storage and start fresh

### Issue: "No changes detected" but I know I changed files

**Cause:** File content might be identical after changes (e.g., whitespace-only changes reverted)

**Verification:**
```bash
# Compute hash manually
md5 lib/my_app/user.ex

# Compare with stored hash in ~/.cicada/projects/<repo_hash>/hashes.json
cat ~/.cicada/projects/<repo_hash>/hashes.json | grep "user.ex"
```

**Solution:**
If file truly changed but hash matches (unlikely):
```bash
# Force full reindex
cicada index --full
```

## Best Practices

### 1. Regular Incremental Reindexing

Add to your development workflow:

```bash
# After pulling changes
git pull && cicada index

# Before committing (reindex changed files)
cicada index && git commit
```

### 2. CI/CD Integration

In your CI pipeline:

```yaml
# .github/workflows/ci.yml
- name: Index codebase
  run: |
    cicada index
    # Run tests that depend on index
    pytest tests/
```

**Note:** In CI, always use full index (no `.cicada/` directory persisted)

### 3. Pre-commit Hook

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Reindex changed files before commit
cicada index
```

### 4. Storage Location

All index files and hashes are stored in a centralized location outside your repository:

```
~/.cicada/projects/<repo_hash>/
  ├── index.json        # Code index
  ├── hashes.json       # File hashes for incremental indexing
  ├── config.yaml       # Keyword extraction configuration
  └── pr_index.json     # Pull request index (if using PR features)
```

Only the MCP configuration file (`.mcp.json`, `.cursor/mcp.json`, or `.vscode/settings.json`) is added to your repository.

### 5. Periodic Full Reindexing

Even with incremental indexing, occasionally do a full reindex:

```bash
# Weekly or after major refactors
cicada index --full  # or cicada index --force --keywords --full
```

This ensures:
- No accumulated drift from interrupted runs
- Fresh keyword extraction with current configuration
- Cleanup of any orphaned entries

## Advanced Usage

### Scripting with Incremental Indexing

```python
from cicada.indexer import ElixirIndexer

indexer = ElixirIndexer()

# Incremental by default
index = indexer.incremental_index_repository(
    repo_path="/path/to/repo",
    output_path=".cicada/index.json",
    extract_keywords=True,
    spacy_model="small",
    force_full=False  # Set to True for full reindex
)

# Check what was processed
metadata = index["metadata"]
print(f"Total modules: {metadata['total_modules']}")
print(f"Total functions: {metadata['total_functions']}")
```

### Custom Hash Storage Location

```python
from cicada.utils.hash_utils import save_file_hashes, load_file_hashes

# Load from custom location
hashes = load_file_hashes("/custom/path")

# Save to custom location
save_file_hashes("/custom/path", hashes)
```

### Monitoring Indexing Progress

```python
import signal
from cicada.indexer import ElixirIndexer

indexer = ElixirIndexer()

# Custom interrupt handler
def custom_handler(signum, frame):
    print("Custom cleanup before interrupt")
    indexer._handle_interrupt(signum, frame)

signal.signal(signal.SIGINT, custom_handler)

# Run indexing
indexer.incremental_index_repository(
    repo_path=".",
    extract_keywords=True
)
```

## Related Features

- **[PR Indexing](PR_INDEXING.md)**: Also supports incremental updates
- **[Extended Git History](EXTENDED_GIT_HISTORY.md)**: Works with incrementally built indexes
- **Keyword Search**: Major beneficiary of incremental indexing (keyword extraction is slow)

## Implementation Notes

### Why Separate Hash File?

The hash file is stored separately from the main index for several reasons:

1. **Separation of concerns**: Index = code structure, hashes = change detection
2. **Faster loading**: Don't need to load/parse hashes when just reading index
3. **Cleaner index**: Index.json focuses on code, not metadata
4. **Easier debugging**: Can inspect hashes without wading through large index

### Why Not Directory Tree Hashing?

Current implementation uses file-level hashing. Future versions may add directory tree hashing for even better performance:

```
Planned feature (not yet implemented):
- Hash each directory's contents
- Propagate hashes up the tree
- Skip entire unchanged subtrees
- Especially valuable for monorepos
```

File-level hashing is simpler and covers 95% of use cases.

### Hash Collision Handling

MD5 collision probability is negligible for this use case:

- **Probability**: ~2^-64 for random 4KB files
- **Impact if it happens**: File not reindexed (will be caught on next change)
- **Not a security concern**: We're detecting changes, not preventing tampering

## FAQ

**Q: Does incremental indexing work with keyword extraction (`--keywords`)?**

A: Yes! This is where it shines. Keyword extraction is CPU-intensive (~0.2s per file with docs), so incremental indexing provides the biggest speedup when using keyword extraction.

**Q: What happens if I interrupt during keyword extraction?**

A: Current file finishes extracting keywords, then progress is saved. Next run continues with remaining files. No data loss.

**Q: Can I use incremental indexing in CI/CD?**

A: Yes, but CI usually runs in clean environments without persisted `~/.cicada/` directories. First run will always be full. Consider caching `~/.cicada/projects/` between runs if your CI supports it.

**Q: Does it detect renamed files?**

A: Renamed/moved files are detected as (deleted + new). Both files get reprocessed. This is correct behavior since the path changed.

**Q: How much disk space do hashes use?**

A: Minimal. Each hash is 32 bytes + file path length. For 1,000 files with average 40-char paths: ~72KB.

**Q: Can I manually edit hashes.json?**

A: Yes, it's just JSON. Useful for forcing reindex of specific files by deleting their hashes.

**Q: Does it work with multiple repositories?**

A: Yes, each repository has its own `~/.cicada/projects/<repo_hash>/` directory with independent hashes. No cross-contamination.

**Q: What if I change the hashing algorithm in future versions?**

A: The hash file includes a `version` field. Future versions can detect old format and trigger migration or full reindex.

## Summary

Incremental indexing provides:

✅ **Massive speedup** for reindexing (10-25x faster)
✅ **Interrupt safety** with graceful Ctrl-C handling
✅ **Automatic** change detection via MD5 hashing
✅ **Especially valuable** with keyword extraction
✅ **Zero configuration** - works out of the box
✅ **Backward compatible** - gracefully handles missing hashes

Simply run `cicada index` as usual - incremental indexing happens automatically!
