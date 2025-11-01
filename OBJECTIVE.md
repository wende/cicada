# OBJECTIVE: 3-Workflow Keyword Extraction System

## Mission Brief
Augment Cicada's keyword extraction with semantic expansion capabilities. Implement 3 distinct workflows that balance speed, accuracy, and semantic coverage.

## Research Summary

### NLP Technologies Overview

#### KeyBERT
- BERT-based keyword extraction using semantic similarity
- Document embedding → candidate generation → similarity ranking
- Supports diversification (MMR) to avoid redundant keywords
- Works with any sentence-transformers model

#### all-MiniLM-L6-v2
- Lightweight sentence transformer (22MB, 384 dims)
- Fast inference: 14.7 ms / 1K tokens
- Max input: 256 word pieces
- Good balance of speed and accuracy

#### BAAI/bge-small
- State-of-the-art small embedding model (384 dims)
- 5-8% better retrieval accuracy than MiniLM
- Slower: 79-82 ms latency
- Better for accuracy-critical tasks

#### FastText
- Subword-based word embeddings (Facebook AI)
- Handles out-of-vocabulary (OOV) words via character n-grams
- Pre-trained: wiki-news-300d-1M (~650MB)
- Better for morphologically rich languages and rare words
- Implementation: gensim

#### GloVe
- Global vector embeddings (Stanford NLP)
- Uses global word co-occurrence statistics
- Pre-trained: glove.6B.300d (~1GB, 400K vocab)
- Cannot handle OOV words (whole-word only)
- Good for common words with sufficient training data
- Implementation: gensim KeyedVectors

#### Lemmatization
- Reduces words to dictionary form (lemma)
- "running", "ran", "runs" → "run"
- More accurate than stemming (uses vocabulary + POS)
- Current implementation: lemminflect

#### Keyword Expansion
- Uses word embeddings to find semantically similar terms
- Seed keyword → embedding space → find nearest neighbors
- Enhances search recall and semantic coverage
- Example: "authenticate" → ["verify", "validate", "login"]

## Strategic Decisions (Commander's Orders)

1. **Expansion**: Always-on for workflows 2 & 3 (automatic semantic expansion)
2. **Embeddings**: Support both FastText AND GloVe (user selects during setup)
3. **Expansion Count**: 2-3 similar words per keyword (conservative approach)
4. **Cleanup**: Remove "max" tier (420MB paraphrase-mpnet) entirely

## Workflow Architecture

### Workflow 1: Simple Extraction (Lemmatization)
```
Raw Text
   ↓
Tokenization
   ↓
Lemmatization (lemminflect)
   ↓
Frequency-based ranking
   ↓
Keywords (10x code identifiers, 3x split words)
```

**Characteristics:**
- Fast, proven, grammar-based
- No external models needed
- Current implementation: Keep as-is
- Use case: Speed-critical, proven reliability

### Workflow 2: Semantic Fast (KeyBERT MiniLM + Expansion)
```
Raw Text
   ↓
KeyBERT Extraction (all-MiniLM-L6-v2)
   ↓
Semantic Keywords (top 15)
   ↓
Keyword Expansion (FastText/GloVe)
   ↓
Expanded Keywords (2-3 per seed)
   ↓
Final Keyword Set
```

**Characteristics:**
- 80MB KeyBERT model + 650MB-1GB embeddings
- Fast inference (~1-2s per document)
- Semantic understanding + expansion
- Use case: Balanced speed and quality

### Workflow 3: Semantic Accurate (KeyBERT BGE + Expansion)
```
Raw Text
   ↓
KeyBERT Extraction (BAAI/bge-small)
   ↓
Semantic Keywords (top 15)
   ↓
Keyword Expansion (FastText/GloVe)
   ↓
Expanded Keywords (2-3 per seed)
   ↓
Final Keyword Set
```

**Characteristics:**
- 133MB KeyBERT model + 650MB-1GB embeddings
- Slower inference (~1.4s per document)
- Best semantic accuracy + expansion
- Use case: Quality-critical applications

## Implementation Plan

### 1. Create Keyword Expansion Module

**File:** `cicada/keyword_expander.py` (NEW)

**Requirements:**
- Class: `KeywordExpander`
- Support FastText and GloVe embeddings
- Lazy model loading (download on first use)
- Cache embeddings in `~/.cicada/embeddings/`
- Similarity threshold: 0.7 (configurable)
- Top-N expansion: 2-3 similar words per keyword

