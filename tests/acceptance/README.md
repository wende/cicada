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

## Pytest vs Shell Scripts

- **Pytest tests** (`tests/test_acceptance.py`): Automated tests that run in CI/CD and track code coverage. Use these for regular testing and development.
- **Shell scripts**: Manual testing tools useful for quick debugging and experimentation. They invoke the same Python code as the pytest tests.

The pytest tests mirror the functionality of the shell scripts but are integrated into the test suite for better maintainability and coverage tracking.
