"""Tests for dead code analyzer functionality.

Author: Cursor(Auto)
"""

import pytest

from cicada.dead_code.analyzer import DeadCodeAnalyzer
from cicada.utils.path_utils import is_test_file


@pytest.fixture
def sample_index():
    """Create a sample index for testing."""
    return {
        "modules": {
            "MyApp.UserController": {
                "file": "lib/my_app/user_controller.ex",
                "functions": [
                    {
                        "name": "index",
                        "arity": 2,
                        "type": "def",
                        "line": 10,
                        "signature": "def index(conn, _params)",
                        "impl": False,
                    },
                    {
                        "name": "show",
                        "arity": 2,
                        "type": "def",
                        "line": 20,
                        "signature": "def show(conn, %{id: id})",
                        "impl": False,
                    },
                    {
                        "name": "helper",
                        "arity": 1,
                        "type": "defp",
                        "line": 30,
                    },
                ],
                "aliases": {},
                "imports": [],
                "requires": [],
                "uses": [],
                "behaviours": [],
                "value_mentions": [],
                "calls": [{"function": "show", "arity": 2, "module": None, "line": 25}],
            },
            "MyApp.UserService": {
                "file": "lib/my_app/user_service.ex",
                "functions": [
                    {
                        "name": "get_user",
                        "arity": 1,
                        "type": "def",
                        "line": 10,
                        "impl": False,
                    },
                    {
                        "name": "delete_user",
                        "arity": 1,
                        "type": "def",
                        "line": 20,
                        "impl": False,
                    },
                ],
                "aliases": {},
                "imports": [],
                "requires": [],
                "uses": [],
                "behaviours": [],
                "value_mentions": [],
                "calls": [],
            },
            "MyApp.GenServerImpl": {
                "file": "lib/my_app/gen_server_impl.ex",
                "functions": [
                    {
                        "name": "init",
                        "arity": 1,
                        "type": "def",
                        "line": 10,
                        "impl": True,
                    },
                    {
                        "name": "handle_call",
                        "arity": 3,
                        "type": "def",
                        "line": 20,
                        "impl": "GenServer",
                    },
                ],
                "aliases": {},
                "imports": [],
                "requires": [],
                "uses": ["GenServer"],
                "behaviours": ["GenServer"],
                "value_mentions": [],
                "calls": [],
            },
            "MyApp.DynamicModule": {
                "file": "lib/my_app/dynamic_module.ex",
                "functions": [
                    {
                        "name": "dynamic_func",
                        "arity": 1,
                        "type": "def",
                        "line": 10,
                        "impl": False,
                    },
                ],
                "aliases": {},
                "imports": [],
                "requires": [],
                "uses": [],
                "behaviours": [],
                "value_mentions": [],
                "calls": [],
            },
            "MyApp.Router": {
                "file": "lib/my_app/router.ex",
                "functions": [],
                "aliases": {},
                "imports": [],
                "requires": [],
                "uses": [],
                "behaviours": [],
                "value_mentions": ["MyApp.DynamicModule"],
                "calls": [],
            },
            "MyApp.TestHelper": {
                "file": "test/support/test_helper.ex",
                "functions": [
                    {
                        "name": "setup_test",
                        "arity": 0,
                        "type": "def",
                        "line": 5,
                        "impl": False,
                    },
                ],
                "aliases": {},
                "imports": [],
                "requires": [],
                "uses": [],
                "behaviours": [],
                "value_mentions": [],
                "calls": [],
            },
        }
    }


def test_analyzer_initialization(sample_index):
    """Test analyzer is initialized with index."""
    analyzer = DeadCodeAnalyzer(sample_index)
    assert analyzer.index == sample_index
    assert analyzer.modules == sample_index["modules"]


def test_find_unused_functions(sample_index):
    """Test finding unused public functions."""
    analyzer = DeadCodeAnalyzer(sample_index)
    results = analyzer.analyze()

    # Check summary
    assert "summary" in results
    assert "candidates" in results

    # Should find index (unused) but not show (called locally)
    high_confidence = results["candidates"]["high"]
    function_names = [c["function"] for c in high_confidence]

    assert "index" in function_names
    assert "show" not in function_names  # show is called

    # Should find unused functions in UserService
    assert "get_user" in function_names
    assert "delete_user" in function_names


