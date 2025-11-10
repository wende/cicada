"""
Tests for MCP dependency analysis tools.
"""

import json
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def mock_server_with_dependencies(tmp_path):
    """Create a mock MCP server with dependency data."""
    from cicada.mcp.server import CicadaServer

    # Create a test index with dependency data
    test_index = {
        "modules": {
            "MyApp.User": {
                "file": "lib/my_app/user.ex",
                "line": 1,
                "functions": [
                    {
                        "name": "create_user",
                        "arity": 2,
                        "type": "def",
                        "line": 10,
                        "dependencies": [
                            {
                                "module": "MyApp.User",
                                "function": "validate_attrs",
                                "arity": 1,
                                "line": 11,
                            },
                            {
                                "module": "MyApp.Repo",
                                "function": "insert",
                                "arity": 1,
                                "line": 12,
                            },
                            {
                                "module": "MyApp.Auth",
                                "function": "hash_password",
                                "arity": 1,
                                "line": 13,
                            },
                        ],
                    },
                    {
                        "name": "validate_attrs",
                        "arity": 1,
                        "type": "defp",
                        "line": 20,
                        "dependencies": [],
                    },
                ],
                "dependencies": {
                    "modules": ["MyApp.Repo", "MyApp.Auth", "Ecto.Schema"],
                    "has_dynamic_calls": False,
                },
                "aliases": {"Repo": "MyApp.Repo", "Auth": "MyApp.Auth"},
            },
            "MyApp.Repo": {
                "file": "lib/my_app/repo.ex",
                "line": 1,
                "functions": [],
                "dependencies": {
                    "modules": ["Ecto.Repo"],
                    "has_dynamic_calls": False,
                },
            },
            "MyApp.Auth": {
                "file": "lib/my_app/auth.ex",
                "line": 1,
                "functions": [],
                "dependencies": {
                    "modules": ["Bcrypt"],
                    "has_dynamic_calls": False,
                },
            },
        },
        "metadata": {
            "indexed_at": "2024-01-01T00:00:00",
            "total_modules": 3,
            "total_functions": 2,
        },
    }

    # Create config file
    config_dir = tmp_path / ".cicada" / "projects" / "test_hash"
    config_dir.mkdir(parents=True)

    index_path = config_dir / "index.json"
    index_path.write_text(json.dumps(test_index))

    config = {
        "repository": {"path": str(tmp_path)},
        "storage": {"index_path": str(index_path)},
    }
    config_path = config_dir / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    # Create server
    server = CicadaServer(config_path=str(config_path))
    server.index = test_index
    return server


class TestGetModuleDependencies:
    """Test get_module_dependencies MCP tool."""

    @pytest.mark.asyncio
    async def test_get_module_dependencies_markdown(self, mock_server_with_dependencies):
        """Test getting module dependencies in markdown format."""
        result = await mock_server_with_dependencies._get_module_dependencies(
            "MyApp.User", "markdown", depth=1
        )

        assert len(result) == 1
        text = result[0].text
        assert "# Dependencies for MyApp.User" in text
        assert "## Direct Dependencies (3)" in text
        assert "- MyApp.Auth" in text
        assert "- MyApp.Repo" in text
        assert "- Ecto.Schema" in text

    @pytest.mark.asyncio
    async def test_get_module_dependencies_json(self, mock_server_with_dependencies):
        """Test getting module dependencies in JSON format."""
        result = await mock_server_with_dependencies._get_module_dependencies(
            "MyApp.User", "json", depth=1
        )

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["module"] == "MyApp.User"
        assert "MyApp.Repo" in data["dependencies"]["direct"]
        assert "MyApp.Auth" in data["dependencies"]["direct"]
        assert "Ecto.Schema" in data["dependencies"]["direct"]
        assert data["dependencies"]["depth"] == 1

    @pytest.mark.asyncio
    async def test_get_module_dependencies_transitive(self, mock_server_with_dependencies):
        """Test getting transitive dependencies."""
        result = await mock_server_with_dependencies._get_module_dependencies(
            "MyApp.User", "markdown", depth=2
        )

        assert len(result) == 1
        text = result[0].text
        assert "# Dependencies for MyApp.User" in text
        assert "## Direct Dependencies (3)" in text
        assert "## Transitive Dependencies" in text
        # Should include Ecto.Repo (from MyApp.Repo) and Bcrypt (from MyApp.Auth)
        assert "Ecto.Repo" in text or "Bcrypt" in text

    @pytest.mark.asyncio
    async def test_get_module_dependencies_not_found(self, mock_server_with_dependencies):
        """Test error handling for non-existent module."""
        result = await mock_server_with_dependencies._get_module_dependencies(
            "MyApp.Users", "markdown", depth=1
        )

        assert len(result) == 1
        text = result[0].text
        assert "Module not found: MyApp.Users" in text
        assert "Did you mean one of these?" in text
        assert "MyApp.User" in text  # Should suggest the similar module

    @pytest.mark.asyncio
    async def test_get_module_dependencies_no_deps(self, mock_server_with_dependencies):
        """Test module with no dependencies."""
        # Add a module with no dependencies
        mock_server_with_dependencies.index["modules"]["MyApp.Empty"] = {
            "file": "lib/my_app/empty.ex",
            "line": 1,
            "functions": [],
            "dependencies": {"modules": [], "has_dynamic_calls": False},
        }

        result = await mock_server_with_dependencies._get_module_dependencies(
            "MyApp.Empty", "markdown", depth=1
        )

        assert len(result) == 1
        text = result[0].text
        assert "# Dependencies for MyApp.Empty" in text
        assert "*No dependencies found*" in text