**API:**
```python
class KeywordExpander:
    def __init__(self, model_type: str, verbose: bool = False):
        """
        Args:
            model_type: "fasttext" or "glove"
            verbose: Print progress messages
        """

    def expand_keywords(
        self,
        keywords: list[str],
        top_n: int = 3,
        threshold: float = 0.7
    ) -> dict[str, list[tuple[str, float]]]:
        """
        Expand keywords using word embeddings.

        Returns:
            Dict mapping seed keyword to list of (similar_word, score)
        """
```

**Model Management:**
- FastText: Download `wiki-news-300d-1M-subword.bin` from Facebook Research
- GloVe: Download `glove.6B.300d.txt` from Stanford NLP
- Storage: `~/.cicada/embeddings/{fasttext|glove}/`
- Use gensim for both (FastText via `gensim.models.FastText`, GloVe via `gensim.models.KeyedVectors`)
- Show download progress with progress bar

**Expansion Logic:**
```python
def expand_keywords(self, keywords, top_n=3, threshold=0.7):
    expanded = {}
    for keyword in keywords:
        # Get most similar words
        similar = self.model.most_similar(keyword, topn=10)
        # Filter by threshold
        filtered = [(word, score) for word, score in similar if score >= threshold]
        # Take top N
        expanded[keyword] = filtered[:top_n]
    return expanded
```

### 2. Modify KeyBERTExtractor

**File:** `cicada/keybert_extractor.py` (MODIFY)

**Changes:**

1. **Remove "max" tier:**
```python
KEYBERT_MODELS = {
    "fast": "all-MiniLM-L6-v2",  # 80MB, fast extraction
    "regular": "BAAI/bge-small-en-v1.5",  # 133MB, balanced
    # REMOVED: "max": "paraphrase-mpnet-base-v2",
}
```

2. **Add expansion support to __init__:**
```python
def __init__(
    self,
    verbose: bool = False,
    model_tier: str | None = None,
    expansion_model: str | None = None  # NEW: "fasttext" | "glove" | None
):
    """
    Args:
        expansion_model: If provided, expand keywords using embeddings
    """
    self.expansion_model = expansion_model
    self.expander = None

    if expansion_model:
        from cicada.keyword_expander import KeywordExpander
        self.expander = KeywordExpander(expansion_model, verbose=verbose)
```

3. **Update extract_keywords method:**
```python
def extract_keywords(self, text: str, top_n: int = 15) -> dict[str, Any]:
    # ... existing KeyBERT extraction ...

    # NEW: Expand keywords if expander is available
    if self.expander:
        top_keyword_strings = [kw for kw, _ in top_keywords]
        expanded = self.expander.expand_keywords(top_keyword_strings, top_n=3)

        # Add expanded words to keyword list
        for seed, similar_words in expanded.items():
            for word, score in similar_words:
                # Add with reduced score (expansion is less confident)
                if word.lower() not in keyword_scores:
                    keyword_scores[word.lower()] = score * 0.5

        # Re-sort and take top_n after expansion
        top_keywords = sorted(keyword_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]

    return {
        "top_keywords": top_keywords,
        # ... rest of return dict ...
        "expanded_keywords": expanded if self.expander else {},  # NEW field
    }
```

### 3. Update Interactive Setup

**File:** `cicada/interactive_setup.py` (MODIFY)

**Changes:**

1. **Replace 2-step menu with 3-workflow menu:**

```python
def show_first_time_setup() -> tuple[str, str, str]:
    """
    Returns:
        tuple[str, str, str]: (method, tier, expansion)
        Examples:
            ("lemminflect", "regular", "none")
            ("bert", "fast", "fasttext")
            ("bert", "regular", "glove")
    """
    # Step 1: Choose workflow
    workflow_items = [
        "Simple - Lemminflect (fast, grammar-based)",
        "Semantic Fast - MiniLM + Expansion (balanced)",
        "Semantic Accurate - BGE + Expansion (best quality)",
    ]

    workflow_index = show_menu(workflow_items, "Step 1/2: Choose workflow")

    if workflow_index == 0:
        # Lemminflect - no expansion
        return ("lemminflect", "regular", "none")

    # Step 2: Choose expansion embeddings (for BERT workflows)
    expansion_items = [
        "FastText wiki-news (650MB, better rare words)",
        "GloVe 6B (1GB, faster for common words)",
    ]

    expansion_index = show_menu(expansion_items, "Step 2/2: Choose embeddings")

    method = "bert"
    tier = "fast" if workflow_index == 1 else "regular"
    expansion = "fasttext" if expansion_index == 0 else "glove"

    return (method, tier, expansion)
```