def test_skip_impl_functions(sample_index):
    """Test that @impl functions are skipped."""
    analyzer = DeadCodeAnalyzer(sample_index)
    results = analyzer.analyze()

    # Check that impl functions are not in candidates
    all_candidates = (
        results["candidates"]["high"]
        + results["candidates"]["medium"]
        + results["candidates"]["low"]
    )
    candidate_functions = [(c["module"], c["function"]) for c in all_candidates]

    assert ("MyApp.GenServerImpl", "init") not in candidate_functions
    assert ("MyApp.GenServerImpl", "handle_call") not in candidate_functions

    # Check summary shows skipped impl functions
    assert results["summary"]["skipped_impl"] == 2


def test_skip_private_functions(sample_index):
    """Test that private functions (defp) are not analyzed."""
    analyzer = DeadCodeAnalyzer(sample_index)
    results = analyzer.analyze()

    # helper is a defp, should not appear anywhere
    all_candidates = (
        results["candidates"]["high"]
        + results["candidates"]["medium"]
        + results["candidates"]["low"]
    )
    function_names = [c["function"] for c in all_candidates]

    assert "helper" not in function_names


def test_skip_test_files(sample_index):
    """Test that test files are skipped."""
    analyzer = DeadCodeAnalyzer(sample_index)
    results = analyzer.analyze()

    # setup_test is in test file, should not appear
    all_candidates = (
        results["candidates"]["high"]
        + results["candidates"]["medium"]
        + results["candidates"]["low"]
    )
    candidate_functions = [(c["module"], c["function"]) for c in all_candidates]

    assert ("MyApp.TestHelper", "setup_test") not in candidate_functions

    # Check summary
    assert results["summary"]["skipped_files"] == 1


def test_is_test_file():
    """Test test file detection with universal patterns."""
    # Test directory patterns (universal)
    assert is_test_file("test/my_test.ex")
    assert is_test_file("tests/test_user.py")
    assert is_test_file("lib/my_app/test/helper.ex")

    # Test file naming patterns (universal)
    assert is_test_file("lib/my_module_test.ex")  # *_test.* pattern
    assert is_test_file("tests/test_calculator.py")  # test_*.* pattern

    # Non-test files
    assert not is_test_file("lib/my_app/module.ex")
    assert not is_test_file("lib/controllers/user.ex")
    assert not is_test_file("config/config.exs")  # Not a test file (config)
    assert not is_test_file("mix.exs")  # Not a test file (build script)


def test_medium_confidence_with_behaviours(sample_index):
    """Test medium confidence for modules with behaviours."""
    analyzer = DeadCodeAnalyzer(sample_index)
    results = analyzer.analyze()

    # Modules with behaviours but unused functions should be medium confidence
    # But in our fixture, GenServerImpl functions all have @impl, so they're skipped
    # We need to test with a different scenario

    # Add a function without @impl in a module with behaviour
    sample_index["modules"]["MyApp.GenServerImpl"]["functions"].append(
        {
            "name": "extra_func",
            "arity": 0,
            "type": "def",
            "line": 30,
            "impl": False,
        }
    )

    analyzer = DeadCodeAnalyzer(sample_index)
    results = analyzer.analyze()

    medium_candidates = results["candidates"]["medium"]
    candidate_functions = [(c["module"], c["function"]) for c in medium_candidates]

    assert ("MyApp.GenServerImpl", "extra_func") in candidate_functions


