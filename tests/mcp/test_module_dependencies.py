"""
Tests for module dependency features in ModuleSearchHandler.

Covers:
- Transitive dependency collection
- Granular dependency info (function usage)
- search_module with what_it_calls
- Function boundary calculations
"""

import pytest

from cicada.mcp.handlers.module_handlers import ModuleSearchHandler


@pytest.fixture
def sample_index():
    """Create a sample index with dependency relationships."""
    return {
        "metadata": {"total_modules": 5},
        "modules": {
            "MyApp.Auth": {
                "name": "MyApp.Auth",
                "file": "lib/my_app/auth.ex",
                "line": 1,
                "doc": "Authentication module",
                "dependencies": {
                    "modules": ["MyApp.User", "MyApp.Logger"],
                },
                "functions": [
                    {
                        "name": "authenticate",
                        "arity": 2,
                        "line": 10,
                        "type": "def",
                        "dependencies": [
                            {"module": "MyApp.User", "function": "get", "arity": 1, "line": 15},
                            {"module": "MyApp.Logger", "function": "log", "arity": 2, "line": 20},
                        ],
                    },
                    {
                        "name": "validate",
                        "arity": 1,
                        "line": 50,
                        "type": "def",
                        "dependencies": [
                            {"module": "MyApp.User", "function": "valid?", "arity": 1, "line": 55},
                        ],
                    },
                ],
            },
            "MyApp.User": {
                "name": "MyApp.User",
                "file": "lib/my_app/user.ex",
                "line": 1,
                "doc": "User module",
                "public_functions": 2,
                "private_functions": 0,
                "dependencies": {
                    "modules": ["MyApp.Repo", "MyApp.Schema"],
                },
                "functions": [
                    {"name": "get", "arity": 1, "line": 10, "type": "def", "dependencies": []},
                    {"name": "valid?", "arity": 1, "line": 30, "type": "def", "dependencies": []},
                ],
            },
            "MyApp.Logger": {
                "name": "MyApp.Logger",
                "file": "lib/my_app/logger.ex",
                "line": 1,
                "doc": "Logger module",
                "dependencies": {
                    "modules": ["MyApp.Config"],
                },
                "functions": [
                    {"name": "log", "arity": 2, "line": 10, "type": "def", "dependencies": []},
                ],
            },
            "MyApp.Repo": {
                "name": "MyApp.Repo",
                "file": "lib/my_app/repo.ex",
                "line": 1,
                "doc": "Repository module",
                "dependencies": {"modules": []},
                "functions": [],
            },
            "MyApp.Schema": {
                "name": "MyApp.Schema",
                "file": "lib/my_app/schema.ex",
                "line": 1,
                "doc": "Schema module",
                "dependencies": {"modules": []},
                "functions": [],
            },
            "MyApp.Config": {
                "name": "MyApp.Config",
                "file": "lib/my_app/config.ex",
                "line": 1,
                "doc": "Config module",
                "dependencies": {"modules": []},
                "functions": [],
            },
        },
    }


@pytest.fixture
def handler(sample_index):
    """Create a ModuleSearchHandler with the sample index."""
    config = {"repository": {"path": "."}}
    return ModuleSearchHandler(sample_index, config)


class TestTransitiveDependencies:
    """Test transitive dependency collection."""

    def test_collect_depth_1_returns_empty(self, handler):
        """Test that depth 1 returns no transitive dependencies."""
        direct_deps = ["MyApp.User", "MyApp.Logger"]

        result = handler._collect_transitive_dependencies("MyApp.Auth", direct_deps, max_depth=1)

        # At depth 1, we only have direct deps, so transitive should be empty
        assert result == {}

    def test_collect_depth_2_returns_transitive(self, handler):
        """Test that depth 2 returns transitive dependencies."""
        direct_deps = ["MyApp.User", "MyApp.Logger"]

        result = handler._collect_transitive_dependencies("MyApp.Auth", direct_deps, max_depth=2)

        # MyApp.User depends on MyApp.Repo and MyApp.Schema
        # MyApp.Logger depends on MyApp.Config
        assert "MyApp.Repo" in result
        assert "MyApp.Schema" in result
        assert "MyApp.Config" in result

        # Each transitive dep should show which direct dep requires it
        assert "MyApp.User" in result["MyApp.Repo"]
        assert "MyApp.User" in result["MyApp.Schema"]
        assert "MyApp.Logger" in result["MyApp.Config"]

    def test_collect_handles_missing_module(self, handler):
        """Test that collection handles references to non-existent modules."""
        # Add a reference to a non-existent module
        handler.index["modules"]["MyApp.Auth"]["dependencies"]["modules"].append("NonExistent")
        direct_deps = ["MyApp.User", "MyApp.Logger", "NonExistent"]

        result = handler._collect_transitive_dependencies("MyApp.Auth", direct_deps, max_depth=2)

        # Should still work without crashing
        assert "MyApp.Repo" in result

    def test_collect_avoids_cycles(self, handler):
        """Test that collection avoids infinite cycles."""
        # Create a cycle: Auth -> User -> Auth
        handler.index["modules"]["MyApp.User"]["dependencies"]["modules"].append("MyApp.Auth")
        direct_deps = ["MyApp.User"]

        result = handler._collect_transitive_dependencies("MyApp.Auth", direct_deps, max_depth=3)

        # Should not include self in transitive deps
        assert "MyApp.Auth" not in result