class TestGetFunctionDependencies:
    """Test get_function_dependencies MCP tool."""

    @pytest.mark.asyncio
    async def test_get_function_dependencies_markdown(self, mock_server_with_dependencies):
        """Test getting function dependencies in markdown format."""
        result = await mock_server_with_dependencies._get_function_dependencies(
            "MyApp.User", "create_user", 2, "markdown", False
        )

        assert len(result) == 1
        text = result[0].text
        assert "# Dependencies for MyApp.User.create_user/2" in text
        assert "## Internal Calls (1)" in text
        assert "- validate_attrs/1 (line 11)" in text
        assert "## External Calls (2)" in text
        assert "- MyApp.Repo.insert/1 (line 12)" in text
        assert "- MyApp.Auth.hash_password/1 (line 13)" in text

    @pytest.mark.asyncio
    async def test_get_function_dependencies_json(self, mock_server_with_dependencies):
        """Test getting function dependencies in JSON format."""
        result = await mock_server_with_dependencies._get_function_dependencies(
            "MyApp.User", "create_user", 2, "json", False
        )

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["module"] == "MyApp.User"
        assert data["function"] == "create_user/2"
        assert len(data["dependencies"]) == 3
        assert any(d["function"] == "validate_attrs" for d in data["dependencies"])
        assert any(d["function"] == "insert" for d in data["dependencies"])
        assert any(d["function"] == "hash_password" for d in data["dependencies"])

    @pytest.mark.asyncio
    async def test_get_function_dependencies_with_context(
        self, mock_server_with_dependencies, tmp_path
    ):
        """Test getting function dependencies with code context."""
        # Create source file with code
        lib_dir = tmp_path / "lib" / "my_app"
        lib_dir.mkdir(parents=True)
        user_file = lib_dir / "user.ex"
        user_file.write_text(
            """defmodule MyApp.User do
  def create_user(name, email) do
    attrs = %{name: name, email: email}
    validate_attrs(attrs)
    hash = Auth.hash_password("password")
    Repo.insert(attrs)
  end

  defp validate_attrs(attrs) do
    # validation logic
  end
end
"""
        )

        # Update config to point to tmp_path
        mock_server_with_dependencies.config["repository"]["path"] = str(tmp_path)

        result = await mock_server_with_dependencies._get_function_dependencies(
            "MyApp.User", "create_user", 2, "markdown", True
        )

        assert len(result) == 1
        text = result[0].text
        assert "# Dependencies for MyApp.User.create_user/2" in text
        # Should include code context
        assert "```elixir" in text

    @pytest.mark.asyncio
    async def test_get_function_dependencies_module_not_found(self, mock_server_with_dependencies):
        """Test error handling for non-existent module."""
        result = await mock_server_with_dependencies._get_function_dependencies(
            "NonExistent.Module", "some_func", 1, "markdown", False
        )

        assert len(result) == 1
        text = result[0].text
        assert "Module not found: NonExistent.Module" in text

    @pytest.mark.asyncio
    async def test_get_function_dependencies_function_not_found(
        self, mock_server_with_dependencies
    ):
        """Test error handling for non-existent function."""
        result = await mock_server_with_dependencies._get_function_dependencies(
            "MyApp.User", "nonexistent_func", 1, "markdown", False
        )

        assert len(result) == 1
        text = result[0].text
        assert "Function not found: MyApp.User.nonexistent_func/1" in text
        assert "Available functions in MyApp.User:" in text
        assert "- create_user/2" in text

    @pytest.mark.asyncio
    async def test_get_function_dependencies_no_deps(self, mock_server_with_dependencies):
        """Test function with no dependencies."""
        result = await mock_server_with_dependencies._get_function_dependencies(
            "MyApp.User", "validate_attrs", 1, "markdown", False
        )

        assert len(result) == 1
        text = result[0].text
        assert "# Dependencies for MyApp.User.validate_attrs/1" in text
        assert "*No dependencies found*" in text


