# Model Change Detection

## Overview

When using CICADA with keyword extraction enabled (via `--fast`, `--regular`, or `--max` flags), the system tracks which model configuration was used to create the index. If you attempt to run an incremental index with a different model configuration, CICADA will detect this and prompt you to choose whether to proceed with a full reindex or keep the existing index.

## Why This Matters

Keyword extraction is a fundamental part of how CICADA indexes your code for semantic search. Different extraction methods (spaCy vs KeyBERT) and model tiers (fast, regular, max) produce different keywords, which means:

- **Inconsistent search results**: If part of your index uses one model and another part uses a different model, search results will be inconsistent
- **Lost semantic meaning**: Mixing models can lead to poor search quality
- **Confusion**: Without tracking, users might not realize their index is using an outdated or different model configuration

## How It Works

### Metadata Tracking

Every time you create or update an index with keyword extraction enabled, CICADA stores the model configuration in the index metadata:

```json
{
  "modules": { ... },
  "metadata": {
    "indexed_at": "2024-01-15T10:30:00",
    "keyword_method": "spacy",
    "model_tier": "regular",
    ...
  }
}
```

### Change Detection

When you run `cicada index` on an existing index, CICADA checks:

1. Was keyword extraction enabled in the existing index?
2. If yes, does the new model configuration match the old one?
3. If no match, prompt the user with options

### User Prompt

If a model change is detected, you'll see an interactive prompt:

```
⚠  Model Configuration Change Detected

  Previous configuration:
    Method: SPACY
    Model:  Regular

  New configuration:
    Method: BERT
    Model:  Max

  Changing the model requires reindexing the entire codebase.

What would you like to do?
» Continue - Reindex entire codebase with new model
  Abort - Keep existing index with old model
```

## Usage Examples

### Example 1: Changing from Fast to Max Tier

```bash
# Initial indexing with fast model (token-based)
cd my-elixir-project
cicada index --force --fast

# Later, trying to upgrade to max quality (BERT-based)
cicada index --force --max

# CICADA will detect the change and prompt:
# ⚠  Model Configuration Change Detected
#   Previous: Fast (token-based)
#   New: Max (BERT-based)
#
# Choose: Continue or Abort
```

### Example 2: Upgrading Model Quality

```bash
# Initial indexing with regular model (default)
cicada index --force --regular

# Later, upgrading to max quality
cicada index --force --max

# CICADA will detect the tier change and prompt
```

### Example 3: No Prompt When Configuration Matches

```bash
# Initial indexing
cicada index --force --regular

# Later, running again with same config
cicada index --force --regular

# No prompt - proceeds with incremental indexing normally
```

## Configuration Storage

The model configuration is stored in two places:

1. **Index metadata** (`.cicada/index.json`): Used for change detection
2. **Config file** (`.cicada/config.yaml`): Used for MCP server and other tools

Both are kept in sync automatically.

## API Reference

### Command Line Flags

The following flags affect model configuration:

- `--fast`: Fast tier - Token-based extraction with lemminflect (no model downloads)
- `--regular`: Regular tier - KeyBERT small model + GloVe (default, ~128MB)
- `--max`: Max tier - KeyBERT large model + FastText (~958MB+)

### Metadata Fields

- `keyword_method`: Either `"spacy"`, `"bert"`, or `null` (if keywords disabled)
- `model_tier`: Either `"fast"`, `"regular"`, `"max"`, or `null`

## Implementation Details

### Function: `prompt_model_change()`

Located in `cicada/indexer.py`, this function:

1. Displays the configuration change information
2. Uses `simple-term-menu` for interactive selection (falls back to text input if unavailable)
3. Returns `True` if user chooses to continue, `False` to abort
4. Exits with code 1 if user presses Ctrl+C

### When Detection Happens

The check occurs in `incremental_index_repository()`:

1. After loading existing index and hashes
2. Before processing any files
3. Only when `extract_keywords=True`
4. Only when old index had keywords enabled

### What Happens on Continue

If the user chooses to continue:

1. The function immediately calls `index_repository()` for a full reindex
2. All files are processed with the new model configuration
3. Old index is completely replaced
4. New metadata includes the updated model configuration

### What Happens on Abort

If the user chooses to abort:

1. The existing index is returned unchanged
2. No files are processed
3. Process exits normally with no changes made

## Testing

The feature is comprehensively tested in `tests/test_model_change_detection.py`:

- Model change detection (method change, tier change)
- User interaction (continue vs abort)
- Full reindex triggering
- No prompt when config unchanged
- No prompt when keywords disabled
- Metadata persistence
- Fallback to text input when terminal menu unavailable

Run tests with:

```bash
make test
# or specifically:
uv run pytest tests/test_model_change_detection.py -v
```

## Backward Compatibility

Indexes created before this feature was added will have `keyword_method` and `model_tier` set to `null` in their metadata. If you try to run an incremental index with keywords enabled on such an index:

- No prompt will be shown (because old metadata has `null` values)
- The index will be updated incrementally as before
- New metadata will include the model configuration

## Future Enhancements

Potential improvements for future versions:

1. **Automatic migration**: Offer to automatically reindex a subset of changed files
2. **Model compatibility matrix**: Allow some model changes without full reindex if compatible
3. **Index versioning**: Track index schema version for easier migrations
4. **Partial reindex**: Reindex only modules that would benefit most from the new model

## See Also

- [Interactive Setup Documentation](../cicada/interactive_setup.py)
- [Keyword Extraction Methods](../README.md#keyword-extraction)
- [Index Structure Documentation](INDEX_STRUCTURE.md)
