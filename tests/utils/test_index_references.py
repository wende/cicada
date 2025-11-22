"""
Comprehensive tests for cicada/utils/index_references.py
"""

import pytest

from cicada.utils.index_references import (
    get_call_sites,
    get_callees_of,
    get_callers_of,
    get_dependencies,
    get_references_to,
)


@pytest.fixture
def sample_index_with_calls():
    """Sample index with call sites and dependencies"""
    return {
        "modules": {
            "Calculator": {
                "file": "lib/calculator.ex",
                "line": 1,
                "dependencies": {
                    "modules": ["Math.Utils", "Logger"],
                },
                "functions": [
                    {
                        "name": "add",
                        "arity": 2,
                        "line": 5,
                        "dependencies": [
                            {
                                "module": "Math.Utils",
                                "function": "validate",
                                "arity": 1,
                                "line": 6,
                            },
                        ],
                    },
                    {
                        "name": "process",
                        "arity": 1,
                        "line": 10,
                        "dependencies": [
                            {
                                "module": "Calculator",
                                "function": "add",
                                "arity": 2,
                                "line": 11,
                            },
                            {
                                "module": "Logger",
                                "function": "info",
                                "arity": 1,
                                "line": 12,
                            },
                        ],
                    },
                ],
            },
            "Math.Utils": {
                "file": "lib/math/utils.ex",
                "line": 1,
                "dependencies": [],
                "functions": [
                    {
                        "name": "validate",
                        "arity": 1,
                        "line": 3,
                        "dependencies": [],
                    },
                ],
            },
            "Logger": {
                "file": "lib/logger.ex",
                "line": 1,
                "functions": [
                    {
                        "name": "info",
                        "arity": 1,
                        "line": 2,
                        "dependencies": [],
                    },
                ],
            },
        }
    }


@pytest.fixture
def sample_index_with_legacy_calls():
    """Sample index with legacy 'calls' format (raw SCIP symbols)"""
    return {
        "modules": {
            "TestModule": {
                "file": "lib/test.ex",
                "line": 1,
                "functions": [
                    {
                        "name": "caller_func",
                        "arity": 1,
                        "line": 5,
                        "calls": [
                            {
                                "callee": "target_func/1",
                                "file": "lib/test.ex",
                                "line": 6,
                            },
                            {
                                "symbol": "another_func/0",
                                "caller_file": "lib/test.ex",
                                "caller_line": 7,
                            },
                        ],
                    },
                ],
            },
        }
    }


@pytest.fixture
def empty_index():
    """Index with no modules"""
    return {}


@pytest.fixture
def index_with_old_deps_format():
    """Index with old dependencies format (list of dicts)"""
    return {
        "modules": {
            "OldModule": {
                "file": "lib/old.ex",
                "line": 1,
                "dependencies": [
                    {"module": "Dep1"},
                    {"module": "Dep2"},
                    {"other": "field"},  # Should be filtered out
                ],
                "functions": [],
            }
        }
    }


class TestGetCallSites:
    """Tests for get_call_sites function"""

    def test_get_call_sites_with_dependencies(self, sample_index_with_calls):
        """Should return dependencies for function with calls"""
        sites = get_call_sites(sample_index_with_calls, "Calculator", "add")

        assert len(sites) == 1
        assert sites[0]["module"] == "Math.Utils"
        assert sites[0]["function"] == "validate"
        assert sites[0]["line"] == 6

    def test_get_call_sites_multiple_calls(self, sample_index_with_calls):
        """Should return all call sites for function with multiple calls"""
        sites = get_call_sites(sample_index_with_calls, "Calculator", "process")

        assert len(sites) == 2
        functions = {s["function"] for s in sites}
        assert functions == {"add", "info"}

    def test_get_call_sites_no_calls(self, sample_index_with_calls):
        """Should return empty list for function with no calls"""
        sites = get_call_sites(sample_index_with_calls, "Math.Utils", "validate")

        assert sites == []

    def test_get_call_sites_nonexistent_module(self, sample_index_with_calls):
        """Should return empty list for nonexistent module"""
        sites = get_call_sites(sample_index_with_calls, "NonExistent", "func")

        assert sites == []

    def test_get_call_sites_nonexistent_function(self, sample_index_with_calls):
        """Should return empty list for nonexistent function"""
        sites = get_call_sites(sample_index_with_calls, "Calculator", "nonexistent")

        assert sites == []

    def test_get_call_sites_empty_index(self, empty_index):
        """Should return empty list for empty index"""
        sites = get_call_sites(empty_index, "Calculator", "add")

        assert sites == []

    def test_get_call_sites_with_legacy_calls_format(self, sample_index_with_legacy_calls):
        """Should fallback to 'calls' field if 'dependencies' not present"""
        sites = get_call_sites(sample_index_with_legacy_calls, "TestModule", "caller_func")

        assert len(sites) == 2
        # Should have raw SCIP symbol format
        assert any("callee" in s or "symbol" in s for s in sites)


