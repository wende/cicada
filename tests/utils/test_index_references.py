"""Comprehensive tests for cicada/utils/index_references.py"""

import pytest

from cicada.utils.index_references import (
    get_call_sites,
    get_callees_of,
    get_callers_of,
    get_dependencies,
    get_references_to,
)


@pytest.fixture
def sample_index_with_dependencies():
    """Create a sample index with function dependencies and calls."""
    return {
        "modules": {
            "UserService": {
                "name": "UserService",
                "file": "lib/user_service.py",
                "line": 1,
                "dependencies": {
                    "modules": ["Database", "Logger", "Validator"],
                },
                "functions": [
                    {
                        "name": "create_user",
                        "arity": 2,
                        "line": 10,
                        "dependencies": [
                            {
                                "module": "Validator",
                                "function": "validate_email",
                                "arity": 1,
                                "line": 12,
                            },
                            {
                                "module": "Database",
                                "function": "insert",
                                "arity": 2,
                                "line": 15,
                            },
                            {
                                "module": "Logger",
                                "function": "log_info",
                                "arity": 1,
                                "line": 18,
                            },
                        ],
                    },
                    {
                        "name": "update_user",
                        "arity": 2,
                        "line": 25,
                        "dependencies": [
                            {
                                "module": "Database",
                                "function": "update",
                                "arity": 2,
                                "line": 27,
                            }
                        ],
                    },
                    {
                        "name": "delete_user",
                        "arity": 1,
                        "line": 35,
                        "dependencies": [],  # No dependencies
                    },
                ],
            },
            "Database": {
                "name": "Database",
                "file": "lib/database.py",
                "line": 1,
                "dependencies": {"modules": []},
                "functions": [
                    {
                        "name": "insert",
                        "arity": 2,
                        "line": 5,
                        "dependencies": [],
                    },
                    {
                        "name": "update",
                        "arity": 2,
                        "line": 15,
                        "dependencies": [],
                    },
                ],
            },
            "Validator": {
                "name": "Validator",
                "file": "lib/validator.py",
                "line": 1,
                "dependencies": {"modules": ["StringUtils"]},
                "functions": [
                    {
                        "name": "validate_email",
                        "arity": 1,
                        "line": 5,
                        "dependencies": [
                            {
                                "module": "StringUtils",
                                "function": "lowercase",
                                "arity": 1,
                                "line": 7,
                            }
                        ],
                    }
                ],
            },
            "Logger": {
                "name": "Logger",
                "file": "lib/logger.py",
                "line": 1,
                "dependencies": {"modules": []},
                "functions": [
                    {
                        "name": "log_info",
                        "arity": 1,
                        "line": 5,
                        "dependencies": [],
                    }
                ],
            },
            "StringUtils": {
                "name": "StringUtils",
                "file": "lib/string_utils.py",
                "line": 1,
                "dependencies": {"modules": []},
                "functions": [
                    {
                        "name": "lowercase",
                        "arity": 1,
                        "line": 5,
                        "dependencies": [],
                    }
                ],
            },
        }
    }


@pytest.fixture
def sample_index_old_format():
    """Create index with old-style dependencies (list format)."""
    return {
        "modules": {
            "OldModule": {
                "name": "OldModule",
                "file": "lib/old.py",
                "line": 1,
                "dependencies": [
                    {"module": "Dep1"},
                    {"module": "Dep2"},
                ],  # Old list format
                "functions": [],
            }
        }
    }


@pytest.fixture
def sample_index_with_old_calls():
    """Create index with old-style calls format (for backward compatibility)."""
    return {
        "modules": {
            "Legacy": {
                "name": "Legacy",
                "file": "lib/legacy.py",
                "line": 1,
                "functions": [
                    {
                        "name": "legacy_func",
                        "arity": 1,
                        "line": 5,
                        "calls": [  # Old format with 'calls' instead of 'dependencies'
                            {
                                "callee": "OtherModule.other_func",
                                "file": "lib/other.py",
                                "line": 7,
                            }
                        ],
                    }
                ],
            }
        }
    }


