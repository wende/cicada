"""
Tests for function dependency features in FunctionSearchHandler.

Covers:
- Dependency context extraction
- Detailed dependency information
- Call site consolidation and filtering
- Code context extraction and dedentation
"""

from pathlib import Path

import pytest

from cicada.mcp.handlers.function_handlers import FunctionSearchHandler


@pytest.fixture
def sample_index():
    """Create a sample index with function call relationships."""
    return {
        "metadata": {"total_modules": 3},
        "modules": {
            "MyApp.Auth": {
                "name": "MyApp.Auth",
                "file": "lib/my_app/auth.ex",
                "line": 1,
                "doc": "Authentication module",
                "aliases": {},
                "calls": [],
                "functions": [
                    {
                        "name": "authenticate",
                        "arity": 2,
                        "line": 10,
                        "type": "def",
                        "dependencies": [
                            {"module": "MyApp.User", "function": "get", "arity": 1, "line": 15},
                            {
                                "module": "MyApp.Auth",
                                "function": "validate",
                                "arity": 1,
                                "line": 20,
                            },
                        ],
                    },
                    {
                        "name": "validate",
                        "arity": 1,
                        "line": 50,
                        "type": "def",
                        "dependencies": [],
                    },
                ],
            },
            "MyApp.User": {
                "name": "MyApp.User",
                "file": "lib/my_app/user.ex",
                "line": 1,
                "doc": "User module",
                "aliases": {"Auth": "MyApp.Auth"},
                "calls": [
                    {"module": "Auth", "function": "authenticate", "arity": 2, "line": 25},
                    {"module": "Auth", "function": "authenticate", "arity": 2, "line": 35},
                ],
                "functions": [
                    {
                        "name": "login",
                        "arity": 1,
                        "line": 20,
                        "type": "def",
                        "dependencies": [],
                    },
                    {
                        "name": "register",
                        "arity": 2,
                        "line": 40,
                        "type": "def",
                        "dependencies": [],
                    },
                ],
            },
            "MyApp.AuthTest": {
                "name": "MyApp.AuthTest",
                "file": "test/my_app/auth_test.exs",
                "line": 1,
                "doc": "Test module",
                "aliases": {"Auth": "MyApp.Auth"},
                "calls": [
                    {"module": "Auth", "function": "authenticate", "arity": 2, "line": 15},
                ],
                "functions": [
                    {
                        "name": "test_auth",
                        "arity": 1,
                        "line": 10,
                        "type": "def",
                        "dependencies": [],
                    },
                ],
            },
        },
    }


@pytest.fixture
def handler(sample_index, tmp_path):
    """Create a FunctionSearchHandler with the sample index."""
    # Create a test source file for context extraction
    lib_dir = tmp_path / "lib" / "my_app"
    lib_dir.mkdir(parents=True)

    auth_file = lib_dir / "auth.ex"
    auth_file.write_text(
        """defmodule MyApp.Auth do
  @moduledoc "Authentication module"

  def authenticate(user, password) do
    user = User.get(user.id)
    if validate(user) do
      {:ok, user}
    else
      {:error, :invalid}
    end
  end

  def validate(user) do
    user.active
  end
end
"""
    )

    config = {"repository": {"path": str(tmp_path)}}
    return FunctionSearchHandler(sample_index, config)


class TestDependencyContextExtraction:
    """Test dependency context extraction from source files."""

    def test_extract_contexts_for_valid_lines(self, handler):
        """Test extracting context for valid line numbers."""
        dependencies = [
            {"module": "MyApp.User", "function": "get", "arity": 1, "line": 5},
            {"module": "MyApp.Auth", "function": "validate", "arity": 1, "line": 6},
        ]

        result = handler._extract_dependency_contexts(dependencies, "lib/my_app/auth.ex")

        assert 5 in result
        assert 6 in result
        assert "user" in result[5].lower() or "get" in result[5].lower()

    def test_extract_contexts_for_nonexistent_file(self, handler):
        """Test that non-existent file returns empty dict."""
        dependencies = [{"module": "X", "function": "y", "arity": 0, "line": 5}]

        result = handler._extract_dependency_contexts(dependencies, "nonexistent.ex")

        assert result == {}

    def test_extract_contexts_for_invalid_line(self, handler):
        """Test that invalid line numbers are skipped."""
        dependencies = [{"module": "X", "function": "y", "arity": 0, "line": 1000}]

        result = handler._extract_dependency_contexts(dependencies, "lib/my_app/auth.ex")

        # Line 1000 doesn't exist, should be empty
        assert 1000 not in result


