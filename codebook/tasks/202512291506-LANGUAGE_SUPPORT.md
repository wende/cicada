---
reviewed:
- cicada/languages/__init__.py:55333356461a69e7a26dffdfd6b95930f72ce161
- cicada/languages/base.py:55333356461a69e7a26dffdfd6b95930f72ce161
- cicada/parsing/language_config.py:55333356461a69e7a26dffdfd6b95930f72ce161
- cicada/languages/scip/configs.py:55333356461a69e7a26dffdfd6b95930f72ce161
- cicada/languages/scip/configurable_indexer.py:55333356461a69e7a26dffdfd6b95930f72ce161
- cicada/languages/scip/indexer.py:55333356461a69e7a26dffdfd6b95930f72ce161
- cicada/languages/python/indexer.py:55333356461a69e7a26dffdfd6b95930f72ce161
- cicada/languages/typescript/indexer.py:55333356461a69e7a26dffdfd6b95930f72ce161
- cicada/languages/elixir/parser.py:55333356461a69e7a26dffdfd6b95930f72ce161
- cicada/languages/erlang/parser.py:55333356461a69e7a26dffdfd6b95930f72ce161
- cicada/languages/rust/indexer.py:55333356461a69e7a26dffdfd6b95930f72ce161
- cicada/languages/go/indexer.py:55333356461a69e7a26dffdfd6b95930f72ce161
- cicada/languages/jvm/indexer.py:55333356461a69e7a26dffdfd6b95930f72ce161
- cicada/languages/clang/indexer.py:55333356461a69e7a26dffdfd6b95930f72ce161
- cicada/languages/ruby/indexer.py:55333356461a69e7a26dffdfd6b95930f72ce161
- cicada/languages/dotnet/indexer.py:55333356461a69e7a26dffdfd6b95930f72ce161
- cicada/languages/dart/indexer.py:55333356461a69e7a26dffdfd6b95930f72ce161
---
This file is a diff of a feature specification. I want you to change the code to match the new spec.

# Language Support