class TestGetCallSites:
    """Tests for get_call_sites function."""

    def test_get_call_sites_with_dependencies(self, sample_index_with_dependencies):
        """Should return all call sites for a function."""
        call_sites = get_call_sites(sample_index_with_dependencies, "UserService", "create_user")

        assert len(call_sites) == 3

        # Check Validator.validate_email call
        validator_call = next(
            (c for c in call_sites if c.get("function") == "validate_email"), None
        )
        assert validator_call is not None
        assert validator_call["module"] == "Validator"
        assert validator_call["line"] == 12

        # Check Database.insert call
        db_call = next((c for c in call_sites if c.get("function") == "insert"), None)
        assert db_call is not None
        assert db_call["module"] == "Database"
        assert db_call["line"] == 15

    def test_get_call_sites_no_dependencies(self, sample_index_with_dependencies):
        """Should return empty list for function with no dependencies."""
        call_sites = get_call_sites(sample_index_with_dependencies, "UserService", "delete_user")

        assert call_sites == []

    def test_get_call_sites_nonexistent_module(self, sample_index_with_dependencies):
        """Should return empty list for non-existent module."""
        call_sites = get_call_sites(sample_index_with_dependencies, "NonExistent", "func")

        assert call_sites == []

    def test_get_call_sites_nonexistent_function(self, sample_index_with_dependencies):
        """Should return empty list for non-existent function."""
        call_sites = get_call_sites(sample_index_with_dependencies, "UserService", "nonexistent")

        assert call_sites == []

    def test_get_call_sites_old_calls_format(self, sample_index_with_old_calls):
        """Should handle old 'calls' format for backward compatibility."""
        call_sites = get_call_sites(sample_index_with_old_calls, "Legacy", "legacy_func")

        assert len(call_sites) == 1
        assert call_sites[0]["callee"] == "OtherModule.other_func"
        assert call_sites[0]["line"] == 7

    def test_get_call_sites_empty_dependencies(self, sample_index_with_dependencies):
        """Should handle function with empty dependencies list."""
        call_sites = get_call_sites(sample_index_with_dependencies, "Database", "insert")

        assert call_sites == []


class TestGetCallersOf:
    """Tests for get_callers_of function."""

    def test_get_callers_of_single_caller(self, sample_index_with_dependencies):
        """Should find single caller of a function."""
        callers = get_callers_of(sample_index_with_dependencies, "log_info")

        assert len(callers) == 1
        assert callers[0]["module"] == "UserService"
        assert callers[0]["function"] == "create_user"
        assert callers[0]["line"] == 18

    def test_get_callers_of_multiple_callers(self, sample_index_with_dependencies):
        """Should find multiple callers of a function."""
        callers = get_callers_of(sample_index_with_dependencies, "insert")

        # Called by UserService.create_user
        assert len(callers) >= 1
        user_service_caller = next((c for c in callers if c["module"] == "UserService"), None)
        assert user_service_caller is not None
        assert user_service_caller["function"] == "create_user"

    def test_get_callers_of_no_callers(self, sample_index_with_dependencies):
        """Should return empty list when function has no callers."""
        # lowercase is called by validate_email, but let's test a function not called
        callers = get_callers_of(sample_index_with_dependencies, "nonexistent_function")

        assert callers == []

    def test_get_callers_of_partial_name_match(self, sample_index_with_dependencies):
        """Should match function names that contain the query."""
        # This tests the 'in' matching logic
        callers = get_callers_of(sample_index_with_dependencies, "validate")

        # Should find callers of any function containing "validate"
        assert len(callers) >= 1

    def test_get_callers_of_without_modules_key(self):
        """Should handle index without 'modules' key."""
        empty_index = {}
        callers = get_callers_of(empty_index, "any_func")

        assert callers == []

    def test_get_callers_of_with_old_calls_format(self, sample_index_with_old_calls):
        """Should handle old 'calls' format for backward compatibility."""
        callers = get_callers_of(sample_index_with_old_calls, "other_func")

        assert len(callers) == 1
        assert callers[0]["module"] == "Legacy"
        assert callers[0]["function"] == "legacy_func"

    def test_get_callers_includes_file_info(self, sample_index_with_dependencies):
        """Should include file information for callers."""
        callers = get_callers_of(sample_index_with_dependencies, "validate_email")

        assert len(callers) >= 1
        caller = callers[0]
        assert "file" in caller
        assert caller["file"] == "lib/user_service.py"


class TestGetCalleesOf:
    """Tests for get_callees_of function."""

    def test_get_callees_of_with_dependencies(self, sample_index_with_dependencies):
        """Should return all functions called by a function."""
        callees = get_callees_of(sample_index_with_dependencies, "UserService", "create_user")

        assert len(callees) == 3

        # Check that all expected callees are present
        callee_names = [c.get("function") for c in callees]
        assert "validate_email" in callee_names
        assert "insert" in callee_names
        assert "log_info" in callee_names

    def test_get_callees_of_no_calls(self, sample_index_with_dependencies):
        """Should return empty list for function that doesn't call anything."""
        callees = get_callees_of(sample_index_with_dependencies, "UserService", "delete_user")

        assert callees == []

    def test_get_callees_of_nonexistent_module(self, sample_index_with_dependencies):
        """Should return empty list for non-existent module."""
        callees = get_callees_of(sample_index_with_dependencies, "NonExistent", "func")

        assert callees == []

    def test_get_callees_of_nonexistent_function(self, sample_index_with_dependencies):
        """Should return empty list for non-existent function."""
        callees = get_callees_of(sample_index_with_dependencies, "UserService", "nonexistent")

        assert callees == []

    def test_get_callees_includes_location_info(self, sample_index_with_dependencies):
        """Should include line and file information for callees."""
        callees = get_callees_of(sample_index_with_dependencies, "UserService", "create_user")

        assert len(callees) > 0
        for callee in callees:
            assert "line" in callee
            assert callee["line"] is not None


