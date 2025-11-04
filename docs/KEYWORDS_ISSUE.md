# Keywords Issue Report

**Date:** 2025-11-03
**Status:** 🔴 Critical - Keyword scores are being discarded throughout the pipeline

---

## Executive Summary

Cicada's keyword extraction system computes relevance scores for keywords, but these scores are **never exported to the index**. The keyword search falls back to assigning all keywords a uniform score of `1.0`, effectively degrading the search from **weighted relevance ranking** to **boolean matching**. This significantly impacts search quality and wastes computational resources.

---

## The Problem

### What We Found

1. **Keywords exported as lists instead of dicts with scores**
   - Index contains: `"keywords": ["calculator", "python", "class"]`
   - Should contain: `"keywords": {"calculator": 0.85, "python": 0.72, "class": 0.65}`

2. **All keywords get equal weight in search**
   - Search assigns uniform `1.0` score to all keywords
   - "calculator" and "optional" both score `1.0` even though "calculator" should be weighted higher
   - Search relevance is broken

3. **Wasted computation**
   - Extractors carefully compute TF scores and semantic similarity scores
   - All scores are immediately discarded
   - CPU cycles and memory spent on computations that are never used

---

## Root Cause Analysis

### The Pipeline Disconnect

```
[Extractor] → [Simple Wrapper] → [SCIP Converter] → [Index JSON] → [Search]
  computes       throws away       uses simple        stores         assigns
  scores         scores            method             lists          uniform 1.0
```

### Code Locations

1. **`cicada/languages/elixir/extractors/keyword.py:95-104`**
   ```python
   def extract_keywords_simple(self, text: str, top_n: int = 10) -> list[str]:
       results = self.extract_keywords(text, top_n=top_n)
       return [keyword for keyword, _ in results["top_keywords"]]  # ← SCORES DISCARDED
   ```

2. **`cicada/languages/scip/converter.py:180, 299`**
   ```python
   # Module keywords
   module_keywords = self.keyword_extractor.extract_keywords_simple(
       module_text, top_n=10
   )  # ← Uses the wrong method

   # Function keywords
   func_keywords = self.keyword_extractor.extract_keywords_simple(
       func_text, top_n=10
   )  # ← Uses the wrong method
   ```

3. **`cicada/keyword_search.py:59-65, 86-90` (NOW REMOVED)**
   ```python
   # OLD CODE - Had silent fallback
   if isinstance(keywords_dict, list):
       keywords_dict = {kw.lower(): 1.0 for kw in keywords_dict}  # ← ALL SCORES BECOME 1.0
   ```

---

## Impact Assessment

### Search Quality
- ❌ **No relevance ranking**: All matching keywords contribute equally
- ❌ **Poor result ordering**: High-relevance results not prioritized
- ❌ **False precision**: Users can't distinguish important vs incidental matches

### Performance
- ⚠️ **Wasted CPU**: TF-IDF and semantic analysis computed but never used
- ⚠️ **Wasted memory**: Full extraction results built then discarded
- ⚠️ **No benefit**: Users pay performance cost for zero benefit

### User Experience
- 😞 Search returns technically correct results but poorly ranked
- 😞 No way to distinguish "authentication service" from "authenticate helper"
- 😞 Semantic search (BERT/KeyBERT) provides no advantage over simple extraction

---

## Current State (After Investigation)

### Changes Made
✅ **Removed silent fallback** in `cicada/keyword_search.py`
- Now raises `TypeError` when keywords are lists instead of dicts
- Forces the issue to surface instead of hiding it

### Test Results
- ❌ **24/26 keyword search tests failing** - Expected, exposes the issue
- ✅ **SCIP converter tests passing** - They only check for keyword presence, not format
- ⚠️ **Real indexing still produces lists** - Core issue remains

### What Still Works
- ✅ Keyword extraction (extractors work correctly internally)
- ✅ SCIP conversion (still runs, just exports wrong format)
- ✅ Modules without keywords (unaffected by this issue)

