"""
Pytest configuration and fixtures for all tests.
"""

import json
import os
from pathlib import Path

import pytest
import yaml


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Create minimal index and config files for tests that need them.
    This runs once per test session before any tests execute.
    """
    # Create .cicada directory if it doesn't exist
    os.makedirs(".cicada", exist_ok=True)
    os.makedirs("data", exist_ok=True)

    # Create minimal index
    minimal_index = {"modules": {}, "metadata": {"total_modules": 0, "repo_path": "."}}

    index_path = ".cicada/index.json"
    with open(index_path, "w") as f:
        json.dump(minimal_index, f)

    # Generate test index with sample data for tests
    test_index = {
        "modules": {
            "MyApp.User": {
                "file": "lib/my_app/user.ex",
                "line": 1,
                "moduledoc": "User management module",
                "functions": [
                    {
                        "name": "create_user",
                        "arity": 2,
                        "line": 42,
                        "type": "def",
                        "signature": "create_user(attrs, opts)",
                        "doc": "Creates a new user",
                    },
                    {
                        "name": "validate_email",
                        "arity": 1,
                        "line": 100,
                        "type": "defp",
                        "signature": "validate_email(email)",
                        "doc": "Validates email format",
                    },
                ],
                "calls": [
                    {
                        "module": None,
                        "function": "validate_email",
                        "arity": 1,
                        "line": 45,
                    }
                ],
                "aliases": {},
            },
            "MyApp.UserController": {
                "file": "lib/my_app_web/controllers/user_controller.ex",
                "line": 1,
                "functions": [
                    {
                        "name": "create",
                        "arity": 2,
                        "line": 20,
                        "type": "def",
                        "signature": "create(conn, params)",
                    }
                ],
                "calls": [
                    {
                        "module": "User",
                        "function": "create_user",
                        "arity": 2,
                        "line": 23,
                    }
                ],
                "aliases": {"User": "MyApp.User"},
            },
            "MyAppTest.UserTest": {
                "file": "test/my_app/user_test.exs",
                "line": 1,
                "functions": [{"name": "test_create_user", "arity": 1, "line": 10, "type": "def"}],
                "calls": [
                    {
                        "module": "User",
                        "function": "create_user",
                        "arity": 2,
                        "line": 12,
                    }
                ],
                "aliases": {"User": "MyApp.User"},
            },
        },
        "metadata": {"total_modules": 3, "repo_path": "."},
    }

    test_index_path = "data/test_index.json"
    with open(test_index_path, "w") as f:
        json.dump(test_index, f, indent=2)

    # Create config.yaml file
    config = {
        "repository": {"path": "."},
        "storage": {"index_path": ".cicada/index.json"},
    }

    config_path = "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    yield

    # Cleanup happens after all tests complete
    # Note: Individual tests may create their own index/config files,
    # but we don't clean up the main ones as they're needed by multiple tests


@pytest.fixture(autouse=True)
def mock_home_dir(tmp_path, monkeypatch):
    """
    Automatically mock Path.home() for all tests to use a temporary directory.

    This prevents tests from creating directories in the real ~/.cicada/projects/
    directory, which was causing thousands of test directories to accumulate.

    The fixture is autouse=True, so it applies to all tests automatically.
    """
    # Create a mock home directory in the temporary path
    mock_home = tmp_path / "mock_home"
    mock_home.mkdir()

    # Mock Path.home() to return our temporary directory
    monkeypatch.setattr(Path, "home", lambda: mock_home)

    return mock_home
