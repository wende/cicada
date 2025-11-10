"""
Tests for dependency analysis (module and function level).

These tests verify that we can extract clean dependency information
from the already-parsed AST data.
"""

import pytest


class TestModuleDependencyExtraction:
    """Test extraction of module-level dependencies."""

    def test_extract_dependencies_from_aliases(self):
        """Test extracting dependencies from alias statements."""
        # Simulating already-extracted data from parser
        module_data = {
            "module": "MyApp.User",
            "aliases": {
                "Repo": "MyApp.Repo",
                "Auth": "MyApp.Auth",
                "Mailer": "MyApp.Mailer",
                "Schema": "MyApp.Accounts.Schema",
            },
            "imports": [],
            "uses": [],
            "calls": [],
        }

        from cicada.dependency_analyzer import extract_module_dependencies

        deps = extract_module_dependencies(module_data)

        assert "MyApp.Repo" in deps["modules"]
        assert "MyApp.Auth" in deps["modules"]
        assert "MyApp.Mailer" in deps["modules"]
        assert "MyApp.Accounts.Schema" in deps["modules"]

    def test_extract_dependencies_from_imports(self):
        """Test extracting dependencies from import statements."""
        module_data = {
            "module": "MyApp.User",
            "aliases": {},
            "imports": ["Ecto.Query", "MyApp.Helpers"],
            "uses": [],
            "calls": [],
        }

        from cicada.dependency_analyzer import extract_module_dependencies

        deps = extract_module_dependencies(module_data)

        assert "Ecto.Query" in deps["modules"]
        assert "MyApp.Helpers" in deps["modules"]

    def test_extract_dependencies_from_uses(self):
        """Test extracting dependencies from use directives."""
        module_data = {
            "module": "MyApp.User",
            "aliases": {},
            "imports": [],
            "uses": ["MyApp.Schema", "Ecto.Schema"],
            "calls": [],
        }

        from cicada.dependency_analyzer import extract_module_dependencies

        deps = extract_module_dependencies(module_data)

        assert "MyApp.Schema" in deps["modules"]
        assert "Ecto.Schema" in deps["modules"]

    def test_extract_dependencies_from_qualified_calls(self):
        """Test extracting dependencies from Module.function() calls."""
        module_data = {
            "module": "MyApp.User",
            "aliases": {
                "Repo": "MyApp.Repo",  # Repo is aliased
            },
            "imports": [],
            "uses": [],
            "calls": [
                {"module": "Repo", "function": "insert", "arity": 1, "line": 15},
                {"module": "Logger", "function": "info", "arity": 1, "line": 16},
                {
                    "module": None,
                    "function": "validate_attrs",
                    "arity": 1,
                    "line": 17,
                },  # Local call
            ],
        }

        from cicada.dependency_analyzer import extract_module_dependencies

        deps = extract_module_dependencies(module_data)

        # Should resolve "Repo" to "MyApp.Repo" via aliases
        assert "MyApp.Repo" in deps["modules"]
        # Logger is not aliased, so it should appear as-is
        assert "Logger" in deps["modules"]

    def test_resolves_aliases_in_calls(self):
        """Test that aliased modules in calls are resolved to full names."""
        module_data = {
            "module": "MyApp.User",
            "aliases": {
                "Repo": "MyApp.Repo",
                "Auth": "MyApp.Auth",
            },
            "imports": [],
            "uses": [],
            "calls": [
                {"module": "Repo", "function": "insert", "arity": 1, "line": 15},
                {"module": "Auth", "function": "hash_password", "arity": 1, "line": 16},
            ],
        }

        from cicada.dependency_analyzer import extract_module_dependencies

        deps = extract_module_dependencies(module_data)

        assert "MyApp.Repo" in deps["modules"]
        assert "MyApp.Auth" in deps["modules"]
        # Should NOT have short names
        assert "Repo" not in deps["modules"]
        assert "Auth" not in deps["modules"]

    def test_excludes_local_calls_from_module_dependencies(self):
        """Test that local function calls don't create module dependencies."""
        module_data = {
            "module": "MyApp.User",
            "aliases": {},
            "imports": [],
            "uses": [],
            "calls": [
                {
                    "module": None,
                    "function": "validate_attrs",
                    "arity": 1,
                    "line": 15,
                },  # Local
                {
                    "module": None,
                    "function": "hash_password",
                    "arity": 1,
                    "line": 16,
                },  # Local
                {"module": "Repo", "function": "insert", "arity": 1, "line": 17},  # External
            ],
        }

        from cicada.dependency_analyzer import extract_module_dependencies

        deps = extract_module_dependencies(module_data)

        # Should only have the external module
        assert "Repo" in deps["modules"]
        # Should not have created dependencies for local calls
        assert len(deps["modules"]) == 1

    def test_handles_requires_and_behaviours(self):
        """Test extracting dependencies from requires and behaviours."""
        module_data = {
            "module": "MyApp.User",
            "aliases": {},
            "imports": [],
            "requires": ["Logger"],
            "uses": [],
            "behaviours": ["GenServer"],
            "calls": [],
        }

        from cicada.dependency_analyzer import extract_module_dependencies

        deps = extract_module_dependencies(module_data)

        assert "Logger" in deps["modules"]
        assert "GenServer" in deps["modules"]

    def test_deduplicates_dependencies(self):
        """Test that duplicate dependencies are removed."""
        module_data = {
            "module": "MyApp.User",
            "aliases": {"Repo": "MyApp.Repo"},
            "imports": ["MyApp.Repo"],  # Also imported
            "uses": [],
            "calls": [
                {"module": "Repo", "function": "insert", "arity": 1, "line": 15},
                {"module": "Repo", "function": "update", "arity": 1, "line": 16},
            ],
        }

        from cicada.dependency_analyzer import extract_module_dependencies

        deps = extract_module_dependencies(module_data)

        # Should appear only once despite being aliased, imported, and called
        assert deps["modules"].count("MyApp.Repo") == 1