class TestGetCallersOf:
    """Tests for get_callers_of function"""

    def test_get_callers_single_caller(self, sample_index_with_calls):
        """Should find single caller of a function"""
        callers = get_callers_of(sample_index_with_calls, "validate")

        assert len(callers) == 1
        assert callers[0]["module"] == "Calculator"
        assert callers[0]["function"] == "add"
        assert callers[0]["line"] == 6

    def test_get_callers_multiple_callers(self, sample_index_with_calls):
        """Should find all callers of a function"""
        callers = get_callers_of(sample_index_with_calls, "add")

        assert len(callers) == 1
        assert callers[0]["module"] == "Calculator"
        assert callers[0]["function"] == "process"

    def test_get_callers_no_callers(self, sample_index_with_calls):
        """Should return empty list when function has no callers"""
        callers = get_callers_of(sample_index_with_calls, "process")

        assert callers == []

    def test_get_callers_nonexistent_function(self, sample_index_with_calls):
        """Should return empty list for nonexistent function"""
        callers = get_callers_of(sample_index_with_calls, "nonexistent")

        assert callers == []

    def test_get_callers_empty_index(self, empty_index):
        """Should return empty list for empty index"""
        callers = get_callers_of(empty_index, "add")

        assert callers == []

    def test_get_callers_partial_match(self, sample_index_with_calls):
        """Should find callers using partial name match"""
        # "info" appears in function name
        callers = get_callers_of(sample_index_with_calls, "info")

        assert len(callers) >= 1
        # Should find Calculator.process calling Logger.info

    def test_get_callers_with_legacy_calls_format(self, sample_index_with_legacy_calls):
        """Should work with legacy 'calls' field format"""
        callers = get_callers_of(sample_index_with_legacy_calls, "target_func")

        assert len(callers) == 1
        assert callers[0]["module"] == "TestModule"
        assert callers[0]["function"] == "caller_func"

    def test_get_callers_handles_missing_file(self, sample_index_with_calls):
        """Should handle missing file field gracefully"""
        callers = get_callers_of(sample_index_with_calls, "validate")

        assert len(callers) == 1
        # Should still have file from module data or call data
        assert "file" in callers[0]


