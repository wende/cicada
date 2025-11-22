"""
Tests for cicada/utils/index_references.py
"""

import pytest
from cicada.utils.index_references import (
    get_call_sites,
    get_callers_of,
    get_callees_of,
    get_dependencies,
    get_references_to,
)


@pytest.fixture
def sample_index():
    """Sample index for testing reference functions."""
    return {
        "modules": {
            "App.Caller": {
                "file": "lib/app/caller.ex",
                "functions": [
                    {
                        "name": "do_work",
                        "calls": [
                            # SCIP format (simplified)
                            {
                                "callee": "App.Worker.perform",
                                "file": "lib/app/caller.ex",
                                "line": 10
                            },
                            {
                                "callee": "App.Helper.assist",
                                "file": "lib/app/caller.ex",
                                "line": 12
                            }
                        ]
                    }
                ],
                "dependencies": {
                    "modules": ["App.Worker", "App.Helper"]
                }
            },
            "App.Worker": {
                "file": "lib/app/worker.ex",
                "functions": [
                    {
                        "name": "perform",
                        "calls": []
                    }
                ],
                "dependencies": {
                    "modules": []
                }
            },
            "App.Legacy": {
                "file": "lib/app/legacy.ex",
                "functions": [],
                "dependencies": [
                    {"module": "App.OldDep"},
                    {"other": "stuff"}
                ]
            },
            "App.User": {
                "file": "lib/app/user.ex",
                "functions": [
                     {
                        "name": "complex_call",
                        "dependencies": [
                             # Alternative format found in code
                             {
                                 "function": "App.Worker.perform",
                                 "line": 20,
                                 "arity": 1
                             }
                        ]
                     }
                ]
            }
        }
    }


class TestGetCallSites:
    """Tests for get_call_sites function."""

    def test_get_call_sites_existing(self, sample_index):
        """Test getting call sites for a function with calls."""
        sites = get_call_sites(sample_index, "App.Caller", "do_work")
        assert len(sites) == 2
        assert sites[0]["callee"] == "App.Worker.perform"

    def test_get_call_sites_with_dependencies_field(self, sample_index):
        """Test getting call sites using 'dependencies' field inside function."""
        sites = get_call_sites(sample_index, "App.User", "complex_call")
        assert len(sites) == 1
        assert sites[0]["function"] == "App.Worker.perform"

    def test_get_call_sites_empty(self, sample_index):
        """Test getting call sites for function with no calls."""
        sites = get_call_sites(sample_index, "App.Worker", "perform")
        assert sites == []

    def test_get_call_sites_nonexistent_module(self, sample_index):
        """Test getting call sites for non-existent module."""
        sites = get_call_sites(sample_index, "NonExistent", "func")
        assert sites == []

    def test_get_call_sites_nonexistent_function(self, sample_index):
        """Test getting call sites for non-existent function."""
        sites = get_call_sites(sample_index, "App.Caller", "missing")
        assert sites == []


class TestGetCallersOf:
    """Tests for get_callers_of function."""

    def test_get_callers_found(self, sample_index):
        """Test finding callers of a function."""
        callers = get_callers_of(sample_index, "App.Worker.perform")
        assert len(callers) == 2

        modules = {c["module"] for c in callers}
        assert "App.Caller" in modules
        assert "App.User" in modules

        functions = {c["function"] for c in callers}
        assert "do_work" in functions
        assert "complex_call" in functions

    def test_get_callers_not_found(self, sample_index):
        """Test finding callers for unused function."""
        callers = get_callers_of(sample_index, "UnusedFunction")
        assert callers == []

    def test_get_callers_empty_index(self):
        """Test finding callers in empty index."""
        callers = get_callers_of({}, "func")
        assert callers == []


class TestGetCalleesOf:
    """Tests for get_callees_of function."""

    def test_get_callees_found(self, sample_index):
        """Test finding callees of a function."""
        callees = get_callees_of(sample_index, "App.Caller", "do_work")
        assert len(callees) == 2

        names = {c["function"] for c in callees}
        assert "App.Worker.perform" in names
        assert "App.Helper.assist" in names

        for callee in callees:
            assert "line" in callee
            assert "file" in callee

    def test_get_callees_empty(self, sample_index):
        """Test finding callees for function that calls nothing."""
        callees = get_callees_of(sample_index, "App.Worker", "perform")
        assert callees == []

    def test_get_callees_missing_name(self, sample_index):
        """Test finding callees when call entry misses name info."""
        # Inject malformed call
        sample_index["modules"]["App.Caller"]["functions"][0]["calls"].append(
            {"file": "unknown", "line": 99}
        )
        callees = get_callees_of(sample_index, "App.Caller", "do_work")
        # Should ignore the malformed one and return the 2 valid ones
        assert len(callees) == 2


class TestGetDependencies:
    """Tests for get_dependencies function."""

    def test_get_deps_new_format(self, sample_index):
        """Test getting dependencies with new dict format."""
        deps = get_dependencies(sample_index, "App.Caller")
        assert len(deps) == 2
        assert "App.Worker" in deps
        assert "App.Helper" in deps

    def test_get_deps_old_format(self, sample_index):
        """Test getting dependencies with old list format."""
        deps = get_dependencies(sample_index, "App.Legacy")
        assert len(deps) == 1
        assert "App.OldDep" in deps

    def test_get_deps_nonexistent_module(self, sample_index):
        """Test getting dependencies for non-existent module."""
        deps = get_dependencies(sample_index, "NonExistent")
        assert deps == []

    def test_get_deps_invalid_format(self, sample_index):
        """Test dependencies with invalid format."""
        # Inject invalid dependency format
        sample_index["modules"]["Invalid"] = {"dependencies": "string"}
        deps = get_dependencies(sample_index, "Invalid")
        assert deps == []


class TestGetReferencesTo:
    """Tests for get_references_to function."""

    def test_get_references(self, sample_index):
        """Test getting references (combined callers and calls)."""
        # In this case, we look for references to "perform"
        # Since get_references_to calls get_call_sites(index, module, func)
        # AND get_callers_of(index, func)
        # If we pass "App.Worker" and "perform", we get call sites OF perform (0)
        # plus callers OF perform (2)

        refs = get_references_to(sample_index, "App.Worker", "perform")
        assert len(refs) == 2  # 2 callers

        # One is from App.Caller.do_work
        assert any(r.get("module") == "App.Caller" and r.get("function") == "do_work" for r in refs)
        # One is from App.User.complex_call
        assert any(r.get("module") == "App.User" and r.get("function") == "complex_call" for r in refs)