def test_low_confidence_with_value_mentions(sample_index):
    """Test low confidence for modules mentioned as values."""
    analyzer = DeadCodeAnalyzer(sample_index)
    results = analyzer.analyze()

    # dynamic_func should be low confidence because module is mentioned as value
    low_candidates = results["candidates"]["low"]
    candidate_functions = [(c["module"], c["function"]) for c in low_candidates]

    assert ("MyApp.DynamicModule", "dynamic_func") in candidate_functions

    # Check that it includes mentioned_in info
    dynamic_candidate = next(c for c in low_candidates if c["function"] == "dynamic_func")
    assert "mentioned_in" in dynamic_candidate
    assert len(dynamic_candidate["mentioned_in"]) > 0


def test_find_usages_with_aliases():
    """Test finding function usages with alias resolution."""
    index = {
        "modules": {
            "MyApp.UserService": {
                "file": "lib/user_service.ex",
                "functions": [
                    {
                        "name": "get_user",
                        "arity": 1,
                        "type": "def",
                        "line": 10,
                        "impl": False,
                    }
                ],
                "aliases": {},
                "calls": [],
                "uses": [],
                "behaviours": [],
                "value_mentions": [],
            },
            "MyApp.UserController": {
                "file": "lib/user_controller.ex",
                "functions": [],
                "aliases": {"UserService": "MyApp.UserService"},
                "calls": [
                    {
                        "function": "get_user",
                        "arity": 1,
                        "module": "UserService",
                        "line": 20,
                    }
                ],
                "uses": [],
                "behaviours": [],
                "value_mentions": [],
            },
        }
    }

    analyzer = DeadCodeAnalyzer(index)
    count = analyzer._find_usages("MyApp.UserService", "get_user", 1)
    assert count == 1


def test_find_usages_local_calls():
    """Test finding local function calls."""
    index = {
        "modules": {
            "MyApp.Math": {
                "file": "lib/math.ex",
                "functions": [
                    {
                        "name": "add",
                        "arity": 2,
                        "type": "def",
                        "line": 10,
                        "impl": False,
                    },
                    {
                        "name": "sum_list",
                        "arity": 1,
                        "type": "def",
                        "line": 20,
                        "impl": False,
                    },
                ],
                "aliases": {},
                "calls": [{"function": "add", "arity": 2, "module": None, "line": 22}],
                "uses": [],
                "behaviours": [],
                "value_mentions": [],
            },
        }
    }

    analyzer = DeadCodeAnalyzer(index)

    # add is called locally
    count = analyzer._find_usages("MyApp.Math", "add", 2)
    assert count == 1

    # sum_list is not called
    count = analyzer._find_usages("MyApp.Math", "sum_list", 1)
    assert count == 0


def test_filter_spec_and_doc_calls():
    """Test that @spec and @doc calls are filtered out."""
    index = {
        "modules": {
            "MyApp.Math": {
                "file": "lib/math.ex",
                "functions": [
                    {
                        "name": "add",
                        "arity": 2,
                        "type": "def",
                        "line": 10,
                        "impl": False,
                    },
                ],
                "aliases": {},
                "calls": [
                    # Call in @spec (line 8, 2 lines before def at line 10)
                    {"function": "add", "arity": 2, "module": None, "line": 8},
                    # Real call (line 50, far after def)
                    {"function": "add", "arity": 2, "module": None, "line": 50},
                ],
                "uses": [],
                "behaviours": [],
                "value_mentions": [],
            },
        }
    }

    analyzer = DeadCodeAnalyzer(index)
    count = analyzer._find_usages("MyApp.Math", "add", 2)

    # Should only count the real call, not the @spec one
    assert count == 1


def test_is_module_used_as_value():
    """Test checking if module is used as a value."""
    index = {
        "modules": {
            "MyApp.Handler": {"value_mentions": [], "uses": [], "behaviours": []},
            "MyApp.Router": {
                "value_mentions": ["MyApp.Handler"],
                "uses": [],
                "behaviours": [],
            },
        }
    }

    analyzer = DeadCodeAnalyzer(index)
    assert analyzer._is_module_used_as_value("MyApp.Handler")
    assert not analyzer._is_module_used_as_value("MyApp.Router")


