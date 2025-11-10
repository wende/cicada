"""
Tests for dependency extraction integration in the indexer.
"""

import json
from pathlib import Path

import pytest


@pytest.fixture
def sample_elixir_file(tmp_path):
    """Create a sample Elixir file for testing."""
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()
    user_file = lib_dir / "user.ex"
    user_file.write_text(
        """defmodule MyApp.User do
  alias MyApp.Repo
  alias MyApp.Auth

  use Ecto.Schema
  import Ecto.Changeset

  def create_user(name, email) do
    attrs = %{name: name, email: email}
    validate_attrs(attrs)
    hash = Auth.hash_password("password")
    Repo.insert(attrs)
  end

  defp validate_attrs(attrs) do
    # validation logic
    attrs
  end
end
"""
    )
    return tmp_path


class TestIndexerDependencyExtraction:
    """Test dependency extraction in the indexer."""

    def test_extract_dependencies_helper(self, sample_elixir_file):
        """Test the _extract_dependencies helper method."""
        from cicada.indexer import ElixirIndexer

        indexer = ElixirIndexer(verbose=False)

        # Simulate parsed module data
        module_data = {
            "module": "MyApp.User",
            "aliases": {"Repo": "MyApp.Repo", "Auth": "MyApp.Auth"},
            "imports": ["Ecto.Changeset"],
            "uses": ["Ecto.Schema"],
            "requires": [],
            "behaviours": [],
            "calls": [
                {"module": None, "function": "validate_attrs", "arity": 1, "line": 10},
                {"module": "Auth", "function": "hash_password", "arity": 1, "line": 11},
                {"module": "Repo", "function": "insert", "arity": 1, "line": 12},
            ],
        }

        functions = [
            {"name": "create_user", "arity": 2, "line": 8},
            {"name": "validate_attrs", "arity": 1, "line": 15},
        ]

        # Call the helper
        module_deps, updated_functions = indexer._extract_dependencies(module_data, functions)

        # Check module dependencies
        assert "dependencies" not in module_data  # Original not modified
        assert "modules" in module_deps
        assert "MyApp.Repo" in module_deps["modules"]
        assert "MyApp.Auth" in module_deps["modules"]
        assert "Ecto.Schema" in module_deps["modules"]
        assert "Ecto.Changeset" in module_deps["modules"]

        # Check function dependencies were added
        assert "dependencies" in updated_functions[0]
        assert "dependencies" in updated_functions[1]

        # Check create_user dependencies
        create_user_deps = updated_functions[0]["dependencies"]
        assert len(create_user_deps) == 3
        assert any(d["function"] == "validate_attrs" for d in create_user_deps)
        assert any(d["function"] == "hash_password" for d in create_user_deps)
        assert any(d["function"] == "insert" for d in create_user_deps)

        # Check module names are resolved
        hash_dep = next(d for d in create_user_deps if d["function"] == "hash_password")
        assert hash_dep["module"] == "MyApp.Auth"  # Resolved from alias

        insert_dep = next(d for d in create_user_deps if d["function"] == "insert")
        assert insert_dep["module"] == "MyApp.Repo"  # Resolved from alias

    def test_index_repository_includes_dependencies(self, sample_elixir_file):
        """Test that index_repository includes dependency information."""
        from cicada.indexer import ElixirIndexer

        indexer = ElixirIndexer(verbose=False)
        output_path = sample_elixir_file / ".cicada" / "index.json"

        # Index the repository
        index = indexer.index_repository(
            str(sample_elixir_file), str(output_path), extract_keywords=False
        )

        # Check that dependencies are in the index
        assert "MyApp.User" in index["modules"]
        user_module = index["modules"]["MyApp.User"]

        # Check module-level dependencies
        assert "dependencies" in user_module
        assert "modules" in user_module["dependencies"]
        assert "MyApp.Repo" in user_module["dependencies"]["modules"]
        assert "MyApp.Auth" in user_module["dependencies"]["modules"]

        # Check function-level dependencies
        create_user_func = next(f for f in user_module["functions"] if f["name"] == "create_user")
        assert "dependencies" in create_user_func
        assert len(create_user_func["dependencies"]) > 0

    def test_incremental_index_includes_dependencies(self, sample_elixir_file):
        """Test that incremental indexing includes dependency information."""
        from cicada.indexer import ElixirIndexer

        indexer = ElixirIndexer(verbose=False)
        output_path = sample_elixir_file / ".cicada" / "index.json"

        # Do initial index
        indexer.index_repository(str(sample_elixir_file), str(output_path), extract_keywords=False)

        # Modify the file
        user_file = sample_elixir_file / "lib" / "user.ex"
        content = user_file.read_text()
        content += "\n  # Comment added\n"
        user_file.write_text(content)

        # Do incremental index
        index = indexer.incremental_index_repository(
            str(sample_elixir_file), str(output_path), extract_keywords=False
        )

        # Check that dependencies are still in the index
        assert "MyApp.User" in index["modules"]
        user_module = index["modules"]["MyApp.User"]

        # Check module-level dependencies
        assert "dependencies" in user_module
        assert "modules" in user_module["dependencies"]
        assert "MyApp.Repo" in user_module["dependencies"]["modules"]

        # Check function-level dependencies
        create_user_func = next(f for f in user_module["functions"] if f["name"] == "create_user")
        assert "dependencies" in create_user_func

    def test_function_dependencies_line_range(self, sample_elixir_file):
        """Test that function dependencies are correctly filtered by line range."""
        from cicada.indexer import ElixirIndexer

        indexer = ElixirIndexer(verbose=False)

        # Create module with multiple functions
        module_data = {
            "module": "MyApp.User",
            "aliases": {"Repo": "MyApp.Repo"},
            "calls": [
                {"module": "Repo", "function": "get", "arity": 2, "line": 5},  # In first func
                {"module": "Repo", "function": "insert", "arity": 1, "line": 10},  # In second func
                {"module": "Repo", "function": "update", "arity": 2, "line": 15},  # In third func
            ],
        }

        functions = [
            {"name": "get_user", "arity": 1, "line": 4},
            {"name": "create_user", "arity": 1, "line": 9},
            {"name": "update_user", "arity": 2, "line": 14},
        ]

        # Extract dependencies
        module_deps, updated_functions = indexer._extract_dependencies(module_data, functions)

        # Check first function only has get call
        assert len(updated_functions[0]["dependencies"]) == 1
        assert updated_functions[0]["dependencies"][0]["function"] == "get"

        # Check second function only has insert call
        assert len(updated_functions[1]["dependencies"]) == 1
        assert updated_functions[1]["dependencies"][0]["function"] == "insert"

        # Check third function only has update call
        assert len(updated_functions[2]["dependencies"]) == 1
        assert updated_functions[2]["dependencies"][0]["function"] == "update"

    def test_empty_dependencies(self, sample_elixir_file):
        """Test handling of modules/functions with no dependencies."""
        from cicada.indexer import ElixirIndexer

        indexer = ElixirIndexer(verbose=False)

        module_data = {
            "module": "MyApp.Empty",
            "aliases": {},
            "imports": [],
            "uses": [],
            "calls": [],
        }

        functions = [{"name": "simple_func", "arity": 0, "line": 5}]

        # Extract dependencies
        module_deps, updated_functions = indexer._extract_dependencies(module_data, functions)

        # Should have empty lists, not crash
        assert module_deps["modules"] == []
        assert updated_functions[0]["dependencies"] == []

    def test_alias_resolution_in_dependencies(self, sample_elixir_file):
        """Test that aliases are properly resolved in dependencies."""
        from cicada.indexer import ElixirIndexer

        indexer = ElixirIndexer(verbose=False)

        module_data = {
            "module": "MyApp.User",
            "aliases": {
                "R": "MyApp.Repo",
                "A": "MyApp.Auth",
            },
            "calls": [
                {"module": "R", "function": "get", "arity": 2, "line": 5},
                {"module": "A", "function": "hash", "arity": 1, "line": 6},
            ],
        }

        functions = [{"name": "test_func", "arity": 0, "line": 4}]

        # Extract dependencies
        module_deps, updated_functions = indexer._extract_dependencies(module_data, functions)

        # Check that short aliases are resolved to full names
        assert "MyApp.Repo" in module_deps["modules"]
        assert "MyApp.Auth" in module_deps["modules"]
        assert "R" not in module_deps["modules"]
        assert "A" not in module_deps["modules"]

        # Check in function dependencies too
        func_deps = updated_functions[0]["dependencies"]
        assert any(d["module"] == "MyApp.Repo" for d in func_deps)
        assert any(d["module"] == "MyApp.Auth" for d in func_deps)