2. **Update text-based fallback:**
```python
def _text_based_setup() -> tuple[str, str, str]:
    print("1. Simple - Lemminflect (fast, grammar-based)")
    print("2. Semantic Fast - MiniLM + Expansion (balanced)")
    print("3. Semantic Accurate - BGE + Expansion (best quality)")
    # ... handle input ...

    if workflow == "1":
        return ("lemminflect", "regular", "none")

    print("\nChoose expansion embeddings:")
    print("1. FastText wiki-news (650MB, better rare words)")
    print("2. GloVe 6B (1GB, faster common words)")
    # ... handle input ...

    return (method, tier, expansion)
```

3. **Update show_full_interactive_setup:**
```python
def show_full_interactive_setup(repo_path: str | Path | None = None) -> None:
    # ... editor selection ...

    # Get workflow config
    method, tier, expansion = show_first_time_setup()

    # Run setup
    setup(
        editor,
        repo_path,
        keyword_method=method,
        keyword_tier=tier,
        keyword_expansion=expansion  # NEW parameter
    )
```

### 4. Update Config Schema

**File:** `cicada/setup.py` (MODIFY)

**Changes:**

1. **Add expansion field to config.yaml generation:**
```python
def generate_config(
    repo_path: Path,
    method: str = "lemminflect",
    tier: str = "regular",
    expansion: str = "none"  # NEW parameter
) -> dict:
    return {
        "repo_path": str(repo_path),
        "keyword_extraction": {
            "method": method,
            "tier": tier,
            "expansion": expansion,  # NEW field
        }
    }
```

2. **Update setup function signature:**
```python
def setup(
    editor: EditorType,
    repo_path: Path | str,
    keyword_method: str = "lemminflect",
    keyword_tier: str = "regular",
    keyword_expansion: str = "none",  # NEW parameter
    index_exists: bool = False,
):
    # ... generate config with expansion field ...
```

**Example config.yaml:**
```yaml
repo_path: /path/to/project
keyword_extraction:
  method: bert
  tier: fast
  expansion: fasttext
```

### 5. Update Indexer

**File:** `cicada/indexer.py` (MODIFY)

**Changes:**

1. **Update _load_config to read expansion:**
```python
def _load_config(self, repo_path: Path) -> tuple[str, str, str]:
    """
    Returns:
        tuple[str, str, str]: (method, tier, expansion)
    """
    config_path = get_config_path(repo_path)

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)

        method = config["keyword_extraction"].get("method", "lemminflect")
        tier = config["keyword_extraction"].get("tier", "regular")
        expansion = config["keyword_extraction"].get("expansion", "none")  # NEW

        return (method, tier, expansion)
    except Exception:
        return ("lemminflect", "regular", "none")
```

2. **Update _initialize_keyword_extractor:**
```python
def _initialize_keyword_extractor(self, method: str, tier: str, expansion: str):
    """
    Args:
        expansion: "fasttext" | "glove" | "none"
    """
    if method == "bert":
        from cicada.keybert_extractor import KeyBERTExtractor

        expansion_model = None if expansion == "none" else expansion

        self.keyword_extractor = KeyBERTExtractor(
            model_tier=tier,
            expansion_model=expansion_model,  # NEW
            verbose=self.verbose
        )
    else:
        from cicada.lightweight_keyword_extractor import LightweightKeywordExtractor
        self.keyword_extractor = LightweightKeywordExtractor(verbose=self.verbose)
```

3. **Handle model downloads in index() method:**
```python
def index(self, repo_path: Path, ...):
    # ... existing code ...

    method, tier, expansion = self._load_config(repo_path)

    # Initialize keyword extractor (may trigger downloads)
    if self.verbose:
        if expansion != "none":
            print(f"Using {method} with {tier} model + {expansion} expansion")
        else:
            print(f"Using {method} extraction")

    self._initialize_keyword_extractor(method, tier, expansion)

    # ... rest of indexing ...
```

### 6. Update CLI

**File:** `cicada/cli.py` (MODIFY)

**Changes:**

1. **Remove references to "max" tier:**
- Remove from help text
- Remove from any tier validation
- Update comments

