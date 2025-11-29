# PRD: Parallel Keyword Expansion

## Summary

Research and implementation of parallel keyword expansion for Cicada indexing. Successfully achieved ~800% CPU utilization using ThreadPoolExecutor with a two-phase architecture.

## Problem Statement

Keyword extraction and expansion during indexing runs single-threaded, making it a bottleneck for large codebases. With 4700+ items to expand, the expansion phase takes significant time.

## Research Findings

### Thread Safety Analysis

| Component | Thread-Safe | Notes |
|-----------|-------------|-------|
| GloVe (gensim KeyedVectors) | ✅ Yes | NumPy operations release GIL |
| FastText (gensim) | ✅ Yes | Same as GloVe |
| lemminflect | ✅ Yes | Pure Python, loads per thread |
| KeyBERT | ⚠️ Partial | Tokenizers have race conditions |

### Approaches Tried

| Approach | Result | Issue |
|----------|--------|-------|
| ThreadPoolExecutor | ✅ Works | GIL limits pure Python, but NumPy releases it |
| ProcessPoolExecutor + initializer | ❌ Slow | Each worker loads 10s model separately |
| ProcessPoolExecutor + fork | ❌ Crashes | macOS uses spawn by default |
| ProcessPoolExecutor + explicit fork context | ❌ Crashes | gensim doesn't survive fork after loading |

### Key Insight

Despite Python's GIL, **ThreadPoolExecutor achieves ~800% CPU utilization** because:
- gensim's `most_similar()` uses NumPy under the hood
- NumPy releases the GIL during array operations
- The actual similarity computation happens in C/BLAS, not Python

## Solution Architecture

### Two-Phase Approach

```
Phase 1: Extraction (sequential)
├── Parse all modules/functions
├── Extract keywords from docstrings (KeyBERT or regex)
└── Collect ExpansionTask objects (deferred)

Phase 2: Expansion (parallel)
├── Load GloVe model once (before ThreadPoolExecutor)
├── Create ThreadPoolExecutor with CPU-count workers
├── Submit all expansion tasks
└── Collect results and apply to targets
```

### Implementation

**New file:** `cicada/parallel_expander.py`
- `ParallelKeywordExpander` class wrapping `KeywordExpander`
- Pre-loads embedding model in `__init__` before parallel use
- `expand_keywords_parallel_with_scores()` for batch expansion
- Default workers = `os.cpu_count()`

**Modified:** `cicada/languages/python/indexer.py`
- Added `ExpansionTask` dataclass for deferred expansion
- `_extract_docstring_keywords()` collects tasks instead of expanding inline
- `_extract_string_keywords()` collects tasks instead of expanding inline
- New batch expansion phase after extraction

## Performance Results

| Configuration | Time | CPU Usage |
|--------------|------|-----------|
| 4 workers | 57.78s | ~400% |
| 10 workers (CPU count) | 49.03s | ~800% |

- **Items expanded:** 4704
- **Model loading:** Once (GloVe ~10s), lemminflect per thread (fast)
- **Total indexing time:** ~90s (down from previous inline approach)

## Configuration

The tier system controls extraction and expansion methods:

```yaml
# ~/.cicada/projects/<hash>/config.yaml
keyword_extraction:
  method: regular  # or "bert" for KeyBERT
keyword_expansion:
  method: glove    # or "lemmi", "fasttext"
```

Tier mappings:
- `--fast`: regular + lemmi
- `--regular`: regular + glove
- `--max`: bert + fasttext

## Current State (as of implementation)

### ✅ Completed

- `cicada/parallel_expander.py` - ThreadPoolExecutor wrapper with pre-loaded model
- `cicada/languages/python/indexer.py` - Two-phase deferred expansion
- `cicada/indexer.py` - Elixir indexer also uses ParallelKeywordExpander
- Verified working: 4704 items, 10 workers, ~800% CPU, 49s expansion time

### 🔄 Not Yet Done

- Tests in `tests/keywords/test_parallel_keywords.py` may need updating (were written for earlier approaches)
- No progress reporting during parallel expansion phase
- No baseline comparison (single-threaded expansion time not measured)

## Future Improvements

1. **Progress reporting**: Add periodic progress updates during parallel expansion
2. **Batch size tuning**: Experiment with chunking tasks for better cache locality
3. **ProcessPoolExecutor**: Revisit if gensim fixes fork compatibility
4. **KeyBERT parallelization**: Investigate batch inference for BERT models

## Files Changed

- `cicada/parallel_expander.py` (new)
- `cicada/languages/python/indexer.py` (modified for two-phase)
- `cicada/indexer.py` (Elixir - same pattern)
- `cicada/tier.py` (tier configuration)
- `tests/keywords/test_parallel_keywords.py` (new tests)
