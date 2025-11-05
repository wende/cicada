# Executable Bundling Research for CICADA

**Date**: October 29, 2025
**Author**: Claude
**Status**: Research Complete

## Executive Summary

CICADA can technically be bundled into a single executable, but **it is not recommended** for production use due to significant practical challenges. The current `uv tool install` approach provides a much better out-of-the-box experience than a bundled executable would.

### Key Verdict: ❌ NOT RECOMMENDED

**Reasons:**
1. **Size**: Final executable would be 500MB-1GB+ (mostly due to spaCy)
2. **Complexity**: High maintenance burden for multi-platform builds
3. **spaCy challenges**: Well-documented issues with model loading in bundled environments
4. **External dependencies**: Still requires Git (and optionally GitHub CLI)
5. **Current solution is better**: `uv tool install` is fast, reliable, and platform-independent

---

## Current Installation Experience

CICADA currently uses `uv tool install`, which provides:
- ✅ **Single command installation**: `uv tool install git+https://github.com/wende/cicada.git@v0.1.1`
- ✅ **Fast startup**: Commands available immediately after install
- ✅ **Isolated environments**: Each tool gets its own virtual environment
- ✅ **Cross-platform**: Works identically on Windows, macOS, Linux
- ✅ **Easy updates**: `uv tool upgrade cicada`
- ⚠️ **Requires**: uv and Python 3.10+ on target system

---

## Project Analysis

### Technology Stack

**Core Application:**
- Python 3.10+ (~392KB of source code)
- 5 entry points:
  - `cicada-mcp` (MCP server)
  - `cicada` (project setup)
  - `cicada-index` (Elixir indexer)
  - `cicada-index-pr` (PR indexer)
  - `cicada-find-dead-code` (dead code analyzer)

**Python Dependencies:**
| Package | Bundling Difficulty | Notes |
|---------|-------------------|-------|
| mcp | ✅ Easy | Pure Python |
| pyyaml | ✅ Easy | Pure Python with C extensions, well-supported |
| tree-sitter | ⚠️ Moderate | Native code, but has binary wheels |
| tree-sitter-elixir | ⚠️ Moderate | Native code, binary wheels available |
| gitpython | ✅ Easy | Pure Python wrapper around Git |
| **spacy** | ❌ **VERY HARD** | Large (500MB+), complex model loading, documented bundling issues |
| rank-bm25 | ✅ Easy | Pure Python |

**External Tool Dependencies:**
- **Git** (required) - Used by GitPython for commit history, blame, etc.
- **GitHub CLI (`gh`)** (optional) - Only for PR indexing features

---

## Bundling Options Evaluated

### 1. PyInstaller (Most Popular)

**How it works:**
- Analyzes Python code and dependencies
- Creates executable with embedded Python interpreter
- Bundles all dependencies and data files

**Pros:**
- Most mature and widely used
- Good documentation and community support
- Works with most Python packages
- Can create single-file executables

**Cons:**
- **Major spaCy issues**: Well-documented problems with model loading
  - Models don't get discovered properly in bundled environment
  - Requires complex hooks and manual configuration
  - Users report needing to extract models to external directories
  - Registry errors for transformer models
- Large executable size (500MB-1GB with spaCy models)
- Slow build times
- Requires separate builds for each platform
- Single-file mode is even slower to start

**Verdict for CICADA:** ⚠️ Possible but painful

### 2. Nuitka (Python-to-C Compiler)

**How it works:**
- Compiles Python code to C
- Links with Python C API
- Creates native executable

**Pros:**
- True native compilation
- Better performance than PyInstaller
- Harder to decompile (code protection)
- Can create standalone executables

**Cons:**
- Even more complex configuration than PyInstaller
- C compilation required on build machine
- spaCy complexity remains
- Longer build times
- Platform-specific builds required

**Verdict for CICADA:** ⚠️ More work than PyInstaller, same issues

### 3. PyOxidizer (Rust-based)

**How it works:**
- Uses Rust to bundle Python applications
- Embeds Python interpreter in Rust executable
- Zero-copy module loading from memory

**Pros:**
- Fast startup (loads modules from memory)
- Modern tooling
- Good performance

**Cons:**
- Steeper learning curve
- Complex configuration (TOML-based)
- spaCy challenges persist
- Less mature than PyInstaller
- Requires Rust toolchain for builds

**Verdict for CICADA:** ⚠️ Interesting but immature for complex deps

### 4. Shiv / PEX / zipapp (Python ZIP Apps)

**How it works:**
- Creates self-extracting ZIP file with dependencies
- Unpacks to user's home directory on first run
- Still requires Python on target system