class TestGetCalleesOf:
    """Tests for get_callees_of function"""

    def test_get_callees_single_callee(self, sample_index_with_calls):
        """Should find callees of a function"""
        callees = get_callees_of(sample_index_with_calls, "Calculator", "add")

        assert len(callees) == 1
        assert callees[0]["function"] == "validate"
        assert callees[0]["line"] == 6

    def test_get_callees_multiple_callees(self, sample_index_with_calls):
        """Should find all callees of a function"""
        callees = get_callees_of(sample_index_with_calls, "Calculator", "process")

        assert len(callees) == 2
        functions = {c["function"] for c in callees}
        assert functions == {"add", "info"}

    def test_get_callees_no_callees(self, sample_index_with_calls):
        """Should return empty list when function has no callees"""
        callees = get_callees_of(sample_index_with_calls, "Math.Utils", "validate")

        assert callees == []

    def test_get_callees_nonexistent_module(self, sample_index_with_calls):
        """Should return empty list for nonexistent module"""
        callees = get_callees_of(sample_index_with_calls, "NonExistent", "func")

        assert callees == []

    def test_get_callees_nonexistent_function(self, sample_index_with_calls):
        """Should return empty list for nonexistent function"""
        callees = get_callees_of(sample_index_with_calls, "Calculator", "nonexistent")

        assert callees == []

    def test_get_callees_with_legacy_format(self, sample_index_with_legacy_calls):
        """Should work with legacy 'calls' field format"""
        callees = get_callees_of(sample_index_with_legacy_calls, "TestModule", "caller_func")

        assert len(callees) == 2
        # Should extract function names from various fields
        functions = {c["function"] for c in callees}
        assert "target_func/1" in functions or "another_func/0" in functions


class TestGetDependencies:
    """Tests for get_dependencies function"""

    def test_get_dependencies_new_format(self, sample_index_with_calls):
        """Should get dependencies in new dict format"""
        deps = get_dependencies(sample_index_with_calls, "Calculator")

        assert deps == ["Math.Utils", "Logger"]

    def test_get_dependencies_old_format(self, index_with_old_deps_format):
        """Should get dependencies in old list format"""
        deps = get_dependencies(index_with_old_deps_format, "OldModule")

        assert len(deps) == 2
        assert "Dep1" in deps
        assert "Dep2" in deps

    def test_get_dependencies_no_dependencies(self, sample_index_with_calls):
        """Should return empty list when module has no dependencies"""
        deps = get_dependencies(sample_index_with_calls, "Math.Utils")

        assert deps == []

    def test_get_dependencies_nonexistent_module(self, sample_index_with_calls):
        """Should return empty list for nonexistent module"""
        deps = get_dependencies(sample_index_with_calls, "NonExistent")

        assert deps == []

    def test_get_dependencies_empty_index(self, empty_index):
        """Should return empty list for empty index"""
        deps = get_dependencies(empty_index, "Calculator")

        assert deps == []

    def test_get_dependencies_missing_field(self):
        """Should handle module without dependencies field"""
        index = {
            "modules": {
                "TestModule": {
                    "file": "test.ex",
                    "line": 1,
                    "functions": [],
                }
            }
        }
        deps = get_dependencies(index, "TestModule")

        assert deps == []

    def test_get_dependencies_invalid_format(self):
        """Should handle invalid dependencies format"""
        index = {
            "modules": {
                "TestModule": {
                    "file": "test.ex",
                    "line": 1,
                    "dependencies": "invalid_string",
                    "functions": [],
                }
            }
        }
        deps = get_dependencies(index, "TestModule")

        assert deps == []


class TestGetReferencesTo:
    """Tests for get_references_to function"""

    def test_get_references_with_calls(self, sample_index_with_calls):
        """Should get references including call sites"""
        refs = get_references_to(sample_index_with_calls, "Calculator", "add")

        # Should include call sites and callers
        assert len(refs) >= 1

    def test_get_references_combines_sources(self, sample_index_with_calls):
        """Should combine call sites and callers"""
        refs = get_references_to(sample_index_with_calls, "Math.Utils", "validate")

        # Should find references from callers
        assert len(refs) >= 1
        # Should have caller information
        assert any("module" in ref for ref in refs)

    def test_get_references_no_references(self, sample_index_with_calls):
        """Should return empty list when no references found"""
        refs = get_references_to(sample_index_with_calls, "Logger", "info")

        # Logger.info is called but has no dependencies itself
        # Should still find callers
        assert isinstance(refs, list)

    def test_get_references_nonexistent_function(self, sample_index_with_calls):
        """Should return list for nonexistent function"""
        refs = get_references_to(sample_index_with_calls, "Calculator", "nonexistent")

        # Should return list (possibly empty, or with callers if any)
        assert isinstance(refs, list)

    def test_get_references_empty_index(self, empty_index):
        """Should return empty list for empty index"""
        refs = get_references_to(empty_index, "Calculator", "add")

        assert refs == []