2. **Update flag descriptions:**
```python
parser.add_argument(
    "--nlp",
    action="store_true",
    help="Use lemminflect-based keyword extraction (Workflow 1: Simple)",
)

parser.add_argument(
    "--rag",
    choices=["fast", "regular"],
    help="Use KeyBERT semantic extraction (Workflow 2: fast=MiniLM, Workflow 3: regular=BGE)",
)

parser.add_argument(
    "--expand",
    choices=["fasttext", "glove"],
    help="Add keyword expansion using embeddings (applies to --rag only)",
)
```

3. **Update command parsing:**
```python
def handle_index_command(args):
    method = "lemminflect"
    tier = "regular"
    expansion = "none"

    if args.nlp:
        method = "lemminflect"
    elif args.rag:
        method = "bert"
        tier = args.rag  # "fast" or "regular"
        expansion = args.expand if args.expand else "none"

    # Pass to indexer
    indexer.index(
        repo_path=args.path,
        keyword_method=method,
        keyword_tier=tier,
        keyword_expansion=expansion
    )
```

4. **Update help messages:**
```bash
$ cicada index --help

Workflows:
  --nlp                Simple lemminflect extraction (fast, proven)
  --rag fast           Semantic MiniLM + expansion (balanced)
  --rag regular        Semantic BGE + expansion (best quality)

Expansion (use with --rag):
  --expand fasttext    Use FastText embeddings (650MB, better OOV)
  --expand glove       Use GloVe embeddings (1GB, faster)
```

### 7. Dependencies & Model Management

**File:** `pyproject.toml` (VERIFY)

**Current dependencies:**
```toml
dependencies = [
    "keybert>=0.8.0",      # ✓ Already present
    "lemminflect>=0.2.3",  # ✓ Already present
    "gensim>=4.4.0",       # ✓ Already present
]
```

**Model Download Helper:**

Add to `cicada/keyword_expander.py`:

```python
def _download_fasttext():
    """Download FastText wiki-news-300d-1M model."""
    import urllib.request

    url = "https://dl.fbaipublicfiles.com/fasttext/vectors-english/wiki-news-300d-1M-subword.bin.zip"
    target = Path.home() / ".cicada/embeddings/fasttext"
    target.mkdir(parents=True, exist_ok=True)

    zip_path = target / "wiki-news-300d-1M-subword.bin.zip"
    bin_path = target / "wiki-news-300d-1M-subword.bin"

    if bin_path.exists():
        return bin_path

    print(f"Downloading FastText embeddings (~650MB)...")
    urllib.request.urlretrieve(url, zip_path, reporthook=_download_progress)

    # Extract
    import zipfile
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(target)

    zip_path.unlink()
    return bin_path

def _download_glove():
    """Download GloVe 6B 300d model."""
    url = "https://nlp.stanford.edu/data/glove.6B.zip"
    target = Path.home() / ".cicada/embeddings/glove"
    target.mkdir(parents=True, exist_ok=True)

    zip_path = target / "glove.6B.zip"
    txt_path = target / "glove.6B.300d.txt"

    if txt_path.exists():
        return txt_path

    print(f"Downloading GloVe embeddings (~1GB)...")
    urllib.request.urlretrieve(url, zip_path, reporthook=_download_progress)

    # Extract only 300d file
    import zipfile
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extract("glove.6B.300d.txt", target)

    zip_path.unlink()
    return txt_path

def _download_progress(block_num, block_size, total_size):
    """Progress callback for downloads."""
    downloaded = block_num * block_size
    percent = min(100, (downloaded / total_size) * 100)
    print(f"\rProgress: {percent:.1f}%", end="", flush=True)
```

### 8. Remove Unused Code

**Files to clean up:**

1. **cicada/keybert_extractor.py:**
   - Remove "max" from `KEYBERT_MODELS` dict
   - Update docstrings to remove max tier references

2. **cicada/interactive_setup.py:**
   - Remove "Max (420MB)" from all menu items
   - Update tier_map to only have {0: "fast", 1: "regular"}

3. **cicada/cli.py:**
   - Remove "max" from any help text
   - Remove tier validation for "max"

4. **Tests:**
   - Update test fixtures to remove "max" tier tests
   - Add tests for expansion workflows

### 9. Testing Strategy

**Test Coverage:**