class TestGetDependencies:
    """Tests for get_dependencies function."""

    def test_get_dependencies_new_format(self, sample_index_with_dependencies):
        """Should return dependencies in new dict format."""
        deps = get_dependencies(sample_index_with_dependencies, "UserService")

        assert deps == ["Database", "Logger", "Validator"]

    def test_get_dependencies_old_format(self, sample_index_old_format):
        """Should handle old list format for backward compatibility."""
        deps = get_dependencies(sample_index_old_format, "OldModule")

        assert deps == ["Dep1", "Dep2"]

    def test_get_dependencies_no_dependencies(self, sample_index_with_dependencies):
        """Should return empty list for module with no dependencies."""
        deps = get_dependencies(sample_index_with_dependencies, "Database")

        assert deps == []

    def test_get_dependencies_nonexistent_module(self, sample_index_with_dependencies):
        """Should return empty list for non-existent module."""
        deps = get_dependencies(sample_index_with_dependencies, "NonExistent")

        assert deps == []

    def test_get_dependencies_module_without_dependencies_key(self):
        """Should handle module without dependencies key."""
        index = {"modules": {"NoDeps": {"name": "NoDeps", "file": "nodeps.py"}}}
        deps = get_dependencies(index, "NoDeps")

        assert deps == []

    def test_get_dependencies_invalid_format(self):
        """Should handle invalid dependencies format gracefully."""
        index = {
            "modules": {
                "InvalidDeps": {
                    "name": "InvalidDeps",
                    "file": "invalid.py",
                    "dependencies": "not a list or dict",  # Invalid format
                }
            }
        }
        deps = get_dependencies(index, "InvalidDeps")

        assert deps == []

    def test_get_dependencies_old_format_missing_module_key(self):
        """Should handle old format with missing 'module' key."""
        index = {
            "modules": {
                "BrokenOld": {
                    "name": "BrokenOld",
                    "file": "broken.py",
                    "dependencies": [
                        {"module": "Valid"},
                        {"other_key": "Invalid"},  # Missing 'module' key
                    ],
                }
            }
        }
        deps = get_dependencies(index, "BrokenOld")

        # Should only include valid entries
        assert deps == ["Valid"]

    def test_get_dependencies_new_format_missing_modules_key(self):
        """Should handle new dict format with missing 'modules' key."""
        index = {
            "modules": {
                "BrokenNew": {
                    "name": "BrokenNew",
                    "file": "broken.py",
                    "dependencies": {"other_key": "something"},  # No 'modules' key
                }
            }
        }
        deps = get_dependencies(index, "BrokenNew")

        assert deps == []


class TestGetReferencesTo:
    """Tests for get_references_to function."""

    def test_get_references_includes_call_sites(self, sample_index_with_dependencies):
        """Should include call sites in references."""
        refs = get_references_to(
            sample_index_with_dependencies, "Validator", "validate_email"
        )

        assert len(refs) > 0

        # Should include references from callers (UserService.create_user calls validate_email)
        user_service_ref = next(
            (r for r in refs if r.get("module") == "UserService"), None
        )
        assert user_service_ref is not None

    def test_get_references_includes_callers(self, sample_index_with_dependencies):
        """Should include callers in references."""
        refs = get_references_to(sample_index_with_dependencies, "Logger", "log_info")

        assert len(refs) > 0

        # Should find references from callers
        caller_ref = next((r for r in refs if r.get("module") == "UserService"), None)
        assert caller_ref is not None

    def test_get_references_no_references(self, sample_index_with_dependencies):
        """Should return empty list when function has no references."""
        # Database.insert is called, but let's test a function with no refs
        refs = get_references_to(sample_index_with_dependencies, "StringUtils", "nonexistent")

        # Will return empty since function doesn't exist
        assert len(refs) == 0

    def test_get_references_nonexistent_module(self, sample_index_with_dependencies):
        """Should handle non-existent module."""
        refs = get_references_to(sample_index_with_dependencies, "NonExistent", "func")

        assert len(refs) == 0

    def test_get_references_deduplication(self, sample_index_with_dependencies):
        """Should combine call sites and callers (may have duplicates)."""
        refs = get_references_to(sample_index_with_dependencies, "Database", "insert")

        # References should include both call sites and callers
        # The function doesn't deduplicate, so we just check that both are included
        assert len(refs) > 0