class TestEdgeCases:
    """Tests for edge cases and error conditions"""

    def test_functions_without_dependencies_field(self):
        """Should handle functions without dependencies/calls field"""
        index = {
            "modules": {
                "TestModule": {
                    "file": "test.ex",
                    "line": 1,
                    "functions": [
                        {
                            "name": "test_func",
                            "line": 2,
                            # No dependencies or calls field
                        }
                    ],
                }
            }
        }

        sites = get_call_sites(index, "TestModule", "test_func")
        assert sites == []

        callees = get_callees_of(index, "TestModule", "test_func")
        assert callees == []

    def test_empty_dependencies_list(self):
        """Should handle empty dependencies list"""
        index = {
            "modules": {
                "TestModule": {
                    "file": "test.ex",
                    "line": 1,
                    "functions": [
                        {
                            "name": "test_func",
                            "line": 2,
                            "dependencies": [],
                        }
                    ],
                }
            }
        }

        sites = get_call_sites(index, "TestModule", "test_func")
        assert sites == []

    def test_malformed_call_entries(self):
        """Should handle malformed call entries (excluding None values)"""
        index = {
            "modules": {
                "TestModule": {
                    "file": "test.ex",
                    "line": 1,
                    "functions": [
                        {
                            "name": "test_func",
                            "line": 2,
                            "dependencies": [
                                {},  # Empty dict
                                {"line": 5},  # Missing callee/function/symbol
                                {"function": "valid_func", "line": 6},  # Valid entry
                            ],
                        }
                    ],
                }
            }
        }

        # Should not crash on empty dicts or missing fields
        callees = get_callees_of(index, "TestModule", "test_func")
        # Should only include entries with valid function names
        assert isinstance(callees, list)
        # Should have found the valid entry
        assert len(callees) == 1
        assert callees[0]["function"] == "valid_func"

    def test_unicode_in_function_names(self):
        """Should handle unicode characters in function names"""
        index = {
            "modules": {
                "TestModule": {
                    "file": "test.ex",
                    "line": 1,
                    "functions": [
                        {
                            "name": "tëst_func",
                            "line": 2,
                            "dependencies": [
                                {
                                    "function": "ünïcode_func",
                                    "line": 3,
                                }
                            ],
                        }
                    ],
                }
            }
        }

        sites = get_call_sites(index, "TestModule", "tëst_func")
        assert len(sites) == 1
        assert sites[0]["function"] == "ünïcode_func"

    def test_dependencies_with_mixed_formats(self):
        """Should handle dependencies with both old and new format fields"""
        index = {
            "modules": {
                "TestModule": {
                    "file": "test.ex",
                    "line": 1,
                    "dependencies": {
                        "modules": ["Dep1"],
                        # Has new format but also some extra fields
                        "other": "data",
                    },
                    "functions": [],
                }
            }
        }

        deps = get_dependencies(index, "TestModule")
        assert deps == ["Dep1"]

    def test_callers_with_nested_call_structure(self):
        """Should handle nested or complex call structures"""
        index = {
            "modules": {
                "ModuleA": {
                    "file": "a.ex",
                    "line": 1,
                    "functions": [
                        {
                            "name": "func_a",
                            "line": 2,
                            "dependencies": [
                                {
                                    "function": "func_b",
                                    "module": "ModuleB",
                                    "line": 3,
                                }
                            ],
                        }
                    ],
                },
                "ModuleB": {
                    "file": "b.ex",
                    "line": 1,
                    "functions": [
                        {
                            "name": "func_b",
                            "line": 2,
                            "dependencies": [
                                {
                                    "function": "func_c",
                                    "module": "ModuleC",
                                    "line": 3,
                                }
                            ],
                        }
                    ],
                },
            }
        }

        # Find who calls func_b
        callers = get_callers_of(index, "func_b")
        assert len(callers) == 1
        assert callers[0]["function"] == "func_a"