def test_find_value_mentioners():
    """Test finding modules that mention a module as value."""
    index = {
        "modules": {
            "MyApp.Handler": {
                "file": "lib/handler.ex",
                "value_mentions": [],
                "uses": [],
                "behaviours": [],
            },
            "MyApp.Router": {
                "file": "lib/router.ex",
                "value_mentions": ["MyApp.Handler"],
                "uses": [],
                "behaviours": [],
            },
            "MyApp.Controller": {
                "file": "lib/controller.ex",
                "value_mentions": ["MyApp.Handler"],
                "uses": [],
                "behaviours": [],
            },
        }
    }

    analyzer = DeadCodeAnalyzer(index)
    mentioners = analyzer._find_value_mentioners("MyApp.Handler")

    assert len(mentioners) == 2
    modules = [m["module"] for m in mentioners]
    assert "MyApp.Router" in modules
    assert "MyApp.Controller" in modules


def test_calculate_confidence_high():
    """Test high confidence calculation."""
    analyzer = DeadCodeAnalyzer({"modules": {}})
    module_data = {
        "uses": [],
        "behaviours": [],
    }

    confidence = analyzer._calculate_confidence("MyApp.SimpleModule", module_data)
    assert confidence == "high"


def test_calculate_confidence_medium_with_behaviour():
    """Test medium confidence with behaviour."""
    index = {
        "modules": {
            "MyApp.GenServer": {"value_mentions": [], "uses": [], "behaviours": []},
        }
    }
    analyzer = DeadCodeAnalyzer(index)
    module_data = {
        "uses": [],
        "behaviours": ["GenServer"],
    }

    confidence = analyzer._calculate_confidence("MyApp.GenServer", module_data)
    assert confidence == "medium"


def test_calculate_confidence_medium_with_use():
    """Test medium confidence with use."""
    index = {
        "modules": {
            "MyApp.Controller": {"value_mentions": [], "uses": [], "behaviours": []},
        }
    }
    analyzer = DeadCodeAnalyzer(index)
    module_data = {
        "uses": ["Phoenix.Controller"],
        "behaviours": [],
    }

    confidence = analyzer._calculate_confidence("MyApp.Controller", module_data)
    assert confidence == "medium"


def test_calculate_confidence_low_with_value_mention():
    """Test low confidence when module is mentioned as value."""
    index = {
        "modules": {
            "MyApp.Handler": {"value_mentions": [], "uses": [], "behaviours": []},
            "MyApp.Router": {
                "value_mentions": ["MyApp.Handler"],
                "uses": [],
                "behaviours": [],
            },
        }
    }
    analyzer = DeadCodeAnalyzer(index)
    module_data = {
        "uses": [],
        "behaviours": [],
    }

    confidence = analyzer._calculate_confidence("MyApp.Handler", module_data)
    assert confidence == "low"


def test_summary_statistics(sample_index):
    """Test that summary statistics are calculated correctly."""
    analyzer = DeadCodeAnalyzer(sample_index)
    results = analyzer.analyze()

    summary = results["summary"]

    # Check all fields exist
    assert "total_public_functions" in summary
    assert "analyzed" in summary
    assert "skipped_impl" in summary
    assert "skipped_files" in summary
    assert "total_candidates" in summary

    # Verify counts
    assert summary["total_public_functions"] > 0
    assert summary["analyzed"] <= summary["total_public_functions"]
    assert summary["total_candidates"] >= 0


def test_candidate_structure(sample_index):
    """Test that candidates have correct structure."""
    analyzer = DeadCodeAnalyzer(sample_index)
    results = analyzer.analyze()

    # Check all confidence levels exist
    assert "high" in results["candidates"]
    assert "medium" in results["candidates"]
    assert "low" in results["candidates"]

    # Check structure of candidates
    for level in ["high", "medium", "low"]:
        for candidate in results["candidates"][level]:
            assert "module" in candidate
            assert "function" in candidate
            assert "arity" in candidate
            assert "line" in candidate
            assert "file" in candidate
            assert "reason" in candidate