**Pros:**
- ✅ Simpler than full executable bundling
- ✅ Better handling of native dependencies (.so, .dll files)
- ✅ Smaller distribution size
- ✅ Easier to build and maintain
- ✅ Cross-platform (same .pyz works everywhere)

**Cons:**
- ⚠️ Still requires Python on target system
- ⚠️ First run is slower (extracts dependencies)
- ⚠️ Less "out of the box" than true executable

**Verdict for CICADA:** ✅ Better than full bundling, but still requires Python

---

## The spaCy Problem

spaCy is the biggest obstacle to bundling CICADA. It's only used for **keyword extraction** (an experimental feature).

### spaCy Characteristics:
- **Size**: ~100-500MB depending on language models
- **Native dependencies**: Compiled C/Cython extensions
- **Model loading**: Complex data file discovery mechanism
- **Bundling issues**: Extensively documented problems with PyInstaller

### Known Issues with PyInstaller + spaCy:
1. Models fail to load with "Can't find model 'en_core_web_sm'" errors
2. Registry errors for transformer architectures
3. Need to manually extract models to external directories
4. Hidden import configuration is complex and fragile
5. Single-file mode often doesn't work

### Evidence from Research:
Multiple Stack Overflow threads and GitHub issues document these problems:
- [Can't find SpaCy model when packaging with PyInstaller](https://stackoverflow.com/questions/66495437/)
- [Packing spacy console application using Pyinstaller throws error](https://github.com/explosion/spaCy/issues/4683)
- [PyInstaller cannot package application with spaCy](https://github.com/explosion/spaCy/issues/2536)

---

## Alternative Approaches

### Option A: Continue with `uv tool install` (RECOMMENDED)

**Current state:**
- Single command: `uv tool install git+https://github.com/wende/cicada.git@v0.1.1`
- Works on all platforms
- Isolated virtual environment
- Fast and reliable

**Improvements to consider:**
1. Create install script that auto-installs uv if missing
2. Provide platform-specific one-liners for complete setup
3. Add shell completion scripts
4. Create brew formula (for macOS)
5. Package for apt/yum (for Linux distros)

**Example improved install script:**
```bash
# One-command install (installs uv if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh && \
  uv tool install git+https://github.com/wende/cicada.git@v0.1.1
```

### Option B: Make spaCy Optional

**Approach:**
- Move spaCy to optional dependency
- Only import/use if user explicitly enables keyword extraction
- Reduce core dependencies to the essentials

**Benefits:**
- Makes bundling much more feasible
- Reduces installation size
- Most users don't need keyword extraction

**Changes required:**
```python
# pyproject.toml
[project.optional-dependencies]
keywords = ["spacy>=3.8.7"]

# Code changes
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

def extract_keywords(...):
    if not SPACY_AVAILABLE:
        raise RuntimeError("Install with: pip install 'cicada[keywords]'")
    # ... spacy code
```

### Option C: Hybrid Approach - Core Binary + Optional Features

**Approach:**
1. Bundle core functionality (search, indexing) into executable
2. Keep advanced features (spaCy, PR indexing) as optional installs
3. Detect and use system tools (git, gh) via PATH

**Pros:**
- Reasonable executable size (~50-100MB without spaCy)
- Core features work out-of-box
- Advanced users can install full Python environment

**Cons:**
- More complex to implement and maintain
- Still requires git binary
- User confusion about what's included

---

## Estimated Bundle Sizes

Based on typical bundling results:

| Configuration | Estimated Size | Notes |
|--------------|----------------|-------|
| **Minimal** (no spaCy) | 50-100 MB | Python + tree-sitter + basic deps |
| **Full** (with spaCy + models) | 500-800 MB | spaCy with en_core_web_sm model |
| **Full** (with large models) | 800 MB - 1 GB+ | spaCy with larger language models |

For comparison:
- `uv tool install`: ~150MB (shared Python environment)
- Git: ~50MB
- GitHub CLI: ~30MB

---

## Build Complexity Assessment

Creating bundled executables would require:

### 1. Build Infrastructure
- ❌ CI/CD for 3 platforms (Linux, macOS, Windows)
- ❌ Code signing certificates (especially for macOS)
- ❌ Platform-specific testing
- ❌ Large artifact storage (500MB+ per platform)

### 2. Maintenance Burden
- ❌ Keep PyInstaller specs updated with dependency changes
- ❌ Debug platform-specific bundling issues
- ❌ Handle spaCy model bundling changes
- ❌ Test bundled versions for each release

### 3. User Experience Issues
- ❌ Large download size (500MB+)
- ❌ Still need Git installed
- ❌ Still need GitHub CLI for PR features
- ❌ Platform-specific installers/packages needed
- ❌ No easy updates (must re-download entire bundle)

---

## Recommendations

### Primary Recommendation: ✅ Stick with `uv tool install`

**Rationale:**
1. **Current approach works well**: Single command, fast, reliable
2. **Better than bundled**: Smaller, faster, easier to update
3. **uv is growing**: Increasingly common in Python ecosystem
4. **Avoid complexity**: Bundling adds significant maintenance burden
5. **Dependencies matter**: Git/gh are required anyway

**Enhancements to current approach:**
1. Create convenience install script that installs uv automatically
2. Add shell completion for better UX
3. Create OS-specific packages (brew, apt, chocolatey) that install uv + cicada
4. Improve documentation with platform-specific quickstarts

### Secondary Recommendation: Make spaCy Optional

Even if not bundling, making spaCy optional would:
- Reduce default installation size (~500MB → ~50MB)
- Speed up installation
- Make bundling feasible for future consideration
- Most users don't use keyword extraction

**Implementation:**
```toml
[project.optional-dependencies]
keywords = ["spacy>=3.8.7"]
```

```bash
# Core install (default)
uv tool install git+https://github.com/wende/cicada.git

# With keyword extraction
uv tool install git+https://github.com/wende/cicada.git[keywords]
```

### If You Must Bundle: Use Shiv/PEX

If bundling is absolutely required:
1. Make spaCy optional first
2. Use **shiv** or **PEX** to create .pyz bundle
3. Document that Python 3.10+ is required
4. Provide per-platform installation guides

**Pros:**
- Easier than PyInstaller
- Better handling of native dependencies
- Single .pyz file works cross-platform
- Much smaller than full executable

**Cons:**
- Still requires Python on system
- Less "magical" than true executable

---

## Conclusion

**Should CICADA be bundled into a single executable?**

**Answer: NO** ❌

**Why:**
1. Current `uv tool install` approach is superior in almost every way
2. spaCy creates insurmountable practical challenges
3. Still requires external tools (git, gh)
4. Massive maintenance burden for questionable benefit
5. Results in 500MB+ executables that are hard to distribute

**Better alternatives:**
1. **Improve current install UX** with auto-installing script
2. **Make spaCy optional** to reduce default install size
3. **Create OS packages** (brew, apt) that handle uv installation
4. **Better documentation** for non-Python users

**Only consider bundling if:**
- spaCy is removed or made truly optional
- You accept 50-100MB executable size
- You have resources for multi-platform CI/CD
- You're willing to maintain bundling infrastructure

**The real problem isn't bundling - it's installation UX.** Fix that with better scripts and documentation, not bundling.

---

## Next Steps (If Proceeding)

If you decide to pursue bundling despite the recommendation:

### Phase 1: Make it Feasible
1. Make spaCy optional (move to extras)
2. Test core functionality without spaCy
3. Ensure all features work with lazy imports

### Phase 2: Proof of Concept
1. Create PyInstaller spec file
2. Test bundling on one platform (Linux)
3. Measure actual bundle size
4. Test all core features in bundled version

### Phase 3: Multi-Platform
1. Set up CI/CD for Linux, macOS, Windows
2. Handle platform-specific issues
3. Create installers/packages for each platform
4. Document installation per platform

### Phase 4: Maintenance
1. Update bundling on each release
2. Monitor for bundling issues
3. Keep PyInstaller configuration updated
4. Handle user reports of bundled version issues

**Estimated effort**: 2-4 weeks initial + ongoing maintenance

---

## References

### Research Sources
- [PyInstaller Documentation](https://pyinstaller.readthedocs.io/)
- [PyOxidizer Comparisons](https://pyoxidizer.readthedocs.io/en/stable/pyoxidizer_comparisons.html)
- [LinkedIn's Shiv](https://engineering.linkedin.com/blog/2018/05/introducing-and-open-sourcing-shiv)
- [Python zipapp](https://docs.python.org/3/library/zipapp.html)
- [The tree-sitter packaging mess](https://ayats.org/blog/tree-sitter-packaging)
- [spaCy + PyInstaller issues](https://github.com/explosion/spaCy/issues?q=pyinstaller)
- [uv tool install feature discussion](https://github.com/astral-sh/uv/issues/5802)

### Tools Evaluated
- **PyInstaller**: https://pyinstaller.org/
- **Nuitka**: https://nuitka.net/
- **PyOxidizer**: https://github.com/indygreg/PyOxidizer
- **Shiv**: https://github.com/linkedin/shiv
- **PEX**: https://github.com/pantsbuild/pex
- **uv**: https://github.com/astral-sh/uv