### What's Broken Now
- ❌ Keyword search (intentionally broken to expose issue)
- ❌ Any code path that loads index with keywords
- ❌ MCP server keyword search tool

---

## What Needs To Be Fixed

### 1. Change `extract_keywords_simple()` Return Type
**File:** `cicada/languages/elixir/extractors/keyword.py`

```python
def extract_keywords_simple(self, text: str, top_n: int = 10) -> dict[str, float]:
    """Extract keywords and return as {keyword: score} dict."""
    if not text or not text.strip():
        return {}
    try:
        results = self.extract_keywords(text, top_n=top_n)
        return dict(results["top_keywords"])  # ← Return dict, not list
    except Exception as e:
        if self.verbose:
            print(f"Warning: Keyword extraction failed: {e}", file=sys.stderr)
        return {}
```

### 2. Update SCIP Converter
**File:** `cicada/languages/scip/converter.py`

No changes needed - it already uses `extract_keywords_simple()`, which will now return the correct format.

### 3. Update Elixir Indexer
**File:** `cicada/languages/elixir/indexer.py`

Check if it also uses `extract_keywords_simple()` - should automatically work once method returns dict.

### 4. Update Tests
**Files:**
- `tests/test_keyword_search.py` - Update fixtures to use dict format
- `tests/languages/scip/test_scip_converter.py` - Verify dict format is exported
- `tests/languages/elixir/test_indexer.py` - Update keyword assertions

### 5. Update Schema Documentation
**File:** `cicada/parsing/schema.py`

Update `UniversalIndexSchema` to document that keywords must be `dict[str, float]`:

```python
keywords: dict[str, float]  # Keyword -> relevance score mapping
```

---

## Migration Path

### For Existing Indexes

Option 1: **Force reindex**
- Users must reindex their projects after upgrade
- Clear documentation in release notes

Option 2: **Migration script**
- Detect old list format
- Convert to dict with uniform scores as temporary measure
- Warn users to reindex for proper scores

Recommendation: **Option 1** (Force reindex) - cleaner, no technical debt

---

## Testing Strategy

### Unit Tests
1. Test `extract_keywords_simple()` returns dict with scores
2. Test SCIP converter produces dict format
3. Test keyword search with dict format
4. Test score-based ranking works correctly

### Integration Tests
1. Index sample Python project
2. Verify index.json contains keyword dicts
3. Run keyword search
4. Verify results are properly ranked by score

### Regression Tests
1. Test empty keywords (should return `{}`)
2. Test extraction failures (should return `{}`)
3. Test keyword-less modules (should work as before)

---

## Priority: Critical

This issue affects:
- ✅ Search quality (high impact)
- ✅ Performance efficiency (medium impact)
- ✅ User experience (high impact)
- ✅ Data integrity (schema mismatch)

**Recommended action:** Fix in next release, require reindexing.

---

## Related Files

### Core Implementation
- `cicada/languages/elixir/extractors/keyword.py` - Keyword extractor base
- `cicada/languages/elixir/extractors/keybert.py` - BERT-based extractor
- `cicada/languages/scip/converter.py` - SCIP to Cicada converter
- `cicada/languages/elixir/indexer.py` - Elixir indexer
- `cicada/keyword_search.py` - Search implementation

### Tests
- `tests/test_keyword_search.py` - Search tests (24 failing)
- `tests/languages/scip/test_scip_converter.py` - Converter tests
- `tests/languages/elixir/test_indexer.py` - Indexer tests
- `test_python_indexer_keywords.py` - Python indexer test

### Schema
- `cicada/parsing/schema.py` - Index schema definition

---

## Questions for Discussion

1. Should we support both formats during migration period?
2. What's the minimum score threshold for including keywords?
3. Should we normalize scores to 0-1 range across all extractors?
4. Do we need version detection in the index for backward compatibility?

---

**Next Steps:** See TODO in this file for implementation checklist.
