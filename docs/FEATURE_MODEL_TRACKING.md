# Feature: Model Configuration Tracking for Incremental Indexing

## Summary

Added automatic detection and warning when users attempt to change the keyword extraction model configuration during incremental indexing. This prevents inconsistent indexes and helps users understand when a full reindex is required.

## Problem Statement

Previously, users could:
1. Index their codebase with one model (e.g., spaCy + Regular tier)
2. Later run incremental indexing with a different model (e.g., KeyBERT + Max tier)
3. End up with an inconsistent index where some modules use one model and others use a different model

This led to:
- Unpredictable search results
- Poor semantic search quality
- Confusion about which model configuration was actually in use

## Solution

### 1. Metadata Tracking

**Modified Files:**
- `cicada/indexer.py` - Added `keyword_method` and `model_tier` to index metadata

**Changes:**
```python
"metadata": {
    "indexed_at": "2024-01-15T10:30:00",
    "total_modules": 150,
    "total_functions": 1200,
    "repo_path": "/path/to/repo",
    "keyword_method": "spacy",  # NEW: tracks extraction method
    "model_tier": "regular",     # NEW: tracks model tier
}
```

### 2. Change Detection

**Modified Files:**
- `cicada/indexer.py` - Added detection logic in `incremental_index_repository()`

**Logic:**
- On incremental index, compare new model config with metadata from existing index
- If different, prompt user with options:
  - Continue → Trigger full reindex with new model
  - Abort → Keep existing index unchanged

### 3. Interactive User Prompt

**New Functions:**
- `prompt_model_change()` in `cicada/indexer.py`

**Features:**
- Uses same interactive library as setup (`simple-term-menu`)
- Falls back to text-based input if terminal menu unavailable
- Clearly shows old vs new configuration
- Handles keyboard interrupts gracefully

**Example Output:**
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

## Files Changed

### Core Implementation
- `cicada/indexer.py`: 
  - Added `prompt_model_change()` function (90 lines)
  - Modified `index_repository()` to store model config in metadata (2 lines)
  - Modified `incremental_index_repository()` to detect and prompt on changes (34 lines)

### Tests
- `tests/test_model_change_detection.py` (NEW):
  - 12 comprehensive test cases covering:
    - Model method changes
    - Model tier changes
    - User choosing to continue vs abort
    - Full reindex triggering
    - No prompt when config unchanged
    - No prompt when keywords disabled
    - Metadata persistence
    - Terminal menu and text fallback modes

### Documentation
- `docs/MODEL_CHANGE_DETECTION.md` (NEW):
  - Complete feature documentation
  - Usage examples
  - API reference
  - Implementation details
  - Testing guide

## Behavior Changes

### Before This Feature
```bash
# Initial index with fast tier (token-based)
$ cicada index --fast
✓ Indexing complete! Modules: 150

# Later, switching to max tier BERT (SILENTLY creates inconsistent index)
$ cicada index --max
✓ Processing 5 changed files...
✓ Index updated!
# ⚠️  INDEX NOW INCONSISTENT: 145 modules use fast, 5 use max
```

### After This Feature
```bash
# Initial index with fast tier (token-based)
$ cicada index --fast
✓ Indexing complete! Modules: 150

# Later, switching to max tier BERT (PROMPTS USER)
$ cicada index --max
⚠  Model Configuration Change Detected

  Previous configuration:
    Tier: FAST (token-based)

  New configuration:
    Tier: MAX (BERT large)

  Changing the model requires reindexing the entire codebase.

What would you like to do?
» Continue - Reindex entire codebase with new model
  Abort - Keep existing index with old model

# User selects "Continue"
✓ Proceeding with full reindex
✓ Indexing complete! Modules: 150
# ✅ INDEX NOW CONSISTENT: All 150 modules use KeyBERT Max
```

## Backward Compatibility

✅ **Fully backward compatible**

- Old indexes without model metadata: No prompt shown, works as before
- Config file format: Unchanged (already had `keywords.method` and `keywords.model`)
- API: No breaking changes, all parameters remain optional
- Tests: All existing 884 tests still pass + 12 new tests

## Edge Cases Handled

1. **No existing index**: Proceeds with full index (no prompt)
2. **No existing hashes**: Proceeds with full index (no prompt)
3. **Keywords disabled in old index**: No prompt (can't detect what wasn't tracked)
4. **Keywords disabled in new run**: No prompt (not using models anyway)
5. **Same configuration**: No prompt (no change detected)
6. **Keyboard interrupt during prompt**: Graceful exit with cleanup
7. **Terminal doesn't support menus**: Falls back to text input

## Testing

All tests passing: **896/896** (including 12 new tests)

```bash
$ make test
...
============================= 896 passed in 7.73s ==============================
```

New test coverage:
- Model change detection
- User interaction flows
- Metadata persistence
- Prompt fallback modes
- Edge cases

## Usage

No changes to existing workflows. Users only see prompts when they change model configuration:

```bash
# Regular incremental indexing (no model change)
$ cicada index --regular  # First time
$ cicada index --regular  # Later - no prompt

# Changing model configuration
$ cicada index --max      # Prompt shown, user chooses
```

## Benefits

1. **Prevents inconsistent indexes**: Users can't accidentally create mixed-model indexes
2. **Better UX**: Clear communication about what's happening and why
3. **Explicit choice**: Users consciously decide whether to reindex
4. **Maintains quality**: Ensures semantic search remains consistent
5. **Educational**: Helps users understand model configuration impacts
6. **Safe**: Easy to abort and keep existing index

## Future Enhancements

Potential improvements for future versions:
- Smart partial reindexing (only changed modules)
- Model compatibility matrix (allow some changes without full reindex)
- Automatic migration suggestions
- Index schema versioning