class TestLookupModuleWithError:
    """Test _lookup_module_with_error helper."""

    def test_lookup_module_success(self, mock_server_with_dependencies):
        """Test successful module lookup."""
        module_data, error_msg = mock_server_with_dependencies._lookup_module_with_error(
            "MyApp.User"
        )

        assert module_data is not None
        assert error_msg is None
        assert module_data["file"] == "lib/my_app/user.ex"

    def test_lookup_module_not_found_with_suggestions(self, mock_server_with_dependencies):
        """Test module not found with suggestions."""
        module_data, error_msg = mock_server_with_dependencies._lookup_module_with_error(
            "MyApp.Users", include_suggestions=True
        )

        assert module_data is None
        assert error_msg is not None
        assert "Module not found: MyApp.Users" in error_msg
        assert "Did you mean one of these?" in error_msg
        assert "MyApp.User" in error_msg

    def test_lookup_module_not_found_without_suggestions(self, mock_server_with_dependencies):
        """Test module not found without suggestions."""
        module_data, error_msg = mock_server_with_dependencies._lookup_module_with_error(
            "NonExistent.Module", include_suggestions=False
        )

        assert module_data is None
        assert error_msg is not None
        assert "Module not found: NonExistent.Module" in error_msg
        assert "Did you mean one of these?" not in error_msg


class TestFormatDependencyWithContext:
    """Test _format_dependency_with_context helper."""

    def test_format_without_module_no_context(self, mock_server_with_dependencies):
        """Test formatting without module name and without context."""
        dep = {"module": "MyApp.User", "function": "validate", "arity": 1, "line": 10}
        context_lines = {}

        lines = mock_server_with_dependencies._format_dependency_with_context(
            dep, context_lines, include_context=False, include_module=False
        )

        assert lines == ["- validate/1 (line 10)"]

    def test_format_with_module_no_context(self, mock_server_with_dependencies):
        """Test formatting with module name and without context."""
        dep = {"module": "MyApp.Repo", "function": "insert", "arity": 1, "line": 12}
        context_lines = {}

        lines = mock_server_with_dependencies._format_dependency_with_context(
            dep, context_lines, include_context=False, include_module=True
        )

        assert lines == ["- MyApp.Repo.insert/1 (line 12)"]

    def test_format_with_context(self, mock_server_with_dependencies):
        """Test formatting with code context."""
        dep = {"module": "MyApp.Repo", "function": "insert", "arity": 1, "line": 12}
        context_lines = {12: "    Repo.insert(changeset)"}

        lines = mock_server_with_dependencies._format_dependency_with_context(
            dep, context_lines, include_context=True, include_module=True
        )

        assert lines == [
            "- MyApp.Repo.insert/1 (line 12)",
            "  ```elixir",
            "      Repo.insert(changeset)",  # 2 spaces added for markdown indentation
            "  ```",
        ]

    def test_format_with_context_not_available(self, mock_server_with_dependencies):
        """Test formatting when context is requested but not available."""
        dep = {"module": "MyApp.Repo", "function": "insert", "arity": 1, "line": 12}
        context_lines = {}  # No context for line 12

        lines = mock_server_with_dependencies._format_dependency_with_context(
            dep, context_lines, include_context=True, include_module=True
        )

        # Should only show the dependency line, no code block
        assert lines == ["- MyApp.Repo.insert/1 (line 12)"]