class TestFunctionDependencyExtraction:
    """Test extraction of function-level dependencies."""

    def test_extract_function_dependencies_simple(self):
        """Test extracting function calls from a function body."""
        # Simulating function data with calls
        function_data = {
            "name": "create_user",
            "arity": 2,
            "type": "def",
            "line": 10,
        }

        # Simulating calls within this function (extracted from AST)
        # In reality, we'd need to filter calls by line range
        function_calls = [
            {
                "module": None,
                "function": "validate_attrs",
                "arity": 1,
                "line": 11,
            },  # Local
            {
                "module": None,
                "function": "hash_password",
                "arity": 1,
                "line": 12,
            },  # Local
            {"module": "Repo", "function": "insert", "arity": 1, "line": 13},  # External
        ]

        module_data = {
            "module": "MyApp.User",
            "aliases": {"Repo": "MyApp.Repo"},
        }

        from cicada.dependency_analyzer import extract_function_dependencies

        deps = extract_function_dependencies(
            module_data, function_data, function_calls, function_end_line=14
        )

        assert len(deps) == 3

        # Check local calls
        local_calls = [d for d in deps if d["module"] == "MyApp.User"]
        assert len(local_calls) == 2
        assert any(d["function"] == "validate_attrs" and d["arity"] == 1 for d in local_calls)
        assert any(d["function"] == "hash_password" and d["arity"] == 1 for d in local_calls)

        # Check external call with resolved alias
        external_calls = [d for d in deps if d["module"] != "MyApp.User"]
        assert len(external_calls) == 1
        assert external_calls[0]["module"] == "MyApp.Repo"
        assert external_calls[0]["function"] == "insert"
        assert external_calls[0]["arity"] == 1
        assert external_calls[0]["line"] == 13

    def test_filters_calls_by_line_range(self):
        """Test that only calls within the function are included."""
        function_data = {
            "name": "create_user",
            "arity": 2,
            "type": "def",
            "line": 10,
        }

        # Calls from entire module
        all_module_calls = [
            {
                "module": None,
                "function": "some_other_func",
                "arity": 0,
                "line": 5,
            },  # Before function
            {
                "module": None,
                "function": "validate_attrs",
                "arity": 1,
                "line": 11,
            },  # In function
            {
                "module": None,
                "function": "another_func",
                "arity": 0,
                "line": 20,
            },  # After function
        ]

        module_data = {
            "module": "MyApp.User",
            "aliases": {},
        }

        from cicada.dependency_analyzer import extract_function_dependencies

        deps = extract_function_dependencies(
            module_data,
            function_data,
            all_module_calls,
            function_end_line=15,  # Function ends at line 15
        )

        # Should only include the call at line 11
        assert len(deps) == 1
        assert deps[0]["function"] == "validate_attrs"
        assert deps[0]["line"] == 11

    def test_resolves_aliases_in_function_calls(self):
        """Test that aliases are resolved in function-level dependencies."""
        function_data = {
            "name": "create_user",
            "arity": 2,
            "type": "def",
            "line": 10,
        }

        function_calls = [
            {"module": "Repo", "function": "insert", "arity": 1, "line": 11},
            {"module": "Auth", "function": "hash_password", "arity": 1, "line": 12},
        ]

        module_data = {
            "module": "MyApp.User",
            "aliases": {
                "Repo": "MyApp.Repo",
                "Auth": "MyApp.Auth",
            },
        }

        from cicada.dependency_analyzer import extract_function_dependencies

        deps = extract_function_dependencies(
            module_data, function_data, function_calls, function_end_line=13
        )

        # Check that aliases were resolved
        assert any(d["module"] == "MyApp.Repo" and d["function"] == "insert" for d in deps)
        assert any(d["module"] == "MyApp.Auth" and d["function"] == "hash_password" for d in deps)


class TestDependencyEdgeCases:
    """Test edge cases in dependency extraction."""

    def test_handles_empty_dependencies(self):
        """Test handling modules with no dependencies."""
        module_data = {
            "module": "MyApp.User",
            "aliases": {},
            "imports": [],
            "uses": [],
            "calls": [],
        }

        from cicada.dependency_analyzer import extract_module_dependencies

        deps = extract_module_dependencies(module_data)

        assert "modules" in deps
        assert len(deps["modules"]) == 0

    def test_handles_missing_fields(self):
        """Test handling module data with missing optional fields."""
        module_data = {
            "module": "MyApp.User",
            "aliases": {},
            # Missing imports, uses, calls
        }

        from cicada.dependency_analyzer import extract_module_dependencies

        deps = extract_module_dependencies(module_data)

        # Should not crash
        assert "modules" in deps

    def test_excludes_kernel_functions(self):
        """Test that Kernel functions are excluded (too noisy)."""
        module_data = {
            "module": "MyApp.User",
            "aliases": {},
            "imports": [],
            "uses": [],
            "calls": [
                # Kernel functions that should be excluded
                {"module": "Kernel", "function": "if", "arity": 2, "line": 10},
                {"module": "Kernel", "function": "+", "arity": 2, "line": 11},
                # Regular function that should be included
                {"module": "MyApp.Repo", "function": "insert", "arity": 1, "line": 12},
            ],
        }

        from cicada.dependency_analyzer import extract_module_dependencies

        deps = extract_module_dependencies(module_data)

        # Should NOT include Kernel
        assert "Kernel" not in deps["modules"]
        # Should include the regular module
        assert "MyApp.Repo" in deps["modules"]
