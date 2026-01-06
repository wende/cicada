---
reviewed:
- cicada/setup.py:8dcb4ac6c7ac1aab50d9dcf8e15a91bd935ea4d3
- cicada/languages/__init__.py:8dcb4ac6c7ac1aab50d9dcf8e15a91bd935ea4d3
- cicada/interactive_setup_helpers.py:8dcb4ac6c7ac1aab50d9dcf8e15a91bd935ea4d3
- cicada/parsing/language_config.py:8dcb4ac6c7ac1aab50d9dcf8e15a91bd935ea4d3
---
This file is a diff of a feature specification. I want you to change the code to match the new spec.

# Automatic Language Detection

<diff file="codebook/AUTOMATIC_LANGUAGE_DETECTION.md">
```diff
diff --git a/codebook/AUTOMATIC_LANGUAGE_DETECTION.md b/codebook/AUTOMATIC_LANGUAGE_DETECTION.md
new file mode 100644
index 0000000..134153b
--- /dev/null
+++ b/codebook/AUTOMATIC_LANGUAGE_DETECTION.md
@@ -0,0 +1,224 @@
+# Automatic Language Detection
+
+Cicada automatically detects the programming language of your project by scanning for marker files in the repository root. This eliminates manual configuration and enables seamless indexing of multi-language codebases.
+
+## Overview
+
+When you run `cicada install` or `cicada index`, Cicada examines your repository for language-specific marker files like `mix.exs`, `pyproject.toml`, or `Cargo.toml`. Based on these markers, it selects the appropriate parser and indexer for your project's language.
+
+## Supported Languages and Markers
+
+| Language | Marker Files | Priority |
+|----------|--------------|----------|
+| **Python** | `pyproject.toml`, `setup.py`, `requirements.txt`, `Pipfile`, `poetry.lock` | 1 (highest) |
+| **Elixir** | `mix.exs` | 2 |
+| **Rust** | `Cargo.toml` | 3 |
+| **Erlang** | `rebar.config`, `rebar.lock`, `erlang.mk`, or `*.erl` files in `src/` | 4 |
+| **TypeScript** | `tsconfig.json` | 5 |
+| **JavaScript** | `package.json` (without `tsconfig.json`) | 6 |
+| **Go** | `go.mod` | 7 |
+| **Scala** | `build.sbt` | 8 |
+| **Java** | `build.gradle`, `build.gradle.kts`, `pom.xml` | 9 |
+| **C++** | `CMakeLists.txt`, `Makefile`, `compile_commands.json` (with `*.cpp`/`*.cc` files) | 10 |
+| **C** | `CMakeLists.txt`, `Makefile`, `compile_commands.json` (with `*.c` files) | 11 |
+| **Ruby** | `Gemfile` | 12 |
+| **C#** | `*.sln`, `*.csproj` | 13 |
+| **Visual Basic** | `*.vbproj` | 14 |
+| **Dart** | `pubspec.yaml` | 15 |
+
+## Architecture
+
+```
+┌─────────────────────────────────────────────────────────────────┐
+│                  Language Detection Flow                         │
+├─────────────────────────────────────────────────────────────────┤
+│                                                                  │
+│  1. detect_project_language(repo_path)                          │
+│                         │                                        │
+│                         ▼                                        │
+│  2. Check Python markers (pyproject.toml, setup.py, ...)        │
+│         Found? → return "python"                                 │
+│                         │                                        │
+│                         ▼                                        │
+│  3. Check Elixir marker (mix.exs)                               │
+│         Found? → return "elixir"                                 │
+│                         │                                        │
+│                         ▼                                        │
+│  4. Check other language markers...                             │
+│                         │                                        │
+│                         ▼                                        │
+│  5. No markers found → raise ValueError                         │
+│                                                                  │
+└─────────────────────────────────────────────────────────────────┘
+                          │
+                          ▼
+┌─────────────────────────────────────────────────────────────────┐
+│                    LanguageRegistry                              │
+├─────────────────────────────────────────────────────────────────┤
+│                                                                  │
+│  LanguageRegistry.get_indexer(language)                         │
+│         │                                                        │
+│         ├─→ "elixir" → ElixirIndexer (tree-sitter)              │
+│         ├─→ "python" → PythonSCIPIndexer (SCIP/Pyright)         │
+│         ├─→ "rust"   → RustSCIPIndexer (rust-analyzer)          │
+│         ├─→ "go"     → GoSCIPIndexer (gopls)                    │
+│         └─→ ...                                                  │
+│                                                                  │
+└─────────────────────────────────────────────────────────────────┘
+```
+
+### Key Components
+
+| Component | Location | Description |
+|-----------|----------|-------------|
+| `detect_project_language` | `cicada/setup.py:29` | Scans repo for marker files and returns language name |
+| `LanguageRegistry` | `cicada/languages/__init__.py:16` | Factory for language-specific parsers and indexers |
+| `LanguageRegistry.get_indexer` | `cicada/languages/__init__.py:109` | Returns appropriate indexer for detected language |
+| `LanguageRegistry.register_language` | `cicada/languages/__init__.py:34` | Registers new language implementations |
+| `UnsupportedProjectError` | `cicada/interactive_setup_helpers.py:12` | Exception for unrecognized project types |
+
+---
+
+## Detection Algorithm
+
+The `detect_project_language` function checks markers in priority order:
+
+```python
+def detect_project_language(repo_path: Path) -> str:
+    # Python markers (checked first - highest priority)
+    python_markers = ["pyproject.toml", "setup.py", "requirements.txt", 
+                      "Pipfile", "poetry.lock"]
+    for marker in python_markers:
+        if (repo_path / marker).exists():
+            return "python"
+
+    # Elixir marker
+    if (repo_path / "mix.exs").exists():
+        return "elixir"
+
+    # Rust marker
+    if (repo_path / "Cargo.toml").exists():
+        return "rust"
+
+    # ... additional languages checked in order
+
+    # No recognized language
+    raise ValueError("Could not detect project language...")
+```
+
+### Priority Rules
+
+1. **Python takes precedence**: If both `pyproject.toml` and `mix.exs` exist, Python is detected
+2. **TypeScript vs JavaScript**: `tsconfig.json` presence distinguishes TypeScript from JavaScript
+3. **C vs C++**: Presence of `.cpp` or `.cc` files distinguishes C++ from C
+4. **Erlang fallback**: If no `rebar.config`, checks for `*.erl` files in `src/` directory
+
+---
+
+## Language Registry
+
+The `LanguageRegistry` class manages language implementations:
+
+### Registering a Language
+
+Languages are registered at module load time in `cicada/languages/__init__.py`:
+
+```python
+LanguageRegistry.register_language(
+    language="elixir",
+    parser_class="cicada.languages.elixir.parser.ElixirParser",
+    indexer_class="cicada.indexer.ElixirIndexer",
+    config=LanguageConfig.default_elixir(),
+    formatter_class="cicada.languages.elixir.formatter.ElixirFormatter",
+)
+```
+
+### Getting an Indexer
+
+```python
+from cicada.languages import LanguageRegistry
+
+# Get indexer for detected language
+indexer = LanguageRegistry.get_indexer("python")
+indexer.incremental_index_repository(repo_path, output_path)
+```
+
+### SCIP-Based Languages
+
+Languages that use SCIP (Source Code Intelligence Protocol) are only registered if the `cicada_scip` package is available. This includes: Python, TypeScript, JavaScript, Rust, Go, Java, Scala, C, C++, Ruby, C#, Visual Basic, and Dart.
+
+---
+
+## Usage
+
+### Automatic Detection During Setup
+
+```bash
+# Cicada automatically detects the language
+cicada install
+
+# Output:
+# ✓ Detected: Python project (pyproject.toml)
+# Indexing repository...
+```
+
+### Checking Supported Languages
+
+```python
+from cicada.languages import LanguageRegistry
+
+# List all supported languages
+languages = LanguageRegistry.get_supported_languages()
+# ['elixir', 'erlang', 'python', 'typescript', ...]
+
+# Check if a language is supported
+is_python_supported = LanguageRegistry.is_language_supported("python")
+```
+
+### Handling Unsupported Projects
+
+```python
+from cicada.setup import detect_project_language
+
+try:
+    language = detect_project_language(repo_path)
+except ValueError as e:
+    print(f"Error: {e}")
+    # "Could not detect project language in /path/to/repo
+    #  Expected one of: Python (pyproject.toml), Elixir (mix.exs), ..."
+```
+
+---
+
+## Error Handling
+
+When no recognized marker file is found, Cicada raises a `ValueError` with a helpful message listing all supported project types:
+
+```
+Could not detect project language in /path/to/repo
+Expected one of: Python (pyproject.toml), Elixir (mix.exs), Rust (Cargo.toml), 
+Erlang (rebar.config), TypeScript/JavaScript (package.json), Go (go.mod), 
+Java (build.gradle/pom.xml), Scala (build.sbt), C/C++ (CMakeLists.txt/Makefile), 
+Ruby (Gemfile), C# (*.csproj), VB (*.vbproj), Dart (pubspec.yaml)
+```
+
+---
+
+## File Reference
+
+| File | Description |
+|------|-------------|
+| `cicada/setup.py` | Contains `detect_project_language` function |
+| `cicada/languages/__init__.py` | LanguageRegistry class and language registration |
+| `cicada/languages/base.py` | BaseParser and BaseIndexer abstract classes |
+| `cicada/interactive_setup_helpers.py` | UnsupportedProjectError exception |
+| `cicada/parsing/language_config.py` | LanguageConfig class for language settings |
+| `tests/languages/python/test_python_support.py` | Tests for language detection |
+
+---
+
+## Related Features
+
+- **[AST-Level Indexing](../AST_INDEXING.md)**: Language-specific parsing after detection
+- **[Incremental Indexing](../INCREMENTAL_INDEXING.md)**: Fast re-indexing for detected language
+- **Editor Integration**: Uses detected language for MCP server configuration
```
</diff>