1. **Unit Tests:**
   - `test_keyword_expander.py` (NEW)
     - Test FastText expansion
     - Test GloVe expansion
     - Test similarity threshold filtering
     - Test top-N limiting
     - Test model caching

2. **Integration Tests:**
   - `test_keybert_extractor.py` (MODIFY)
     - Test extraction with expansion
     - Test expanded_keywords field in output
     - Verify 2-3 expansions per seed

3. **E2E Tests:**
   - `test_interactive_setup.py` (MODIFY)
     - Test all 3 workflow selections
     - Test expansion embedding selection
     - Test config generation with expansion field

4. **Backward Compatibility:**
   - Test loading old configs without expansion field
   - Default to "none" expansion
   - Verify lemminflect still works

**Test Data:**
```python
# Example test case
def test_expansion_fasttext():
    expander = KeywordExpander("fasttext")
    result = expander.expand_keywords(["database"], top_n=3, threshold=0.7)

    assert "database" in result
    assert len(result["database"]) <= 3
    assert all(score >= 0.7 for word, score in result["database"])
    # Expect words like: "databases", "postgresql", "mysql", "storage"
```

## User Experience Flow

### CLI Usage

**Workflow 1 (Simple):**
```bash
$ cicada index --nlp
Using lemminflect extraction (Simple workflow)
Indexed 150 files in 2.3s
```

**Workflow 2 (Semantic Fast):**
```bash
$ cicada index --rag fast --expand fasttext
Using bert with fast model + fasttext expansion
Downloading FastText embeddings (~650MB)...
Progress: 100.0%
Loading FastText model... ✓
Indexed 150 files in 5.8s (including model download)
```

**Workflow 3 (Semantic Accurate):**
```bash
$ cicada index --rag regular --expand glove
Using bert with regular model + glove expansion
GloVe embeddings already cached ✓
Loading GloVe model... ✓
Indexed 150 files in 7.2s
```

### Interactive Setup

```bash
$ cicada claude
==================================================================
🦗 Welcome to CICADA - Elixir Code Intelligence
==================================================================

Let's set up Cicada for your editor and project.

Step 1/3: Choose your editor
» Claude Code - AI-powered code editor
  Cursor - AI-first code editor
  VS Code - Visual Studio Code

✓ Selected: CLAUDE

Step 2/3: Choose workflow
» Simple - Lemminflect (fast, grammar-based)
  Semantic Fast - MiniLM + Expansion (balanced)
  Semantic Accurate - BGE + Expansion (best quality)

✓ Selected: Semantic Fast

Step 3/3: Choose embeddings
» FastText wiki-news (650MB, better rare words)
  GloVe 6B (1GB, faster common words)

✓ Selected: FastText

Running setup...

Downloading FastText embeddings (~650MB)...
Progress: 100.0%

✓ Model loaded successfully
✓ Indexed 150 files with keyword extraction
✓ MCP config created: .mcp.json
✓ Config saved: ~/.cicada/projects/abc123/config.yaml

Setup complete! Restart Claude Code to activate Cicada.
```

## Technical Specifications

### Expansion Algorithm

**Pseudocode:**
```
function expand_keywords(seeds, top_n=3, threshold=0.7):
    expanded = {}
    for seed in seeds:
        # Get embedding
        seed_vector = model.get_vector(seed)

        # Find similar words
        similar = model.most_similar(seed, topn=10)

        # Filter by threshold
        filtered = [(word, score) for (word, score) in similar if score >= threshold]

        # Take top N
        expanded[seed] = filtered[:top_n]

    return expanded
```

**Example Output:**
```python
seeds = ["authentication", "database", "cache"]
expanded = expander.expand_keywords(seeds, top_n=3, threshold=0.7)

# Result:
{
    "authentication": [
        ("verify", 0.85),
        ("authorize", 0.82),
        ("validate", 0.78)
    ],
    "database": [
        ("postgresql", 0.88),
        ("storage", 0.81),
        ("mysql", 0.76)
    ],
    "cache": [
        ("redis", 0.87),
        ("caching", 0.84),
        ("memcache", 0.79)
    ]
}
```

### Config Schema Evolution

**v0.2.0 (current):**
```yaml
keyword_extraction:
  method: bert
  tier: fast  # or regular or max
```

**v0.3.0 (target):**
```yaml
keyword_extraction:
  method: bert
  tier: fast  # or regular (max removed)
  expansion: fasttext  # or glove or none (NEW)
```
### Performance Estimates