<diff file="codebook/LANGUAGE_SUPPORT.md">
```diff
diff --git a/codebook/LANGUAGE_SUPPORT.md b/codebook/LANGUAGE_SUPPORT.md
new file mode 100644
index 0000000..6473eb0
--- /dev/null
+++ b/codebook/LANGUAGE_SUPPORT.md
@@ -0,0 +1,559 @@
+# Language Support
+
+Cicada provides code intelligence for 14 programming languages through two implementation approaches: tree-sitter AST parsing for deep language support, and SCIP (Source Code Intelligence Protocol) for broad language coverage.
+
+## Overview
+
+Languages are sorted by feature completeness (most complete first).
+
+| Language | Approach | Docs | Strings | Comments | External Tool |
+|----------|----------|------|---------|----------|---------------|
+| **Elixir** | Tree-sitter | Yes | Yes | Yes | - |
+| **Python** | SCIP | Yes | Yes | No | scip-python (auto-install) |
+| **Erlang** | Tree-sitter | Yes | Partial | No | - |
+| **TypeScript** | SCIP | Yes | No | No | scip-typescript (via npx) |
+| **JavaScript** | SCIP | Yes | No | No | scip-typescript (via npx) |
+| **Rust** | SCIP | Yes | No | No | rust-analyzer |
+| **Go** | SCIP | Yes | No | No | scip-go |
+| **Java** | SCIP | Yes | No | No | scip-java / coursier |
+| **Scala** | SCIP | Yes | No | No | scip-java / coursier |
+| **C#** | SCIP | Yes | No | No | scip-dotnet |
+| **Visual Basic** | SCIP | Yes | No | No | scip-dotnet |
+| **Dart** | SCIP | Yes | No | No | scip_dart |
+| **C** | SCIP | Partial | No | No | scip-clang |
+| **C++** | SCIP | Partial | No | No | scip-clang |
+| **Ruby** | SCIP | ? | No | No | scip-ruby |
+
+**Legend:**
+- **Docs**: Extracts documentation (@doc, docstrings, JSDoc, Javadoc, etc.)
+- **Strings**: Extracts keywords from string literals (SQL queries, error messages, etc.)
+- **Comments**: Extracts keywords from inline comments
+- **?**: Untested / unknown
+
+## Architecture
+
+```
+┌─────────────────────────────────────────────────────────────────────┐
+│                       LanguageRegistry                               │
+│                    (cicada/languages/__init__.py)                    │
+├─────────────────────────────────────────────────────────────────────┤
+│                                                                      │
+│  register_language(language, parser, indexer, config, formatter)    │
+│  get_indexer(language) → BaseIndexer                                │
+│  get_parser(language) → BaseParser                                  │
+│  get_formatter(language) → BaseLanguageFormatter                    │
+│  get_supported_languages() → ['elixir', 'python', ...]              │
+│                                                                      │
+├─────────────────────────────────────────────────────────────────────┤
+│                                                                      │
+│  ┌─────────────────────┐       ┌─────────────────────────────────┐  │
+│  │   Tree-sitter       │       │          SCIP-based             │  │
+│  │   Languages         │       │          Languages              │  │
+│  ├─────────────────────┤       ├─────────────────────────────────┤  │
+│  │ • ElixirParser      │       │ • PythonSCIPIndexer             │  │
+│  │ • ElixirIndexer     │       │ • TypeScriptSCIPIndexer         │  │
+│  │ • ErlangParser      │       │ • RustSCIPIndexer               │  │
+│  │ • ErlangIndexer     │       │ • ConfigurableSCIPIndexer       │  │
+│  │                     │       │   (Go, Java, Scala, C, C++,     │  │
+│  │ Always available    │       │    Ruby, C#, VB, Dart)          │  │
+│  └─────────────────────┘       │                                 │  │
+│                                │ Requires cicada_scip package    │  │
+│                                └─────────────────────────────────┘  │
+│                                                                      │
+└─────────────────────────────────────────────────────────────────────┘
+```
+
+### Key Components
+
+| Component | Location | Description |
+|-----------|----------|-------------|
+| `LanguageRegistry` | `cicada/languages/__init__.py:16` | Factory for language-specific parsers and indexers |
+| `BaseParser` | `cicada/parsing/base_parser.py` | Abstract interface for tree-sitter parsers |
+| `BaseIndexer` | `cicada/parsing/base_indexer.py` | Abstract indexer with enrichment pipeline |
+| `LanguageConfig` | `cicada/parsing/language_config.py` | Language-specific configuration (extensions, excludes) |
+| `GenericSCIPIndexer` | `cicada/languages/scip/indexer.py` | Base class for SCIP-based indexers |
+| `ConfigurableSCIPIndexer` | `cicada/languages/scip/configurable_indexer.py` | Config-driven SCIP indexer |
+| `SCIPLanguageConfig` | `cicada/languages/scip/configs.py` | SCIP tool configuration per language |
+
+---
+
+## Tree-sitter Languages
+
+Tree-sitter languages use native AST parsing for deep code understanding. These are always available without external dependencies.
+
+### Elixir
+
+**File:** `cicada/languages/elixir/parser.py`
+
+Elixir has the most comprehensive support with full AST extraction:
+
+| Feature | Support |
+|---------|---------|
+| Module definitions | Full |
+| Function signatures | Full |
+| Type specs (@spec) | Full |
+| Documentation (@doc, @moduledoc) | Full |
+| Dependencies (alias, import, require, use) | Full |
+| Behaviours (@behaviour) | Full |
+| Function calls & call sites | Full |
+| String literals | Full |
+| Inline comments | Full |
+
+**File Extensions:** `.ex`, `.exs`
+
+**Excluded Directories:** `deps`, `_build`, `node_modules`, `.git`, `assets`, `priv`
+
+**Extractors:**
+
+| Extractor | File | Description |
+|-----------|------|-------------|
+| `extract_modules` | `extractors/module.py` | `defmodule` declarations |
+| `extract_functions` | `extractors/function.py` | `def`, `defp`, `test` declarations |
+| `extract_specs` | `extractors/spec.py` | `@spec` type annotations |
+| `extract_docs` | `extractors/doc.py` | `@doc` and `@moduledoc` attributes |
+| `extract_aliases` | `extractors/dependency.py` | `alias` declarations |
+| `extract_imports` | `extractors/dependency.py` | `import` declarations |
+| `extract_requires` | `extractors/dependency.py` | `require` declarations |
+| `extract_uses` | `extractors/dependency.py` | `use` declarations |
+| `extract_behaviours` | `extractors/dependency.py` | `@behaviour` attributes |
+| `extract_function_calls` | `extractors/call.py` | Function call sites |
+| `StringExtractor` | `extractors/string.py` | String literals |
+| `CommentExtractor` | `extractors/comment.py` | Inline comments |
+
+---
+
+### Erlang
+
+**File:** `cicada/languages/erlang/parser.py`
+
+Erlang uses tree-sitter with EDoc comment extraction:
+
+| Feature | Support |
+|---------|---------|
+| Module definitions | Full |
+| Function definitions | Full |
+| Export lists | Full |
+| EDoc documentation | Full |
+| String literals | Partial |
+
+**File Extensions:** `.erl`, `.hrl`
+
+**Excluded Directories:** `_build`, `deps`, `.git`, `node_modules`, `ebin`
+
+**EDoc Format:**
+
+```erlang
+%% @doc Creates a new user.
+%% @param Name The user's name
+%% @returns {ok, User} | {error, Reason}
+create(Name, Email) -> ...
+```
+
+---
+
+## SCIP-based Languages
+
+SCIP (Source Code Intelligence Protocol) languages use external language servers for semantic analysis. They require the `cicada_scip` package and language-specific tools.
+
+### Python
+
+**File:** `cicada/languages/python/indexer.py`
+
+Python uses scip-python (powered by Pyright) for type-aware indexing:
+
+| Feature | Support |
+|---------|---------|
+| Module/file detection | Full |
+| Class definitions | Full |
+| Function/method definitions | Full |
+| Type information | Full (from Pyright) |
+| Docstrings | Full |
+| String literals | Full |
+| Import aliases | Full |
+
+**File Extensions:** `.py`
+
+**Excluded Directories:** `__pycache__`, `.venv`, `venv`, `.git`, `node_modules`, `.pytest_cache`, `.mypy_cache`, `dist`, `build`, `.egg-info`, `.tox`, `.ruff_cache`, `htmlcov`
+
+**External Tool:** `scip-python`
+- Auto-installed via npm if not found
+- Installed to `~/.cicada/node/`
+- Timeout: 10 minutes
+
+**Key Files:**
+
+| File | Description |
+|------|-------------|
+| `cicada/languages/python/indexer.py` | Main Python indexer |
+| `cicada/languages/python/string_extractor.py` | String literal extraction |
+| `cicada/languages/python/alias_extractor.py` | Import alias extraction |
+| `cicada/languages/python/symbol_types.py` | Symbol type detection |
+| `cicada/languages/python/scip_installer.py` | SCIP-python installation |
+
+---
+
+### TypeScript & JavaScript
+
+**File:** `cicada/languages/typescript/indexer.py`
+
+TypeScript and JavaScript share the same indexer using scip-typescript:
+
+| Feature | Support |
+|---------|---------|
+| Module detection | Full |
+| Class definitions | Full |
+| Function definitions | Full |
+| Type information | Full (TypeScript only) |
+| JSDoc comments | Full |
+
+**TypeScript Extensions:** `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`
+
+**JavaScript Extensions:** `.js`, `.jsx`, `.mjs`, `.cjs`
+
+**Excluded Directories:** `node_modules`, `.git`, `dist`, `build`, `coverage`, `.next`, `.nuxt`, `out`, `.cache`
+
+**External Tool:** `@sourcegraph/scip-typescript` (via npx)
+
+**Auto-generated tsconfig.json:**
+
+For JavaScript projects without tsconfig.json, a temporary config is generated:
+
+```json
+{
+  "compilerOptions": {
+    "allowJs": true,
+    "checkJs": false,
+    "noEmit": true,
+    "moduleResolution": "node",
+    "target": "ES2020"
+  },
+  "include": ["**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx"],
+  "exclude": ["node_modules", "dist", "build", ".git"]
+}
+```
+
+---
+
+### Rust
+
+**File:** `cicada/languages/rust/indexer.py`
+
+Rust uses rust-analyzer via SCIP for semantic indexing:
+
+| Feature | Support |
+|---------|---------|
+| Module definitions | Full |
+| Function definitions | Full |
+| Struct/enum/trait definitions | Full |
+| Type information | Full |
+| Documentation comments | Full |
+| String literals | No |
+
+**File Extensions:** `.rs`
+
+**Excluded Directories:** `target`, `.git`, `vendor`, `node_modules`
+
+**External Tool:** `rust-analyzer`
+
+**Key Files:**
+
+| File | Description |
+|------|-------------|
+| `cicada/languages/rust/indexer.py` | Main Rust indexer |
+| `cicada/languages/rust/symbol_types.py` | Symbol type detection |
+
+---
+
+### Go
+
+**File:** `cicada/languages/go/indexer.py`
+
+Go uses scip-go for semantic indexing:
+
+| Feature | Support |
+|---------|---------|
+| Package detection | Full |
+| Function definitions | Full |
+| Type definitions | Full |
+| Documentation comments | Full |
+
+**File Extensions:** `.go`
+
+**Excluded Directories:** `.git`, `node_modules`, `vendor`, `testdata`
+
+**External Tool:** `scip-go`
+
+**Installation:** `go install github.com/sourcegraph/scip-go@latest`
+
+---
+
+### Java & Scala
+
+**File:** `cicada/languages/jvm/indexer.py`
+
+Java and Scala share the same scip-java indexer:
+
+| Feature | Support |
+|---------|---------|
+| Class definitions | Full |
+| Method definitions | Full |
+| Type information | Full |
+| Javadoc/Scaladoc | Full |
+
+**Java Extensions:** `.java`
+
+**Scala Extensions:** `.scala`, `.sc`
+
+**Excluded Directories:** `build`, `target`, `.gradle`, `out`, `bin`, `.idea`, `.bloop`, `.metals`, `project/target`
+
+**External Tool:** `scip-java` or `coursier`
+
+**Installation:** `brew install coursier/formulas/coursier`
+
+**Fallback Commands:**
+1. `scip-java index --output index.scip`
+2. `coursier launch com.sourcegraph:scip-java_2.13:0.11.2 -- index --output index.scip`
+3. `cs launch com.sourcegraph:scip-java_2.13:0.11.2 -- index --output index.scip`
+
+---
+
+### C & C++
+
+**File:** `cicada/languages/clang/indexer.py`
+
+C and C++ use scip-clang for semantic indexing:
+
+| Feature | Support |
+|---------|---------|
+| Function definitions | Full |
+| Class/struct definitions | Full |
+| Header files | Full |
+| Documentation comments | Partial |
+
+**C Extensions:** `.c`, `.h`
+
+**C++ Extensions:** `.cpp`, `.cc`, `.cxx`, `.hpp`, `.hxx`, `.h`
+
+**Excluded Directories:** `build`, `.git`, `node_modules`, `vendor`, `third_party`, `cmake-build-debug`, `cmake-build-release`
+
+**External Tool:** `scip-clang`
+
+**Installation:** https://github.com/nicklockwood/scip-clang
+
+---
+
+### Ruby
+
+**File:** `cicada/languages/ruby/indexer.py`
+
+Ruby uses scip-ruby for semantic indexing:
+
+| Feature | Support |
+|---------|---------|
+| Class definitions | Full |
+| Method definitions | Full |
+| Module definitions | Full |
+
+**File Extensions:** `.rb`, `.rake`
+
+**Excluded Directories:** `vendor`, `.git`, `node_modules`, `tmp`, `log`, `.bundle`
+
+**External Tool:** `scip-ruby`
+
+**Installation:** `gem install scip-ruby`
+
+---
+
+### C# & Visual Basic
+
+**File:** `cicada/languages/dotnet/indexer.py`
+
+C# and Visual Basic use scip-dotnet for .NET semantic indexing:
+
+| Feature | Support |
+|---------|---------|
+| Class definitions | Full |
+| Method definitions | Full |
+| Property definitions | Full |
+| XML documentation | Full |
+
+**C# Extensions:** `.cs`
+
+**VB Extensions:** `.vb`
+
+**Excluded Directories:** `bin`, `obj`, `.git`, `node_modules`, `packages`, `.vs`
+
+**External Tool:** `scip-dotnet`
+
+**Installation:** `dotnet tool install -g scip-dotnet`
+
+---
+
+### Dart
+
+**File:** `cicada/languages/dart/indexer.py`
+
+Dart uses scip_dart for semantic indexing:
+
+| Feature | Support |
+|---------|---------|
+| Class definitions | Full |
+| Function definitions | Full |
+| Type information | Full |
+| Documentation comments | Full |
+
+**File Extensions:** `.dart`
+
+**Excluded Directories:** `build`, `.dart_tool`, `.git`, `node_modules`, `.pub-cache`
+
+**External Tool:** `scip_dart`
+
+**Installation:** `dart pub global activate scip`
+
+**Pre-index Hook:** Automatically runs `dart pub get` if `package_config.json` doesn't exist.
+
+---
+
+## Language Configuration
+
+Each language has a `LanguageConfig` that defines:
+
+```python
+@dataclass
+class LanguageConfig:
+    language: str              # Language identifier
+    file_extensions: list[str] # Extensions to index
+    excluded_dirs: list[str]   # Directories to exclude
+    tree_sitter_grammar: str   # Grammar package (if applicable)
+    comment_syntax: dict       # Comment delimiters
+    parse_options: dict        # Extra parsing config
+```
+
+**Location:** `cicada/parsing/language_config.py`
+
+### Default Configurations
+
+All languages have factory methods for default configuration:
+
+```python
+LanguageConfig.default_elixir()
+LanguageConfig.default_python()
+LanguageConfig.default_typescript()
+LanguageConfig.default_javascript()
+LanguageConfig.default_rust()
+LanguageConfig.default_erlang()
+LanguageConfig.default_go()
+LanguageConfig.default_java()
+LanguageConfig.default_scala()
+LanguageConfig.default_c()
+LanguageConfig.default_cpp()
+LanguageConfig.default_ruby()
+LanguageConfig.default_csharp()
+LanguageConfig.default_vb()
+LanguageConfig.default_dart()
+```
+
+---
+
+## SCIP Language Configuration
+
+SCIP-based languages have additional configuration for external tools:
+
+```python
+@dataclass
+class SCIPLanguageConfig:
+    name: str                              # Language name
+    extensions: list[str]                  # File extensions
+    excluded_dirs: set[str]                # Excluded directories
+    command: list[str]                     # Primary indexer command
+    fallback_commands: list[list[str]]     # Alternative commands
+    required_executables: list[str]        # Required tools
+    install_hint: str                      # Installation instructions
+    pre_index_hook: Callable | None        # Pre-indexing hook
+```
+
+**Location:** `cicada/languages/scip/configs.py`
+
+---
+
+## Adding a New Language
+
+### Tree-sitter Language
+
+1. Create parser in `cicada/languages/{lang}/parser.py`
+2. Create extractors in `cicada/languages/{lang}/extractors/`
+3. Create indexer in `cicada/languages/{lang}/indexer.py`
+4. Add default config to `LanguageConfig`
+5. Register in `cicada/languages/__init__.py`
+
+### SCIP Language
+
+1. Add config to `LANGUAGE_CONFIGS` in `cicada/languages/scip/configs.py`
+2. Create indexer subclass in `cicada/languages/{lang}/indexer.py`
+3. Add default config to `LanguageConfig`
+4. Register in `cicada/languages/__init__.py`
+
+---
+
+## Enrichment Pipeline
+
+All indexers (tree-sitter and SCIP) run through the same enrichment pipeline in `BaseIndexer._run_enrichment_pipeline()`:
+
+1. **Keyword Extraction** - Extract keywords from documentation
+2. **String Keyword Extraction** - Extract keywords from string literals
+3. **Comment Keyword Extraction** - Extract keywords from inline comments
+4. **Timestamp Computation** - Compute git timestamps for functions
+5. **Co-change Analysis** - Analyze git history for co-change patterns
+
+---
+
+## File Reference
+
+### Core Infrastructure
+
+| File | Description |
+|------|-------------|
+| `cicada/languages/__init__.py` | LanguageRegistry and language registration |
+| `cicada/languages/base.py` | Re-exports BaseParser, BaseIndexer, LanguageConfig |
+| `cicada/parsing/base_parser.py` | Abstract base class for parsers |
+| `cicada/parsing/base_indexer.py` | Abstract base class for indexers with enrichment |
+| `cicada/parsing/language_config.py` | LanguageConfig dataclass |
+
+### SCIP Infrastructure
+
+| File | Description |
+|------|-------------|
+| `cicada/languages/scip/__init__.py` | SCIP availability check |
+| `cicada/languages/scip/configs.py` | SCIPLanguageConfig definitions |
+| `cicada/languages/scip/configurable_indexer.py` | Config-driven SCIP indexer |
+| `cicada/languages/scip/indexer.py` | GenericSCIPIndexer base class |
+| `cicada/languages/scip/reader.py` | SCIP file reader |
+| `cicada/languages/scip/converter.py` | SCIP to Cicada format converter |
+
+### Language-Specific
+
+| Language | Parser | Indexer |
+|----------|--------|---------|
+| Elixir | `languages/elixir/parser.py` | `indexer.py` (root) |
+| Erlang | `languages/erlang/parser.py` | `languages/erlang/indexer.py` |
+| Python | - | `languages/python/indexer.py` |
+| TypeScript | - | `languages/typescript/indexer.py` |
+| JavaScript | - | `languages/typescript/indexer.py` |
+| Rust | - | `languages/rust/indexer.py` |
+| Go | - | `languages/go/indexer.py` |
+| Java | - | `languages/jvm/indexer.py` |
+| Scala | - | `languages/jvm/indexer.py` |
+| C | - | `languages/clang/indexer.py` |
+| C++ | - | `languages/clang/indexer.py` |
+| Ruby | - | `languages/ruby/indexer.py` |
+| C# | - | `languages/dotnet/indexer.py` |
+| Visual Basic | - | `languages/dotnet/indexer.py` |
+| Dart | - | `languages/dart/indexer.py` |
+
+---
+
+## Related Features
+
+- **[Automatic Language Detection](../AUTOMATIC_LANGUAGE_DETECTION.md)** - How Cicada detects project language
+- **[AST-Level Indexing](../AST_INDEXING.md)** - How tree-sitter parsing works
+- **[Incremental Indexing](../INCREMENTAL_INDEXING.md)** - Fast re-indexing for all languages
```
</diff>

<diff file="codebook/README.md">
```diff
diff --git a/codebook/README.md b/codebook/README.md
index 95c77e6..341f75a 100644
--- a/codebook/README.md
+++ b/codebook/README.md
@@ -3,20 +3,21 @@
 **CICADA** - Code Intelligence: Contextual Analysis, Discovery, and Attribution
 
 ## Language Support
-1. Elixir Support - Full AST-level indexing with module, function, and macro extraction
-2. Python Support - SCIP-based indexing with class and method detection
-3. Erlang Support - Tree-sitter based parsing with EDoc extraction
-4. TypeScript Support - SCIP-based indexing via TypeScript compiler
-5. JavaScript Support - SCIP-based indexing for JS projects
-6. Rust Support - SCIP-based indexing via rust-analyzer
-7. Go Support - SCIP-based indexing via gopls
-8. Java Support - SCIP-based indexing for JVM projects
-9. Scala Support - SCIP-based indexing via Metals
-10. C/C++ Support - SCIP-based indexing via clangd
-11. Ruby Support - SCIP-based indexing
-12. C# Support - SCIP-based indexing for .NET projects
-13. Visual Basic Support - SCIP-based indexing for .NET projects
-14. Dart Support - SCIP-based indexing
+1. [Language Support](../LANGUAGE_SUPPORT.md) - Comprehensive guide to all 14 supported languages
+2. Elixir Support - Full AST-level indexing with module, function, and macro extraction
+3. Python Support - SCIP-based indexing with class and method detection
+4. Erlang Support - Tree-sitter based parsing with EDoc extraction
+5. TypeScript Support - SCIP-based indexing via TypeScript compiler
+6. JavaScript Support - SCIP-based indexing for JS projects
+7. Rust Support - SCIP-based indexing via rust-analyzer
+8. Go Support - SCIP-based indexing via gopls
+9. Java Support - SCIP-based indexing for JVM projects
+10. Scala Support - SCIP-based indexing via Metals
+11. C/C++ Support - SCIP-based indexing via clangd
+12. Ruby Support - SCIP-based indexing
+13. C# Support - SCIP-based indexing for .NET projects
+14. Visual Basic Support - SCIP-based indexing for .NET projects
+15. Dart Support - SCIP-based indexing
 
 ## Code Indexing
 1. [AST-Level Indexing](../AST_INDEXING.md) - Extracts module, function, and class definitions with signatures and specs
```
</diff>

---
After completing the task, please update the task file with:
- Description of the feature task that was requested
- Short description of the changes that were made and why
Include implemenentation details how the task was implemented.
Do not include code snippets. Only describe the functional changes that were made.
Do not remove diff lines from the task file.
--- FEATURE TASK ---
Create comprehensive documentation for Cicada's multi-language support system. The documentation should cover all 14 supported programming languages, their implementation approaches, external tool requirements, and configuration options.

--- NOTES ---
The language support system has two main implementation approaches:

1. **Tree-sitter languages** (Elixir, Erlang): Use native AST parsing with tree-sitter grammars. These are always available without external dependencies and provide deep code understanding through specialized extractors.

2. **SCIP-based languages** (Python, TypeScript, JavaScript, Rust, Go, Java, Scala, C, C++, Ruby, C#, VB, Dart): Use the Source Code Intelligence Protocol via external language servers. Requires the `cicada_scip` package and language-specific tools.

Key architectural components:
- `LanguageRegistry`: Central factory for parsers and indexers with lazy loading
- `LanguageConfig`: Configuration dataclass for file extensions, excluded directories, and parsing options
- `SCIPLanguageConfig`: SCIP-specific configuration with external tool commands and fallbacks
- `BaseIndexer`: Abstract base with shared enrichment pipeline (keywords, timestamps, co-change)

--- SOLUTION ---
Created `codebook/LANGUAGE_SUPPORT.md` containing:

1. **Overview section** with a table showing all 14 languages, their implementation approach, status, and external tool requirements

2. **Architecture diagram** showing LanguageRegistry as the central factory with tree-sitter and SCIP-based branches

3. **Tree-sitter languages section** covering Elixir (comprehensive support with 12 extractors) and Erlang (with EDoc extraction)

4. **SCIP-based languages section** with detailed coverage of each language including:
   - Feature support tables
   - File extensions
   - Excluded directories
   - External tool requirements and installation commands
   - Key implementation files

5. **Configuration sections** explaining LanguageConfig and SCIPLanguageConfig dataclasses

6. **How to add new languages** guide for both tree-sitter and SCIP approaches

7. **File reference tables** mapping components to their source files

Updated `codebook/README.md` to add a link to the new documentation as the first item in the Language Support section.
