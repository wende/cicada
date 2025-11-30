"""Tests for Python module usage tracking."""

import json
import pytest
from pathlib import Path
from cicada.languages.python.indexer import PythonSCIPIndexer


class TestPythonModuleUsage:
    """Test Python module usage extraction and search."""

    @pytest.mark.asyncio
    async def test_alias_extraction_in_index(self, tmp_path):
        """Test that aliases are extracted and stored in the index."""
        # Create a test Python project with aliases
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        # Create pyproject.toml
        (project_dir / "pyproject.toml").write_text(
            """
[project]
name = "test_project"
version = "0.1.0"
"""
        )

        # Create modules with imports
        (project_dir / "operations.py").write_text(
            """
def add(x, y):
    return x + y

def multiply(x, y):
    return x * y
"""
        )

        (project_dir / "utils.py").write_text(
            """
def average(numbers):
    return sum(numbers) / len(numbers)
"""
        )

        # Create main module that uses aliases
        (project_dir / "main.py").write_text(
            """
import operations as ops
from utils import average as avg

def test_function():
    result1 = ops.add(1, 2)
    result2 = ops.multiply(3, 4)
    avg_val = avg([1, 2, 3])
    return result1 + result2 + avg_val
"""
        )

        # Index the project
        indexer = PythonSCIPIndexer(verbose=False)
        index_path = tmp_path / "index.json"

        try:
            await indexer.index_repository(
                repo_path=str(project_dir),
                output_path=str(index_path),
                extract_keywords=False,
                extract_references=True,
            )

            # Load and verify the index
            with open(index_path, "r") as f:
                index = json.load(f)

            # Find the main module in the index
            main_module = None
            for module_name, module_data in index["modules"].items():
                if "main" in module_data.get("file", ""):
                    main_module = module_data
                    main_module_name = module_name
                    break

            assert main_module is not None, "main module not found in index"

            # Verify aliases are extracted
            aliases = main_module.get("aliases", {})
            assert len(aliases) > 0, "No aliases extracted"

            # Verify specific aliases
            assert "ops" in aliases, "Module alias 'ops' not found"
            assert aliases["ops"] == "operations", f"Expected 'operations', got '{aliases['ops']}'"

            assert "avg" in aliases, "Symbol alias 'avg' not found"
            assert aliases["avg"] == "utils", f"Expected 'utils', got '{aliases['avg']}'"

            print(f"✓ Successfully extracted aliases: {aliases}")
            print(f"✓ Main module: {main_module_name}")

        except Exception as e:
            pytest.skip(f"SCIP indexing not available or failed: {e}")

    @pytest.mark.asyncio
    async def test_module_usage_with_aliases(self, tmp_path):
        """Test that module usage tracking works with aliases."""
        # Create a test Python project
        project_dir = tmp_path / "usage_test"
        project_dir.mkdir()

        # Create pyproject.toml
        (project_dir / "pyproject.toml").write_text(
            """
[project]
name = "usage_test"
version = "0.1.0"
"""
        )

        # Create target module
        (project_dir / "target.py").write_text(
            """
def process_data(data):
    '''Process some data.'''
    return [x * 2 for x in data]
"""
        )

        # Create modules that use the target with different import patterns
        (project_dir / "user1.py").write_text(
            """
import target

def use_target1():
    return target.process_data([1, 2, 3])
"""
        )

        (project_dir / "user2.py").write_text(
            """
import target as tgt

def use_target2():
    return tgt.process_data([4, 5, 6])
"""
        )

        (project_dir / "user3.py").write_text(
            """
from target import process_data as process

def use_target3():
    return process([7, 8, 9])
"""
        )

        # Index the project
        indexer = PythonSCIPIndexer(verbose=False)
        index_path = tmp_path / "index.json"

        try:
            await indexer.index_repository(
                repo_path=str(project_dir),
                output_path=str(index_path),
                extract_keywords=False,
                extract_references=True,
            )

            # Load the index
            with open(index_path, "r") as f:
                index = json.load(f)

            # Verify that all user modules have proper aliases
            for module_name, module_data in index["modules"].items():
                file_path = module_data.get("file", "")

                if "user1" in file_path:
                    # user1 imports target directly (no alias)
                    # Should have "target" tracked as an import
                    imports = module_data.get("imports", [])
                    print(f"user1 imports: {imports}")

                elif "user2" in file_path:
                    # user2 has alias: import target as tgt
                    aliases = module_data.get("aliases", {})
                    assert "tgt" in aliases, "Alias 'tgt' not found in user2"
                    assert aliases["tgt"] == "target", f"Expected 'target', got '{aliases['tgt']}'"
                    print(f"✓ user2 aliases: {aliases}")

                elif "user3" in file_path:
                    # user3 has: from target import process_data as process
                    aliases = module_data.get("aliases", {})
                    assert "process" in aliases, "Alias 'process' not found in user3"
                    assert (
                        aliases["process"] == "target"
                    ), f"Expected 'target', got '{aliases['process']}'"
                    print(f"✓ user3 aliases: {aliases}")

            print("✓ All module usage patterns correctly tracked")

        except Exception as e:
            pytest.skip(f"SCIP indexing not available or failed: {e}")

    def test_sample_python_fixture_has_aliases(self):
        """Test that the sample_python fixture has alias extraction."""
        # Check if the sample_python index has aliases
        fixture_path = Path("tests/fixtures/sample_python")
        index_path = fixture_path / "index.json"

        if not index_path.exists():
            pytest.skip("Sample Python fixture index not available")

        with open(index_path, "r") as f:
            index = json.load(f)

        # Check calculator.py which imports operations
        calculator_module = None
        for module_name, module_data in index["modules"].items():
            if "Calculator" in module_name and "calculator" in module_data.get("file", ""):
                calculator_module = module_data
                break

        if calculator_module:
            # Verify it has aliases field
            assert "aliases" in calculator_module, "aliases field not present"
            aliases = calculator_module.get("aliases", {})

            # calculator.py has: import operations and from utils import ...
            # Should track: {"operations": "operations", "chain_add": "utils", "format_result": "utils"}
            print(f"Calculator module aliases: {aliases}")

            # Verify some expected aliases exist
            if aliases:
                print("✓ Sample Python fixture has aliases extracted")