**Workflow 1 (Lemminflect):**
- Time per doc: ~50ms
- Memory: ~100MB
- Disk: 0MB (no models)

**Workflow 2 (MiniLM + FastText):**
- Time per doc (first run): ~1.5s + download time
- Time per doc (cached): ~1.2s
- Memory: ~2GB (models in RAM)
- Disk: ~730MB (80MB + 650MB)

**Workflow 3 (BGE + GloVe):**
- Time per doc (first run): ~2.5s + download time
- Time per doc (cached): ~2.0s
- Memory: ~2.5GB (models in RAM)
- Disk: ~1.1GB (133MB + 1GB)

**Indexing 150-file Phoenix app:**
- Workflow 1: ~7s
- Workflow 2: ~180s (3 min)
- Workflow 3: ~300s (5 min)

## Risk Analysis

### High Priority Risks

1. **Large Download Sizes**
   - **Risk**: Users on slow connections or metered data
   - **Mitigation**: Show size warnings, allow cancellation, cache models

2. **Memory Consumption**
   - **Risk**: Loading 1GB+ models into RAM
   - **Mitigation**: Lazy load, unload after indexing, document requirements

3. **Disk Space**
   - **Risk**: ~1-2GB storage required
   - **Mitigation**: Check free space before download, clear cache option

### Medium Priority Risks

4. **Backward Compatibility**
   - **Risk**: Breaking existing configs
   - **Mitigation**: Default "expansion: none", handle missing fields

5. **Model Download Failures**
   - **Risk**: Network errors, incomplete downloads
   - **Mitigation**: Retry logic, checksum validation, graceful fallback

6. **Performance Degradation**
   - **Risk**: Expansion adds latency
   - **Mitigation**: Profile and optimize, document performance trade-offs

### Low Priority Risks

7. **Embedding Quality Variance**
   - **Risk**: FastText vs GloVe produce different results
   - **Mitigation**: Document differences, allow user choice

8. **Storage Location Conflicts**
   - **Risk**: Multiple users on same machine
   - **Mitigation**: Store in user home directory (~/.cicada)

## Success Metrics

1. **Functional Requirements:**
   - ✓ All 3 workflows implemented and tested
   - ✓ Interactive setup allows workflow + embedding selection
   - ✓ Models download and cache correctly
   - ✓ Expansion produces 2-3 relevant similar words
   - ✓ Backward compatibility maintained

2. **Performance Requirements:**
   - ✓ Workflow 1: < 10s for 150 files
   - ✓ Workflow 2: < 5min for 150 files (including download)
   - ✓ Workflow 3: < 8min for 150 files (including download)
   - ✓ Subsequent runs: Use cached models

3. **User Experience:**
   - ✓ Clear workflow descriptions in interactive menu
   - ✓ Download progress indicators
   - ✓ Helpful error messages for failures
   - ✓ Config persists across runs

4. **Code Quality:**
   - ✓ All new code has unit tests
   - ✓ Integration tests for workflows
   - ✓ Documentation updated (README, CLAUDE.md)
   - ✓ No unused code (max tier removed)

## Follow-up Tasks

**Post-Implementation:**
1. Update README.md with new workflows
2. Update CHANGELOG.md for v0.3.0
3. Create migration guide for users upgrading from v0.2.0
4. Add performance benchmarks to docs
5. Consider adding workflow comparison table to README

**Future Enhancements (v0.4.0+):**
1. Support custom expansion models (user-provided embeddings)
2. Add semantic caching (cache expanded keywords)
3. Implement adaptive expansion (vary top_n based on keyword importance)
4. Add telemetry to understand which workflows are most popular
5. Consider supporting sentence-level embeddings for better context

## References

**Research Documents:**
- KeyBERT: https://github.com/MaartenGr/KeyBERT
- FastText: https://fasttext.cc/
- GloVe: https://nlp.stanford.edu/projects/glove/
- Gensim: https://radimrehurek.com/gensim/
- Sentence Transformers: https://www.sbert.net/

**Model Downloads:**
- FastText wiki-news: https://dl.fbaipublicfiles.com/fasttext/vectors-english/
- GloVe 6B: https://nlp.stanford.edu/data/glove.6B.zip
- all-MiniLM-L6-v2: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
- BAAI/bge-small: https://huggingface.co/BAAI/bge-small-en-v1.5

---

**End of Mission Brief**

Commander, the complete operational plan has been documented. Ready to execute on your command.