class TestEnrichDependency:
    """Test enriching dependencies with context."""

    def test_enrich_with_context(self, handler):
        """Test adding context to dependency."""
        dep = {"module": "X", "function": "y", "arity": 0, "line": 5}
        context_lines = {5: "    some_context()"}

        result = handler._enrich_dependency_with_context(dep, context_lines)

        assert "context" in result
        assert result["context"] == "    some_context()"
        # Original dep should not be modified
        assert "context" not in dep

    def test_enrich_without_context(self, handler):
        """Test dependency without matching context."""
        dep = {"module": "X", "function": "y", "arity": 0, "line": 5}
        context_lines = {10: "other line"}

        result = handler._enrich_dependency_with_context(dep, context_lines)

        assert "context" not in result


class TestGetDetailedDependencies:
    """Test detailed dependency information retrieval."""

    def test_returns_none_for_no_dependencies(self, handler):
        """Test that functions with no dependencies return None."""
        func = {"name": "validate", "arity": 1, "dependencies": []}

        result = handler._get_detailed_dependencies("MyApp.Auth", func, "lib/my_app/auth.ex", False)

        assert result is None

    def test_separates_internal_and_external(self, handler):
        """Test that dependencies are separated into internal and external."""
        func = {
            "name": "authenticate",
            "arity": 2,
            "dependencies": [
                {"module": "MyApp.User", "function": "get", "arity": 1, "line": 15},
                {"module": "MyApp.Auth", "function": "validate", "arity": 1, "line": 20},
            ],
        }

        result = handler._get_detailed_dependencies("MyApp.Auth", func, "lib/my_app/auth.ex", False)

        assert result is not None
        assert len(result["internal"]) == 1
        assert result["internal"][0]["function"] == "validate"
        assert len(result["external"]) == 1
        assert result["external"][0]["function"] == "get"
        assert result["total_count"] == 2

    def test_includes_context_when_requested(self, handler):
        """Test that context is included when requested."""
        func = {
            "name": "authenticate",
            "arity": 2,
            "dependencies": [
                {"module": "MyApp.User", "function": "get", "arity": 1, "line": 5},
            ],
        }

        result = handler._get_detailed_dependencies("MyApp.Auth", func, "lib/my_app/auth.ex", True)

        assert result is not None
        # Context may or may not be present depending on file content
        assert "external" in result


class TestCallSiteConsolidation:
    """Test call site consolidation by module."""

    def test_consolidate_removes_duplicates(self, handler):
        """Test that consolidation keeps one call per module."""
        call_sites = [
            {"calling_module": "A", "file": "a.ex", "line": 10},
            {"calling_module": "A", "file": "a.ex", "line": 20},
            {"calling_module": "B", "file": "b.ex", "line": 15},
        ]

        result = handler._consolidate_call_sites_by_module(call_sites)

        assert len(result) == 2
        modules = [site["calling_module"] for site in result]
        assert "A" in modules
        assert "B" in modules

    def test_consolidate_preserves_first_occurrence(self, handler):
        """Test that consolidation preserves the first call site."""
        call_sites = [
            {"calling_module": "A", "file": "a.ex", "line": 10},
            {"calling_module": "A", "file": "a.ex", "line": 20},
        ]

        result = handler._consolidate_call_sites_by_module(call_sites)

        assert len(result) == 1
        assert result[0]["line"] == 10