<diff file="codebook/README.md">
```diff
diff --git a/codebook/README.md b/codebook/README.md
index 062f098..8392516 100644
--- a/codebook/README.md
+++ b/codebook/README.md
@@ -11,7 +11,7 @@
 ## Code Indexing
 1. [AST-Level Indexing](../AST_INDEXING.md) - Extracts module, function, and class definitions with signatures and specs - 
 2. [Incremental Indexing](../INCREMENTAL_INDEXING.md) - Only reindexes changed files for fast updates
-3. Automatic Language Detection - Detects project type from mix.exs or pyproject.toml
+3. [Automatic Language Detection](../AUTOMATIC_LANGUAGE_DETECTION.md) - Detects project type from mix.exs or pyproject.toml
 4. Watch Mode - Automatically reindexes files when changes are detected
 5. Configurable Keyword Tiers - Fast, Regular, or Max tiers for keyword extraction quality
 6. String-Based Indexing - Indexes string literals from function bodies (SQL, error messages, etc.)
```
</diff>

--- FEATURE TASK ---
Document the Automatic Language Detection feature for the Cicada codebook reference documentation. This feature automatically identifies the programming language of a repository by scanning for marker files (like mix.exs, pyproject.toml, Cargo.toml) and selects the appropriate indexer.

--- NOTES ---
The automatic language detection system is a core bootstrapping mechanism in Cicada that enables zero-configuration setup. Key implementation components:

