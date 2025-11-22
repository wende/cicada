"""
Test that search_function correctly finds call sites for Python functions.

This test reproduces the bug where search_function claims "No call sites found"
despite the index containing call site data in the dependencies array.
"""

import json
import tempfile
from pathlib import Path

import pytest

from cicada.languages.python.indexer import PythonSCIPIndexer
from cicada.mcp.handlers.function_handlers import FunctionSearchHandler


@pytest.mark.skip(
    reason="Requires git repository for scip-python - tested manually with real index"
)
@pytest.mark.asyncio
async def test_search_function_finds_call_sites():
    """
    Test that search_function can find call sites for a Python function.

    This reproduces the bug: index_repository is called in commands.py
    but search_function reports "No call sites found".
    """
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create a simple Python file with a function definition
        math_ops = repo_path / "math_ops.py"
        math_ops.write_text(
            """
def add(a, b):
    \"\"\"Add two numbers.\"\"\"
    return a + b

def subtract(a, b):
    \"\"\"Subtract two numbers.\"\"\"
    return a - b
"""
        )

        # Create another file that calls the add function
        calculator = repo_path / "calculator.py"
        calculator.write_text(
            """
from math_ops import add, subtract

def calculate_total(values):
    \"\"\"Calculate total of values.\"\"\"
    result = 0
    for val in values:
        result = add(result, val)  # Line 7 - call to add
    return result

def calculate_difference(a, b):
    \"\"\"Calculate difference.\"\"\"
    return subtract(a, b)  # Line 12 - call to subtract
"""
        )

        # Index the repository
        indexer = PythonSCIPIndexer(verbose=False)
        index_path = repo_path / "index.json"

        indexer.index_repository(
            repo_path=str(repo_path),
            output_path=str(index_path),
            force=True,
            verbose=False,
        )

        # Load the index
        with open(index_path) as f:
            index = json.load(f)

        # Debug: Check that dependencies are populated
        calculator_module = None
        for module_name, module_data in index["modules"].items():
            if "calculator" in module_data.get("file", ""):
                calculator_module = module_data
                break

        assert calculator_module is not None, "Calculator module not found in index"

        # Check that functions have dependencies
        calculate_total_func = None
        for func in calculator_module["functions"]:
            if func["name"] == "calculate_total":
                calculate_total_func = func
                break

        assert calculate_total_func is not None, "calculate_total function not found"

        print(f"\nDEBUG: calculate_total function data:")
        print(f"  calls: {calculate_total_func.get('calls', [])}")
        print(f"  dependencies: {calculate_total_func.get('dependencies', [])}")

        # Verify the index has the call data
        deps = calculate_total_func.get("dependencies", [])
        add_calls = [d for d in deps if d.get("function") == "add"]
        assert len(add_calls) > 0, "Index should contain calls to 'add' function"

        # Now test search_function
        handler = FunctionSearchHandler(index)

        # Search for the add function and find its call sites
        result = await handler.search_function(
            function_name="add",
            what_calls_it=True,  # Find call sites
        )

        print(f"\nDEBUG: search_function result:")
        print(json.dumps(result, indent=2))

        # The bug: search_function returns no call sites even though they exist
        assert len(result) > 0, "search_function should find the add function"

        function_result = result[0]
        call_sites = function_result.get("call_sites", [])

        # This assertion will FAIL due to the bug
        assert len(call_sites) > 0, (
            f"search_function should find call sites for 'add' function, "
            f"but found {len(call_sites)}. "
            f"Index has {len(add_calls)} calls in dependencies array."
        )


@pytest.mark.skip(reason="Uses real index - tested manually")
@pytest.mark.asyncio
async def test_search_function_finds_call_sites_for_index_repository():
    """
    Test the actual failing case: search for index_repository function.

    This test uses the real cicada codebase index.
    """
    # Load the real index
    index_path = Path.home() / ".cicada/projects/4188ed606a73c0a4/index.json"

    if not index_path.exists():
        pytest.skip("Real index not available")

    with open(index_path) as f:
        index = json.load(f)

    # Verify the index has calls to index_repository
    commands_module = index["modules"].get("_file_commands")
    assert commands_module is not None, "commands module not found"

    # Check that handle_index_main has dependency on index_repository
    handle_index_main = None
    for func in commands_module["functions"]:
        if func["name"] == "handle_index_main":
            handle_index_main = func
            break

    assert handle_index_main is not None
    deps = handle_index_main.get("dependencies", [])
    index_repo_calls = [d for d in deps if d.get("function") == "index_repository"]

    print(f"\nDEBUG: handle_index_main dependencies:")
    print(f"  Total dependencies: {len(deps)}")
    print(f"  Calls to index_repository: {len(index_repo_calls)}")

    assert len(index_repo_calls) > 0, "Index should contain calls to index_repository"

    # Now test search_function
    handler = FunctionSearchHandler(index)

    # Search for BaseIndexer.index_repository
    result = await handler.search_function(
        function_name="BaseIndexer.index_repository",
        what_calls_it=True,
    )

    print(f"\nDEBUG: search_function result for BaseIndexer.index_repository:")
    print(f"  Found {len(result)} results")

    if result:
        function_result = result[0]
        call_sites = function_result.get("call_sites", [])
        print(f"  Call sites: {len(call_sites)}")

        # This assertion will FAIL due to the bug
        assert len(call_sites) > 0, (
            "search_function should find call sites for index_repository "
            f"but found {len(call_sites)}"
        )
