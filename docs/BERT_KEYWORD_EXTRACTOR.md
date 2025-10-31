# KeyBERT Integration Guide

## Overview

`KeyBERTExtractor` provides semantic keyword extraction using transformer embeddings as an alternative to the spaCy-based `KeywordExtractor`.

## API Compatibility

Both extractors implement identical interfaces:

```python
# Initialization
extractor = KeyBERTExtractor(verbose=True, model_tier="fast")

# Simple extraction (returns list of strings)
keywords = extractor.extract_keywords_simple(text, top_n=10)

# Full extraction (returns dict with scores and metadata)
results = extractor.extract_keywords(text, top_n=15)
```

## Model Tiers

| Tier | Model | Size | Init Time | Extract Time | Use Case |
|------|-------|------|-----------|--------------|----------|
| `fast` | all-MiniLM-L6-v2 | 80MB | ~55s | ~1.14s | Recommended default |
| `regular` | BAAI/bge-small-en-v1.5 | 133MB | ~61s | ~0.94s | Better semantics |
| `max` | paraphrase-mpnet-base-v2 | 420MB | ~252s | ~6.57s | Highest quality |

## Installation

```bash
uv add keybert
```

## Integration in `indexer.py`

### Method 1: Config File

```python
# Load from .cicada/config.yml
keyword_method = config.get("keywords", {}).get("method", "spacy")  # "spacy" or "bert"
bert_tier = config.get("keywords", {}).get("bert_tier", "fast")

# Instantiate
if keyword_method == "bert":
    from cicada.keybert_extractor import KeyBERTExtractor
    keyword_extractor = KeyBERTExtractor(verbose=True, model_tier=bert_tier)
else:
    from cicada.keyword_extractor import KeywordExtractor
    keyword_extractor = KeywordExtractor(verbose=True, model_size=spacy_model)
```

### Method 2: CLI Arguments

```python
# Add arguments
parser.add_argument("--keyword-method", choices=["spacy", "bert"], default="spacy")
parser.add_argument("--bert-model", choices=["fast", "regular", "max"])

# Use in index_repository()
if keyword_method == "bert":
    from cicada.keybert_extractor import KeyBERTExtractor
    keyword_extractor = KeyBERTExtractor(verbose=True, model_tier=bert_model_tier)
```

## Usage Example

```bash
# Config file approach
echo "keywords:\n  method: bert\n  bert_tier: fast" > .cicada/config.yml
cicada index --rag --fast

# CLI approach
cicada index --rag --fast
```

## Differences from Lemminflect

| Feature | Lemminflect | KeyBERT |
|---------|-------------|---------|
| Method | POS tagging + lemmatization | Semantic embeddings |
| Strengths | Linguistic structure | Semantic similarity |
| Keywords | Multi-word phrases | Single words only |
| `nouns`, `verbs`, etc. | ✅ Populated | ❌ Empty arrays |
| `noun_chunks` | Multi-word noun phrases | ❌ Empty array |
| Code identifier boost | 10x weight | 10x weight |
| Dependencies | spacy + models | keybert + sentence-transformers |

## Weighting Strategy

Both extractors apply identical weighting:
- **Code identifiers** (getUserData, snake_case): 10x boost
- **Code split words** (get, user, data): 3x boost
- **Regular keywords**: Base score

## No Changes Required

The rest of `indexer.py` (lines 103-140) works unchanged because both extractors return the same structure from `extract_keywords_simple()`.
