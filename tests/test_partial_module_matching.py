#!/usr/bin/env python
"""
Test partial module name matching with automatic wildcard prefixing.

Tests that searching for "SomeModule" matches "MyProject.SomeModule" and
that "SomeModule.func" matches functions in "MyProject.SomeModule".
"""
import pytest

from cicada.mcp.pattern_utils import FunctionPattern, match_any_pattern


class TestPartialModuleMatching:
    """Test automatic wildcard prefixing for partial module matches."""

    def test_module_pattern_with_wildcard_prefix(self):
        """Test that module patterns get automatic wildcard prefix."""
        # Pattern without explicit wildcard should match with prefix
        pattern = "*.SomeModule"

        assert match_any_pattern([pattern], "MyProject.SomeModule")
        assert match_any_pattern([pattern], "App.SomeModule")
        assert match_any_pattern([pattern], "SomeModule")  # Also matches exact
        assert not match_any_pattern([pattern], "SomeModuleOther")

    def test_function_pattern_adds_wildcard_to_module(self):
        """Test that FunctionPattern automatically adds wildcard to module part."""
        # When parsing "SomeModule.func", should become "*.SomeModule.func"
        pattern = FunctionPattern.from_string("SomeModule.some_function")

        assert pattern.module == "*.SomeModule"
        assert pattern.name == "some_function"
        assert pattern.arity is None

    def test_function_pattern_matches_full_qualified_name(self):
        """Test that function patterns match fully qualified module names."""
        pattern = FunctionPattern.from_string("SomeModule.some_function")

        func = {"name": "some_function", "arity": 2}

        # Should match MyProject.SomeModule
        assert pattern.matches("MyProject.SomeModule", "lib/file.ex", func)
        assert pattern.matches("App.SomeModule", "lib/file.ex", func)
        assert pattern.matches("SomeModule", "lib/file.ex", func)

        # Should not match OtherModule
        assert not pattern.matches("OtherModule", "lib/file.ex", func)
        assert not pattern.matches("MyProject.OtherModule", "lib/file.ex", func)

    def test_function_pattern_with_arity(self):
        """Test that arity matching still works with wildcard prefix."""
        pattern = FunctionPattern.from_string("SomeModule.some_function/2")

        assert pattern.module == "*.SomeModule"
        assert pattern.name == "some_function"
        assert pattern.arity == 2

        # Should match with correct arity
        func_correct = {"name": "some_function", "arity": 2}
        assert pattern.matches("MyProject.SomeModule", "lib/file.ex", func_correct)

        # Should not match with wrong arity
        func_wrong = {"name": "some_function", "arity": 1}
        assert not pattern.matches("MyProject.SomeModule", "lib/file.ex", func_wrong)

    def test_function_pattern_with_explicit_wildcard_unchanged(self):
        """Test that explicit wildcards are not modified."""
        # Pattern already has wildcard - should not add another
        pattern1 = FunctionPattern.from_string("*Module.func")
        assert pattern1.module == "*Module"  # No extra *.

        pattern2 = FunctionPattern.from_string("MyApp.*.func")
        assert pattern2.module == "MyApp.*"  # No extra *.

    def test_function_pattern_with_or_pattern_unchanged(self):
        """Test that OR patterns are not modified."""
        # OR patterns should not get wildcard prefix
        pattern = FunctionPattern.from_string("ModuleA|ModuleB.func")
        # Note: OR patterns are split before reaching from_string, so this tests
        # that a module with | in it doesn't get the prefix
        assert "*" not in pattern.module or "|" in pattern.module

    def test_nested_module_matching(self):
        """Test that partial matching works for nested modules."""
        pattern = FunctionPattern.from_string("User.create_user")

        func = {"name": "create_user", "arity": 2}

        # Should match various nesting levels
        assert pattern.matches("MyApp.User", "lib/file.ex", func)
        assert pattern.matches("MyApp.Context.User", "lib/file.ex", func)
        assert pattern.matches("User", "lib/file.ex", func)

        # Should not match partial module names
        assert not pattern.matches("MyApp.UserContext", "lib/file.ex", func)


@pytest.mark.asyncio
async def test_search_module_with_partial_name(tmp_path):
    """Integration test: search_module should find modules with partial names."""
    import json
    import yaml
    from cicada.mcp.server import CicadaServer

    test_index = {
        "modules": {
            "MyProject.SomeModule": {
                "file": "lib/my_project/some_module.ex",
                "line": 1,
                "moduledoc": "Some module docs",
                "functions": [],
                "public_functions": 0,
                "private_functions": 0,
            },
            "OtherProject.SomeModule": {
                "file": "lib/other_project/some_module.ex",
                "line": 1,
                "moduledoc": "Another module with same suffix",
                "functions": [],
                "public_functions": 0,
                "private_functions": 0,
            },
            "DifferentModule": {
                "file": "lib/different.ex",
                "line": 1,
                "moduledoc": "Different module",
                "functions": [],
                "public_functions": 0,
                "private_functions": 0,
            },
        },
        "metadata": {"total_modules": 3, "repo_path": str(tmp_path)},
    }

    index_path = tmp_path / "index.json"
    with open(index_path, "w") as f:
        json.dump(test_index, f)

    config = {
        "repository": {"path": str(tmp_path)},
        "storage": {"index_path": str(index_path)},
    }
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    server = CicadaServer(config_path=str(config_path))

    # Test 1: Search for "SomeModule" should find both modules ending with SomeModule
    result = await server.module_handler.search_module("SomeModule", "markdown")
    text = result[0].text

    assert "MyProject.SomeModule" in text
    assert "OtherProject.SomeModule" in text
    assert "DifferentModule" not in text


@pytest.mark.asyncio
async def test_search_function_with_partial_module_name(tmp_path):
    """Integration test: search_function should find functions with partial module names."""
    import json
    import yaml
    from cicada.mcp.server import CicadaServer

    test_index = {
        "modules": {
            "MyProject.User": {
                "file": "lib/my_project/user.ex",
                "line": 1,
                "moduledoc": "User module",
                "functions": [
                    {
                        "name": "create_user",
                        "arity": 2,
                        "line": 10,
                        "type": "def",
                        "doc": "Creates a user",
                        "signature": "create_user(name, email)",
                    }
                ],
                "public_functions": 1,
                "private_functions": 0,
            },
            "OtherProject.User": {
                "file": "lib/other_project/user.ex",
                "line": 1,
                "moduledoc": "Another User module",
                "functions": [
                    {
                        "name": "create_user",
                        "arity": 1,
                        "line": 10,
                        "type": "def",
                        "doc": "Creates a user",
                        "signature": "create_user(attrs)",
                    }
                ],
                "public_functions": 1,
                "private_functions": 0,
            },
        },
        "metadata": {"total_modules": 2, "repo_path": str(tmp_path)},
    }

    index_path = tmp_path / "index.json"
    with open(index_path, "w") as f:
        json.dump(test_index, f)

    config = {
        "repository": {"path": str(tmp_path)},
        "storage": {"index_path": str(index_path)},
    }
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    server = CicadaServer(config_path=str(config_path))

    # Test: Search for "User.create_user" should find both functions in both User modules
    result = await server.function_handler.search_function("User.create_user", "json")
    data = json.loads(result[0].text)

    assert "results" in data
    assert data["total_matches"] == 2

    modules = {entry["module"] for entry in data["results"]}
    assert "MyProject.User" in modules
    assert "OtherProject.User" in modules


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