1. **detect_project_language** (`cicada/setup.py:29`): The main detection function that checks for language-specific marker files in priority order. Python markers are checked first, followed by Elixir, Rust, Erlang, TypeScript/JavaScript, Go, Scala, Java, C/C++, Ruby, C#, VB, and Dart.

2. **LanguageRegistry** (`cicada/languages/__init__.py:16`): A factory class that maintains mappings from language names to their parser and indexer implementations. Languages are registered at module load time with lazy class loading.

3. **Priority Rules**: Python takes precedence over other languages. TypeScript vs JavaScript is distinguished by tsconfig.json presence. C vs C++ is determined by source file extensions.

4. **SCIP Integration**: Languages using SCIP (Source Code Intelligence Protocol) are only registered when the cicada_scip package is available, enabling support for 12+ languages.

--- SOLUTION ---
Created comprehensive documentation in `codebook/AUTOMATIC_LANGUAGE_DETECTION.md` covering:

- Feature overview explaining marker-file based detection
- Complete table of 15 supported languages with their marker files and priority
- Architecture diagram showing detection flow and LanguageRegistry integration
- Key components table with file locations and descriptions
- Detection algorithm explanation with priority rules
- LanguageRegistry usage examples (registering languages, getting indexers)
- CLI and programmatic usage examples
- Error handling behavior with helpful error messages
- Complete file reference for implementation files
- Links to related features (AST indexing, Incremental indexing, Editor integration)

Updated `codebook/README.md`:
- Added hyperlink to the new documentation file
- Expanded Language Support section from 4 to 14 languages to reflect full SCIP support