def test_scip_dependencies_dict_format():
    """Test that analyzer handles new SCIP dependencies dict format.

    SCIP converter outputs dependencies as:
    {"modules": ["module1", "module2"], "has_dynamic_calls": False}

    This test ensures the analyzer doesn't crash and can still find usages
    via function-level dependencies.
    """
    index = {
        "modules": {
            "cicada.utils.storage": {
                "file": "cicada/utils/storage.py",
                "line": 1,
                "functions": [
                    {
                        "name": "get_repo_hash",
                        "arity": 1,
                        "type": "public",
                        "line": 10,
                        "signature": "def get_repo_hash(repo_path: str) -> str",
                        "impl": False,
                    }
                ],
                # New SCIP format: dict with modules list
                "dependencies": {"modules": ["pathlib", "hashlib"], "has_dynamic_calls": False},
                "aliases": {},
                "calls": [],
                "uses": [],
                "behaviours": [],
                "value_mentions": [],
            },
            "cicada.indexer": {
                "file": "cicada/indexer.py",
                "line": 1,
                "functions": [
                    {
                        "name": "index_repository",
                        "arity": 2,
                        "type": "public",
                        "line": 50,
                        "signature": "def index_repository(repo_path: str, output: str) -> None",
                        "impl": False,
                        # Function-level dependencies (still list of dicts)
                        "dependencies": [
                            {
                                "module": "`cicada.utils.storage`",
                                "function": "get_repo_hash",
                                "arity": 1,
                                "line": 55,
                            }
                        ],
                    }
                ],
                # New SCIP format: dict with modules list
                "dependencies": {
                    "modules": ["cicada.utils.storage", "pathlib"],
                    "has_dynamic_calls": False,
                },
                "aliases": {},
                "calls": [],
                "uses": [],
                "behaviours": [],
                "value_mentions": [],
            },
        }
    }

    analyzer = DeadCodeAnalyzer(index)

    # Should not crash when processing new dict format
    results = analyzer.analyze()

    # get_repo_hash should NOT be a dead code candidate because it's used in index_repository
    all_candidates = (
        results["candidates"]["high"]
        + results["candidates"]["medium"]
        + results["candidates"]["low"]
    )
    candidate_functions = [(c["module"], c["function"]) for c in all_candidates]

    assert ("cicada.utils.storage", "get_repo_hash") not in candidate_functions


def test_old_elixir_dependencies_list_format():
    """Test that analyzer still handles old Elixir dependencies list format.

    Old Elixir format:
    dependencies: [{"module": "Ecto", "function": "put_change", "arity": 3, "line": 42}]

    This ensures backward compatibility with existing Elixir indexes.
    """
    index = {
        "modules": {
            "MyApp.UserService": {
                "file": "lib/my_app/user_service.ex",
                "functions": [
                    {
                        "name": "create_user",
                        "arity": 1,
                        "type": "def",
                        "line": 10,
                        "impl": False,
                    }
                ],
                # Old Elixir format: list of dependency dicts
                "dependencies": [
                    {"module": "Ecto.Changeset", "function": "cast", "arity": 3, "line": 12},
                    {"module": "MyApp.Auth", "function": "hash_password", "arity": 1, "line": 13},
                ],
                "aliases": {},
                "calls": [],
                "uses": [],
                "behaviours": [],
                "value_mentions": [],
            },
            "MyApp.Auth": {
                "file": "lib/my_app/auth.ex",
                "functions": [
                    {
                        "name": "hash_password",
                        "arity": 1,
                        "type": "def",
                        "line": 5,
                        "impl": False,
                    }
                ],
                "dependencies": [],
                "aliases": {},
                "calls": [],
                "uses": [],
                "behaviours": [],
                "value_mentions": [],
            },
        }
    }

    analyzer = DeadCodeAnalyzer(index)
    results = analyzer.analyze()

    # hash_password should NOT be a dead code candidate because it's in dependencies
    all_candidates = (
        results["candidates"]["high"]
        + results["candidates"]["medium"]
        + results["candidates"]["low"]
    )
    candidate_functions = [(c["module"], c["function"]) for c in all_candidates]

    assert ("MyApp.Auth", "hash_password") not in candidate_functions