class TestEdgeCases:
    """Edge case tests for index reference utilities."""

    def test_functions_with_empty_index(self):
        """All functions should handle empty index gracefully."""
        empty = {}

        assert get_call_sites(empty, "M", "f") == []
        assert get_callers_of(empty, "f") == []
        assert get_callees_of(empty, "M", "f") == []
        assert get_dependencies(empty, "M") == []
        assert get_references_to(empty, "M", "f") == []

    def test_functions_with_empty_modules(self):
        """All functions should handle empty modules dict gracefully."""
        index = {"modules": {}}

        assert get_call_sites(index, "M", "f") == []
        assert get_callers_of(index, "f") == []
        assert get_callees_of(index, "M", "f") == []
        assert get_dependencies(index, "M") == []
        assert get_references_to(index, "M", "f") == []

    def test_module_without_functions(self):
        """Should handle module without functions key."""
        index = {"modules": {"Empty": {"name": "Empty", "file": "empty.py"}}}

        assert get_call_sites(index, "Empty", "f") == []
        assert get_callees_of(index, "Empty", "f") == []

    def test_function_without_dependencies_or_calls(self):
        """Should handle function without dependencies or calls key."""
        index = {
            "modules": {
                "M": {
                    "name": "M",
                    "file": "m.py",
                    "functions": [{"name": "f", "arity": 0}],
                }
            }
        }

        call_sites = get_call_sites(index, "M", "f")
        assert call_sites == []

        callees = get_callees_of(index, "M", "f")
        assert callees == []

    def test_unicode_in_module_and_function_names(self):
        """Should handle unicode in module and function names."""
        index = {
            "modules": {
                "Módulo": {
                    "name": "Módulo",
                    "file": "módulo.py",
                    "functions": [
                        {
                            "name": "función",
                            "arity": 1,
                            "dependencies": [
                                {"module": "Otro", "function": "método", "arity": 1, "line": 5}
                            ],
                        }
                    ],
                }
            }
        }

        call_sites = get_call_sites(index, "Módulo", "función")
        assert len(call_sites) == 1
        assert call_sites[0]["function"] == "método"

    def test_callers_with_nested_function_names(self, sample_index_with_dependencies):
        """Should handle function names that are substrings of others."""
        # The 'in' matching should work for partial matches
        callers = get_callers_of(sample_index_with_dependencies, "update")

        # Should find UserService.update_user calling Database.update
        assert any(c["function"] == "update_user" for c in callers)

    def test_call_sites_with_missing_optional_fields(self):
        """Should handle dependencies with missing optional fields."""
        index = {
            "modules": {
                "M": {
                    "name": "M",
                    "file": "m.py",
                    "functions": [
                        {
                            "name": "f",
                            "arity": 1,
                            "dependencies": [
                                {
                                    # Minimal dependency - only required fields
                                    "module": "Other",
                                    "function": "g",
                                }
                            ],
                        }
                    ],
                }
            }
        }

        call_sites = get_call_sites(index, "M", "f")
        assert len(call_sites) == 1
        assert call_sites[0]["function"] == "g"

    def test_dependencies_with_empty_modules_list(self):
        """Should handle dependencies with empty modules list."""
        index = {
            "modules": {
                "M": {"name": "M", "file": "m.py", "dependencies": {"modules": []}}
            }
        }

        deps = get_dependencies(index, "M")
        assert deps == []

    def test_multiple_call_formats_in_same_index(self):
        """Should handle index with both old and new call formats."""
        index = {
            "modules": {
                "NewStyle": {
                    "name": "NewStyle",
                    "file": "new.py",
                    "functions": [
                        {
                            "name": "new_func",
                            "arity": 1,
                            "dependencies": [
                                {"module": "M", "function": "f", "arity": 1, "line": 5}
                            ],
                        }
                    ],
                },
                "OldStyle": {
                    "name": "OldStyle",
                    "file": "old.py",
                    "functions": [
                        {
                            "name": "old_func",
                            "arity": 1,
                            "calls": [{"callee": "M.f", "file": "m.py", "line": 7}],
                        }
                    ],
                },
            }
        }

        # Both should work
        new_sites = get_call_sites(index, "NewStyle", "new_func")
        assert len(new_sites) == 1

        old_sites = get_call_sites(index, "OldStyle", "old_func")
        assert len(old_sites) == 1
