# Acceptance Tests

Manual scripts for testing Cicada MCP server functionality.

## Running with Pytest (Recommended)

The acceptance tests are integrated with pytest for automated testing and coverage tracking:

```bash
# Run all acceptance tests
pytest tests/test_acceptance.py -v

# Run with coverage
pytest tests/test_acceptance.py --cov=cicada --cov-report=term-missing
```

## Running Shell Scripts Manually

For manual testing or debugging, you can run the shell scripts directly.

### Setup

Activate the virtual environment before running scripts:

```bash
# Using uv (recommended)
uv sync

# Or traditional venv (legacy)
source venv/bin/activate
```

## search_module.sh

Search for module documentation.

```bash
./tests/acceptance/search_module.sh AB.Generators
```

## search_function.sh

Search for function documentation with optional usage examples.

```bash
# Basic search
./tests/acceptance/search_function.sh add_numbers/2

# With examples from code
./tests/acceptance/search_function.sh AB.Generators.create_input_generator --examples

# Examples from tests only, limit to 10
./tests/acceptance/search_function.sh AB.Generators.create_input_generator -te -n 10
```

## check_moduledoc.sh

Test that moduledoc is displayed when searching for modules.

```bash
./tests/acceptance/check_moduledoc.sh AB.Generators
```

## check_functiondoc.sh

Test that function @doc and examples are properly displayed.

```bash
./tests/acceptance/check_functiondoc.sh resolve_all_types
```

## doc_examples.sh

Legacy script - same as check_functiondoc.sh.

```bash
./tests/acceptance/doc_examples.sh resolve_all_types
```

## test_function_history.sh

Test git history tracking for functions. Tracks functions even as they move within files.

```bash
# Track a function across file (even as it moves)
./tests/acceptance/test_function_history.sh cicada/git_helper.py get_pr_info

# With evolution metadata (creation date, last modified, frequency)
./tests/acceptance/test_function_history.sh cicada/git_helper.py get_pr_info --evolution

# Limit number of commits
./tests/acceptance/test_function_history.sh cicada/git_helper.py get_pr_info -n 3

# Line-based tracking mode (tracks specific line range)
./tests/acceptance/test_function_history.sh cicada/git_helper.py --line-mode --start 40 --end 80

# Line tracking with evolution
./tests/acceptance/test_function_history.sh README.md --line-mode --start 1 --end 50 --evolution
```

**Note:** Requires `.gitattributes` with `*.ex diff=elixir` (automatically created by `cicada`)

## search_by_keywords.sh

Test keyword-based semantic search for modules and functions.

```bash
# Search by multiple keywords
./tests/acceptance/search_by_keywords.sh performance benchmark test

# Search by single keyword
./tests/acceptance/search_by_keywords.sh validation

# Search for type-related code
./tests/acceptance/search_by_keywords.sh type spec function
```

**Prerequisites:**
1. Build index with keyword extraction:
   ```bash
   uv run python -m cicada.indexer tests/fixtures/elixir_project --extract-keywords
   ```
2. Create config file (if not exists):
   ```bash
   mkdir -p tests/fixtures/elixir_project/.cicada
   cat > tests/fixtures/elixir_project/.cicada/config.yaml << EOF
   repository:
     path: tests/fixtures/elixir_project
   storage:
     index_path: tests/fixtures/elixir_project/.cicada/index.json
   EOF
   ```

Returns up to 10 results sorted by confidence score, showing:
- Module or function name with location
- Confidence percentage (matched keywords / total query keywords)
- Matched keywords
- Documentation snippet

## test_keyword_extraction.sh

Test keyword extraction with different spaCy model sizes (small, medium, large).

```bash
# Test with default small model
./tests/acceptance/test_keyword_extraction.sh

# Test with medium model
./tests/acceptance/test_keyword_extraction.sh --medium

# Test with multiple models
./tests/acceptance/test_keyword_extraction.sh --small --medium --large

# Test with custom text
./tests/acceptance/test_keyword_extraction.sh --small "Your custom text here"
```

**Options:**
- `--small`: Use small model (en_core_web_sm) - default if no flags specified
- `--medium`: Use medium model (en_core_web_md)
- `--large`: Use large model (en_core_web_lg)

The script extracts and displays:
- Top keywords with occurrence counts
- Nouns, verbs, and adjectives
- Code identifiers (camelCase, snake_case, PascalCase)
- Named entities
- Text statistics (tokens, sentences)

**Note:** Models will be automatically downloaded if not present. Larger models provide better accuracy but are slower and use more memory.

## Pytest vs Shell Scripts

- **Pytest tests** (`tests/test_acceptance.py`): Automated tests that run in CI/CD and track code coverage. Use these for regular testing and development.
- **Shell scripts**: Manual testing tools useful for quick debugging and experimentation. They invoke the same Python code as the pytest tests.

The pytest tests mirror the functionality of the shell scripts but are integrated into the test suite for better maintainability and coverage tracking.