class TestGranularDependencyInfo:
    """Test granular dependency information showing function usage."""

    def test_build_granular_info(self, handler):
        """Test building function-level dependency information."""
        module_data = handler.index["modules"]["MyApp.Auth"]
        direct_deps = ["MyApp.User", "MyApp.Logger"]

        result = handler._build_granular_dependency_info(module_data, direct_deps)

        # Should show which functions use which dependencies
        assert "MyApp.User" in result
        assert "authenticate/2" in result["MyApp.User"]
        assert "validate/1" in result["MyApp.User"]

        assert "MyApp.Logger" in result
        assert "authenticate/2" in result["MyApp.Logger"]

    def test_build_granular_excludes_non_direct(self, handler):
        """Test that granular info excludes non-direct dependencies."""
        # Add a dependency to a non-direct module
        handler.index["modules"]["MyApp.Auth"]["functions"][0]["dependencies"].append(
            {"module": "SomeOther", "function": "foo", "arity": 0, "line": 25}
        )
        module_data = handler.index["modules"]["MyApp.Auth"]
        direct_deps = ["MyApp.User", "MyApp.Logger"]

        result = handler._build_granular_dependency_info(module_data, direct_deps)

        # SomeOther is not in direct deps, so should not appear
        assert "SomeOther" not in result

    def test_build_granular_empty_when_no_dependencies(self, handler):
        """Test that granular info is empty when functions have no matching dependencies."""
        module_data = handler.index["modules"]["MyApp.Repo"]

        result = handler._build_granular_dependency_info(module_data, [])

        assert result == {}


class TestGetModuleDependencies:
    """Test the _get_module_dependencies method."""

    @pytest.mark.asyncio
    async def test_returns_none_when_no_dependencies(self, handler):
        """Test that method returns None when module has no dependencies."""
        module_data = handler.index["modules"]["MyApp.Repo"]

        result = await handler._get_module_dependencies("MyApp.Repo", module_data, 1, False)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_direct_dependencies(self, handler):
        """Test that method returns direct dependencies."""
        module_data = handler.index["modules"]["MyApp.Auth"]

        result = await handler._get_module_dependencies("MyApp.Auth", module_data, 1, False)

        assert result is not None
        assert "MyApp.User" in result["direct"]
        assert "MyApp.Logger" in result["direct"]
        assert result["transitive"] == {}
        assert result["granular"] == {}

    @pytest.mark.asyncio
    async def test_returns_transitive_when_depth_gt_1(self, handler):
        """Test that method returns transitive deps when depth > 1."""
        module_data = handler.index["modules"]["MyApp.Auth"]

        result = await handler._get_module_dependencies("MyApp.Auth", module_data, 2, False)

        assert result is not None
        assert "MyApp.Repo" in result["transitive"]
        assert "MyApp.Schema" in result["transitive"]

    @pytest.mark.asyncio
    async def test_returns_granular_when_requested(self, handler):
        """Test that method returns granular info when requested."""
        module_data = handler.index["modules"]["MyApp.Auth"]

        result = await handler._get_module_dependencies("MyApp.Auth", module_data, 1, True)

        assert result is not None
        assert "MyApp.User" in result["granular"]
        assert "authenticate/2" in result["granular"]["MyApp.User"]


