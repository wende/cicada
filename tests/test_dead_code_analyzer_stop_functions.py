import pytest
from cicada.dead_code.analyzer import DeadCodeAnalyzer


def test_stop_functions_are_excluded():
    """Test that stop functions are excluded from dead code analysis."""
    index = {
        "modules": {
            "MyApp": {
                "file": "lib/my_app.py",
                "functions": [
                    # __init__: default stop function
                    {
                        "name": "__init__",
                        "arity": 1,
                        "line": 10,
                        "type": "public",
                        "dependencies": [],
                    },
                    # main: default stop function
                    {"name": "main", "arity": 0, "line": 20, "type": "public", "dependencies": []},
                    # unused_func: should be detected
                    {
                        "name": "unused_func",
                        "arity": 0,
                        "line": 30,
                        "type": "public",
                        "dependencies": [],
                    },
                    # used_func: simulated usage (will mock _find_usages if needed, or just trust logic)
                    # Actually, DeadCodeAnalyzer._find_usages uses the index.
                    # To simulate usage, we need another module calling it.
                ],
                "aliases": {},
                "dependencies": [],
                "value_mentions": [],
                "behaviours": [],
                "uses": [],
            },
            "Caller": {
                "file": "lib/caller.py",
                "functions": [
                    {
                        "name": "caller_func",
                        "arity": 0,
                        "line": 5,
                        "type": "public",
                        "dependencies": [
                            # Call to used_func
                            {"module": "MyApp", "function": "used_func", "arity": 0}
                        ],
                    }
                ],
                "aliases": {},
                "dependencies": [],
                "value_mentions": [],
                "behaviours": [],
                "uses": [],
            },
        }
    }

    # Add used_func to MyApp
    index["modules"]["MyApp"]["functions"].append(
        {"name": "used_func", "arity": 0, "line": 40, "type": "public", "dependencies": []}
    )

    analyzer = DeadCodeAnalyzer(index)

    # Verify default stop functions
    assert "__init__" in analyzer.stop_functions
    assert "main" in analyzer.stop_functions

    results = analyzer.analyze()
    candidates = results["candidates"]["high"]

    # Check candidate names
    candidate_names = [c["function"] for c in candidates]

    # unused_func should be there
    assert "unused_func" in candidate_names

    # __init__ and main should NOT be there (even though they have 0 usages)
    assert "__init__" not in candidate_names
    assert "main" not in candidate_names

    # used_func should NOT be there (it has usage)
    assert "used_func" not in candidate_names


def test_add_custom_stop_function():
    """Test adding a custom stop function."""
    index = {
        "modules": {
            "MyApp": {
                "file": "lib/my_app.py",
                "functions": [
                    {
                        "name": "custom_stop",
                        "arity": 0,
                        "line": 10,
                        "type": "public",
                        "dependencies": [],
                    },
                ],
                "aliases": {},
                "dependencies": [],
                "value_mentions": [],
                "behaviours": [],
                "uses": [],
            }
        }
    }

    analyzer = DeadCodeAnalyzer(index)
    analyzer.add_stop_function("custom_stop")

    assert "custom_stop" in analyzer.stop_functions

    results = analyzer.analyze()
    candidate_names = [c["function"] for c in results["candidates"]["high"]]

    assert "custom_stop" not in candidate_names