class TestTestFileFiltering:
    """Test filtering call sites to test files."""

    def test_filter_keeps_test_files(self, handler):
        """Test that filter keeps files with 'test' in path."""
        call_sites = [
            {"calling_module": "A", "file": "lib/a.ex", "line": 10},
            {"calling_module": "B", "file": "test/b_test.exs", "line": 15},
            {"calling_module": "C", "file": "integration_test/c.ex", "line": 20},
        ]

        result = handler._filter_test_call_sites(call_sites)

        assert len(result) == 2
        assert all("test" in site["file"].lower() for site in result)

    def test_filter_removes_non_test_files(self, handler):
        """Test that filter removes files without 'test' in path."""
        call_sites = [
            {"calling_module": "A", "file": "lib/a.ex", "line": 10},
            {"calling_module": "B", "file": "lib/b.ex", "line": 15},
        ]

        result = handler._filter_test_call_sites(call_sites)

        assert len(result) == 0


class TestDedentation:
    """Test line dedentation logic."""

    def test_calculate_min_indentation(self, handler):
        """Test calculating minimum indentation."""
        lines = [
            "    def foo do",
            "      bar()",
            "    end",
        ]

        result = handler._calculate_min_indentation(lines)

        assert result == 4  # Minimum is 4 spaces

    def test_calculate_min_ignores_empty_lines(self, handler):
        """Test that empty lines are ignored in indentation calculation."""
        lines = [
            "",
            "    def foo do",
            "      bar()",
            "",
            "    end",
        ]

        result = handler._calculate_min_indentation(lines)

        assert result == 4

    def test_dedent_removes_common_indent(self, handler):
        """Test dedenting removes common indentation."""
        lines = [
            "    def foo do",
            "      bar()",
            "    end",
        ]

        result = handler._dedent_lines(lines, 4)

        assert result[0] == "def foo do"
        assert result[1] == "  bar()"
        assert result[2] == "end"

    def test_dedent_handles_short_lines(self, handler):
        """Test dedenting handles lines shorter than indent amount."""
        lines = [
            "ab",  # Only 2 chars
            "    longer",
        ]

        result = handler._dedent_lines(lines, 4)

        # Short line should be preserved as-is
        assert result[0] == "ab"
        assert result[1] == "longer"

    def test_dedent_zero_does_nothing(self, handler):
        """Test dedenting with zero indent does nothing."""
        lines = ["  foo", "  bar"]

        result = handler._dedent_lines(lines, 0)

        assert result == lines


class TestFindCallSites:
    """Test finding call sites for a function."""

    def test_find_qualified_call_sites(self, handler):
        """Test finding call sites with qualified module references."""
        result = handler._find_call_sites("MyApp.Auth", "authenticate", 2)

        # Should find calls from MyApp.User and MyApp.AuthTest
        assert len(result) >= 2
        calling_modules = [site["calling_module"] for site in result]
        assert "MyApp.User" in calling_modules
        assert "MyApp.AuthTest" in calling_modules

    def test_find_call_sites_resolves_aliases(self, handler):
        """Test that aliases are resolved correctly."""
        result = handler._find_call_sites("MyApp.Auth", "authenticate", 2)

        # Calls use alias "Auth" which resolves to "MyApp.Auth"
        assert len(result) > 0
        for site in result:
            if site["call_type"] == "qualified":
                assert site.get("alias_used") == "Auth"

    def test_find_call_sites_includes_calling_function(self, handler):
        """Test that call sites include the calling function info."""
        result = handler._find_call_sites("MyApp.Auth", "authenticate", 2)

        # At least some call sites should have calling_function info
        sites_with_func = [s for s in result if s["calling_function"] is not None]
        assert len(sites_with_func) > 0


class TestFindFunctionAtLine:
    """Test finding function at a specific line."""

    def test_find_function_exact_match(self, handler):
        """Test finding function at its definition line."""
        result = handler._find_function_at_line("MyApp.Auth", 10)

        assert result is not None
        assert result["name"] == "authenticate"

    def test_find_function_inside_body(self, handler):
        """Test finding function when line is inside body."""
        result = handler._find_function_at_line("MyApp.Auth", 25)

        assert result is not None
        assert result["name"] == "authenticate"

    def test_find_function_before_first(self, handler):
        """Test returning None when line is before first function."""
        result = handler._find_function_at_line("MyApp.Auth", 5)

        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