class TestFunctionBoundaryCalculations:
    """Test function end line calculation and line-to-function mapping."""

    def test_calculate_function_end_with_next_function(self, handler):
        """Test end line calculation when there's a next function."""
        functions = handler.index["modules"]["MyApp.Auth"]["functions"]

        # authenticate (line 10) followed by validate (line 50)
        end_line = handler._calculate_function_end_line(functions, 0, 10)

        # Should be line before next function
        assert end_line == 49

    def test_calculate_function_end_last_function(self, handler):
        """Test end line calculation for last function in module."""
        functions = handler.index["modules"]["MyApp.Auth"]["functions"]

        # validate is at line 50 and is the last function
        end_line = handler._calculate_function_end_line(functions, 1, 50)

        # Should be start + APPROXIMATE_FUNCTION_LENGTH (100)
        assert end_line == 150

    def test_find_function_at_line_exact_match(self, handler):
        """Test finding function when line is exactly at function start."""
        result = handler._find_function_at_line("MyApp.Auth", 10)

        assert result is not None
        assert result["name"] == "authenticate"
        assert result["arity"] == 2

    def test_find_function_at_line_inside_function(self, handler):
        """Test finding function when line is inside function body."""
        result = handler._find_function_at_line("MyApp.Auth", 25)

        assert result is not None
        assert result["name"] == "authenticate"
        assert result["arity"] == 2

    def test_find_function_at_line_second_function(self, handler):
        """Test finding second function at its start line."""
        result = handler._find_function_at_line("MyApp.Auth", 55)

        assert result is not None
        assert result["name"] == "validate"
        assert result["arity"] == 1

    def test_find_function_at_line_before_all_functions(self, handler):
        """Test returning None when line is before all functions."""
        result = handler._find_function_at_line("MyApp.Auth", 5)

        assert result is None

    def test_find_function_at_line_nonexistent_module(self, handler):
        """Test returning None for non-existent module."""
        result = handler._find_function_at_line("NonExistent", 10)

        assert result is None


class TestSearchModuleWithDependencies:
    """Test search_module with what_it_calls parameter."""

    @pytest.mark.asyncio
    async def test_search_with_what_it_calls(self, handler):
        """Test search_module calls dependency methods when what_it_calls=True."""
        # Need to provide a mock dependency_handler
        handler.dependency_handler = object()  # Just needs to be truthy

        result = await handler.search_module(
            module_name="MyApp.Auth",
            what_it_calls=True,
            dependency_depth=2,
            show_function_usage=True,
        )

        assert len(result) == 1
        # The code path for _get_module_dependencies is exercised
        # Output format varies by formatter configuration
        assert "MyApp.Auth" in result[0].text

    @pytest.mark.asyncio
    async def test_search_without_what_it_calls(self, handler):
        """Test search_module doesn't include dependencies when what_it_calls=False."""
        result = await handler.search_module(
            module_name="MyApp.Auth",
            what_it_calls=False,
        )

        assert len(result) == 1
        # Basic module info should still be present
        assert "MyApp.Auth" in result[0].text

    @pytest.mark.asyncio
    async def test_search_module_not_found(self, handler):
        """Test search_module handles non-existent module."""
        result = await handler.search_module(
            module_name="NonExistent",
        )

        assert len(result) == 1
        assert "not found" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_search_module_json_with_usage(self, handler):
        """Test search_module JSON output includes usage data when what_calls_it=True."""
        import json

        result = await handler.search_module(
            module_name="MyApp.User",
            what_calls_it=True,
            output_format="json",
        )

        assert len(result) == 1
        output = json.loads(result[0].text)

        # Verify module info is present
        assert output["module"] == "MyApp.User"

        # Verify usage data is present and not empty
        assert "usage" in output
        assert output["usage"] is not None
        assert isinstance(output["usage"], dict)

        # Verify usage has expected structure from format_module_usage_json
        assert "module" in output["usage"]
        assert output["usage"]["module"] == "MyApp.User"
        assert "aliases" in output["usage"]
        assert "imports" in output["usage"]
        assert "function_calls" in output["usage"]
        assert "summary" in output["usage"]

        # Verify it's not an empty dict (the bug we're fixing)
        assert len(output["usage"]) > 1  # At least module + one data field


class TestLookupModuleWithError:
    """Test module lookup with error handling."""

    def test_lookup_existing_module(self, handler):
        """Test looking up an existing module."""
        data, error = handler.lookup_module_with_error("MyApp.Auth")

        assert data is not None
        assert error is None

    def test_lookup_nonexistent_module_with_suggestions(self, handler):
        """Test looking up non-existent module shows suggestions."""
        data, error = handler.lookup_module_with_error("MyApp.Authh")  # Typo

        assert data is None
        assert error is not None
        assert "not found" in error.lower()


class TestResolveFileToModule:
    """Test file path to module name resolution."""

    def test_resolve_exact_match(self, handler):
        """Test resolving exact file path match."""
        result = handler.resolve_file_to_module("lib/my_app/auth.ex")

        assert result == "MyApp.Auth"

    def test_resolve_partial_path(self, handler):
        """Test resolving partial file path."""
        result = handler.resolve_file_to_module("auth.ex")

        assert result == "MyApp.Auth"

    def test_resolve_with_prefix(self, handler):
        """Test resolving file path with leading ./."""
        result = handler.resolve_file_to_module("./lib/my_app/auth.ex")

        assert result == "MyApp.Auth"

    def test_resolve_nonexistent_file(self, handler):
        """Test resolving non-existent file returns None."""
        result = handler.resolve_file_to_module("lib/nonexistent.ex")

        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
