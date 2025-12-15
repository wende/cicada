"""
Pytest configuration and fixtures for all tests.
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from .elixir_repo_factory import create_sample_elixir_repo


@pytest.fixture(autouse=True)
def patch_generic_indexing():
    """
    Prevent generic indexer from running during unit tests.
    Patches the function in all known usage locations.
    """
    mock_result = {
        "success": True,
        "modules_count": 0,
        "files_indexed": 0,
        "errors": [],
        "metadata": {},
    }

    targets = [
        "cicada.mcp.handlers.index_manager.run_generic_indexing_for_language_indexer",
        "cicada.commands.run_generic_indexing_for_language_indexer",
        "cicada.watcher.run_generic_indexing_for_language_indexer",
        "cicada.setup.run_generic_indexing_for_language_indexer",
    ]

    shared_mock = MagicMock(return_value=mock_result)

    patches = [patch(target, shared_mock) for target in targets]

    for p in patches:
        p.start()

    yield shared_mock

    for p in patches:
        p.stop()



@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Create test data files for tests that need them.
    This runs once per test session before any tests execute.
    """
    # Get the tests directory
    tests_dir = Path(__file__).parent

    # Create data directory for test files
    os.makedirs(tests_dir / "data", exist_ok=True)

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

    test_index_path = tests_dir / "data" / "test_index.json"
    with open(test_index_path, "w") as f:
        json.dump(test_index, f, indent=2)

    # Create config.yaml file (no longer includes index_path - uses centralized storage)
    config = {
        "repository": {"path": "."},
    }

    config_path = "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    yield

    # Cleanup happens after all tests complete
    # Note: Individual tests create their own index/config files in tmp_path


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


@pytest.fixture(autouse=True)
def mock_repo_hash(monkeypatch):
    """
    Mock get_repo_hash to return constant hashes for test fixtures.

    This prevents each test run from generating new random hashes based on
    tmp_path, which was causing 3+ new project index directories per test run.

    Only mocks hash for known fixture repos (elixir_repo). For other paths,
    uses the original hash function to maintain normal test behavior.

    The fixture is autouse=True, so it applies to all tests automatically.
    """
    from cicada.utils import storage

    original_get_repo_hash = storage.get_repo_hash

    def mock_hash(repo_path: str | Path) -> str:
        """Return constant hash for known fixtures, original hash for others."""
        repo_name = Path(repo_path).name
        # Only mock hash for known test fixtures that get reused across tests
        if repo_name == "elixir_repo":
            return "test_elixir_repo"
        # For all other paths, use the original hash function
        return original_get_repo_hash(repo_path)

    monkeypatch.setattr(storage, "get_repo_hash", mock_hash)

    return mock_hash


@pytest.fixture
def elixir_repo(tmp_path):
    """Provision a sample Elixir repository for watcher-related tests."""
    return create_sample_elixir_repo(tmp_path)


@pytest.fixture
def fixtures_dir():
    """
    Return the path to the test fixtures directory.

    This fixture can be used by all tests to access test fixtures
    without hardcoding relative paths.

    Usage:
        def test_something(fixtures_dir):
            sample_file = fixtures_dir / "sample.ex"
    """
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def git_bundle_repo(tmp_path, fixtures_dir):
    """
    Clone git bundle into isolated tmp_path for each test.

    Provides parallel-safe git repository with known co-change patterns.
    Tests using this fixture are automatically grouped to run serially
    via xdist_group marker to prevent git index corruption.

    Contains 11 commits with strategic co-change patterns:
    - lib/auth.ex + lib/credentials.ex: 4 co-changes
    - lib/auth.ex + lib/logger.ex: 2 co-changes
    - Single-file commits for edge case testing
    - Rename scenario: old_name.ex -> new_name.ex
    - Function-level co-changes: ModuleA.func_one <-> ModuleB.func_three
    - Date-stamped commits for filtering tests

    Usage:
        def test_something(git_bundle_repo):
            analyzer = CoChangeAnalyzer()
            result = analyzer.analyze_repository(str(git_bundle_repo))
    """
    import subprocess

    bundle_path = fixtures_dir / "cochange_test_repo.bundle"

    if not bundle_path.exists():
        pytest.fail(
            f"Git bundle not found at {bundle_path}. "
            "Run: tests/fixtures/create_cochange_bundle.sh"
        )

    repo_path = tmp_path / "test_repo"

    # Clear git environment variables to prevent clone from affecting parent repo
    # This is critical when running in a git worktree
    clean_env = os.environ.copy()
    for var in ["GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY"]:
        clean_env.pop(var, None)

    subprocess.run(
        ["git", "clone", str(bundle_path), str(repo_path)],
        check=True,
        capture_output=True,
        timeout=10,
        env=clean_env,
    )

    return repo_path


def pytest_collection_modifyitems(items):
    """
    Automatically mark certain tests to run in same xdist group.

    This prevents issues when multiple workers run tests that share state
    or resources during parallel test execution.
    """
    for item in items:
        # Check if this test uses the git_bundle_repo fixture
        if "git_bundle_repo" in getattr(item, "fixturenames", []):
            # Add xdist_group marker to run all such tests in the same worker
            item.add_marker(pytest.mark.xdist_group(name="git_bundle_serial"))

        # Group all incremental indexing and keyword extraction tests to run serially
        # These tests have shared state issues (keyword extractor global state)
        # when run in parallel
        if "incremental" in item.name.lower() or "keyword" in item.name.lower():
            item.add_marker(pytest.mark.xdist_group(name="indexer_serial"))

        # Also group tests in test_keybert.py (they all use the keyword extractor)
        if "test_keybert" in str(item.fspath):
            item.add_marker(pytest.mark.xdist_group(name="indexer_serial"))
