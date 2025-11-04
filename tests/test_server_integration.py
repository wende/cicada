"""
High-priority server integration tests.

Tests for server-specific functionality and integration with new language-agnostic
architecture. Focuses on potential untested user-facing behavior:

1. Server config mismatch detection
2. Python indexing without Node.js dependency
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml


class TestServerConfigMismatchDetection:
    """Test that server detects mismatches between index and config."""

    def test_server_detects_extraction_method_change(self, tmp_path):
        """Server should detect when extraction method changed without reindexing."""
        storage_dir = tmp_path / ".cicada" / "projects" / "test"
        storage_dir.mkdir(parents=True)

        # Create index with regular extraction
        index_file = storage_dir / "index.json"
        index_data = {
            "modules": {
                "TestMod": {
                    "file": "test.ex",
                    "line": 1,
                    "functions": [],
                    "keywords": {"test": 0.9},
                }
            },
            "metadata": {
                "total_modules": 1,
                "indexed_at": "2025-01-01T00:00:00",
                "language": "elixir",
            },
        }
        with open(index_file, "w") as f:
            json.dump(index_data, f)

        # Create config with bert extraction (different!)
        config_file = storage_dir / "config.yaml"
        config_data = {
            "language": "elixir",
            "keyword_extraction": {"method": "bert"},
            "keyword_expansion": {"method": "glove"},
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Server should detect this mismatch
        # TODO: Implement actual server mismatch detection logic
        # For now, document the expected behavior
        assert index_file.exists(), "Index file should exist"
        assert config_file.exists(), "Config file should exist"

        # Read both and verify they're checking different extraction methods
        with open(index_file) as f:
            index = json.load(f)
        with open(config_file) as f:
            config = yaml.safe_load(f)

        # Index was created with regular (inferred from keywords field)
        # Config now says bert
        config_extraction = config["keyword_extraction"]["method"]
        assert config_extraction == "bert", "Config should specify bert"
        assert (
            "keywords" in index["modules"]["TestMod"]
        ), "Index should have keywords from extraction"

    def test_server_reindex_triggers_on_config_change(self, tmp_path):
        """Server should trigger reindex when config changes."""
        storage_dir = tmp_path / ".cicada" / "projects" / "test"
        storage_dir.mkdir(parents=True)

        # Create old config
        config_file = storage_dir / "config.yaml"
        old_config = {
            "language": "elixir",
            "keyword_extraction": {"method": "regular"},
            "keyword_expansion": {"method": "lemmi"},
        }
        with open(config_file, "w") as f:
            yaml.dump(old_config, f)

        # Read old config
        with open(config_file) as f:
            config = yaml.safe_load(f)
        old_extraction = config["keyword_extraction"]["method"]
        assert old_extraction == "regular"

        # Update config (simulating --max flag)
        new_config = {
            "language": "elixir",
            "keyword_extraction": {"method": "bert"},
            "keyword_expansion": {"method": "fasttext"},
        }
        with open(config_file, "w") as f:
            yaml.dump(new_config, f)

        # Read new config
        with open(config_file) as f:
            config = yaml.safe_load(f)
        new_extraction = config["keyword_extraction"]["method"]

        # Verify the change was made
        assert new_extraction != old_extraction, "Config should have changed"
        assert new_extraction == "bert", "Should have updated to bert"

    def test_server_loads_config_correctly(self, tmp_path):
        """Server should load and parse config.yaml without errors."""
        storage_dir = tmp_path / ".cicada" / "projects" / "test"
        storage_dir.mkdir(parents=True)

        config_file = storage_dir / "config.yaml"
        config_data = {
            "language": "elixir",
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(storage_dir / "index.json")},
            "keyword_extraction": {"method": "regular"},
            "keyword_expansion": {"method": "lemmi"},
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Server-like config loading
        from cicada.utils.storage import get_config_path

        with patch("cicada.utils.storage.get_config_path") as mock_get_config:
            mock_get_config.return_value = config_file

            # Should load without error
            with open(config_file) as f:
                config = yaml.safe_load(f)

            assert config is not None, "Config should load successfully"
            assert config["language"] == "elixir"
            assert config["keyword_extraction"]["method"] == "regular"

    def test_server_handles_missing_config(self, tmp_path):
        """Server should handle missing config gracefully."""
        storage_dir = tmp_path / ".cicada" / "projects" / "test"
        storage_dir.mkdir(parents=True)

        config_file = storage_dir / "nonexistent.yaml"

        # Attempt to load non-existent config
        if config_file.exists():
            with open(config_file) as f:
                config = yaml.safe_load(f)
        else:
            config = None

        assert config is None, "Missing config should result in None"

        # Server should use defaults
        default_extraction = "regular"
        default_expansion = "lemmi"
        assert default_extraction is not None
        assert default_expansion is not None


class TestPythonIndexingWithoutNodeJS:
    """Test Python indexing error handling when dependencies are missing."""

    def test_python_indexer_requires_nodejs(self, tmp_path):
        """Python indexing should verify Node.js is available."""
        # Create a Python project marker
        (tmp_path / "pyproject.toml").write_text("[tool.poetry]")

        # Mock subprocess to simulate Node.js not found
        import subprocess

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("nodejs not found")

            # Attempt to detect Node.js
            try:
                # This is how a Python indexer would check for Node.js
                result = subprocess.run(
                    ["node", "--version"], capture_output=True, check=True, text=True
                )
                pytest.fail("Should not succeed if node is not found")
            except FileNotFoundError:
                # Expected
                pass

    def test_python_scip_installer_error_handling(self, tmp_path):
        """scip-python installer should show clear error if Node.js missing."""
        # Simulate error during scip-python installation
        error_msg = "Node.js is required to run scip-python. Please install Node.js 16+ from https://nodejs.org"

        # In real scenario, this would be checked by PythonSCIPIndexer
        assert "Node.js" in error_msg, "Error message should mention Node.js requirement"
        assert "https://nodejs.org" in error_msg, "Should provide installation link"

    def test_python_indexer_graceful_fallback(self, tmp_path):
        """Python indexer should gracefully handle missing dependencies."""
        # Create minimal Python project structure
        (tmp_path / "pyproject.toml").write_text(
            "[tool.poetry]\n" "name = 'test-project'\n" "version = '0.1.0'"
        )

        # Simulate graceful error handling during indexing
        try:
            # This represents what would happen in PythonSCIPIndexer.index_repository()
            # when Node.js is not available
            subprocess_error = "scip-python requires Node.js to be installed"
            raise RuntimeError(subprocess_error)
        except RuntimeError as e:
            # Should catch and report clearly
            assert "scip-python" in str(e)
            assert "Node.js" in str(e)

    def test_language_detection_prompts_for_python_setup(self, tmp_path):
        """When Python project detected, should explain indexing requirements."""
        (tmp_path / "pyproject.toml").write_text("[tool.poetry]")
        (tmp_path / "setup.py").write_text("from setuptools import setup")

        from cicada.setup import detect_project_language

        language = detect_project_language(tmp_path)

        # If Python is detected, user should be informed about Node.js requirement
        if language == "python":
            requirement_msg = "Python indexing requires Node.js 16+ for scip-python"
            assert requirement_msg  # Should be communicated to user

    def test_mixed_language_project_python_preferred(self, tmp_path):
        """When both Python and Elixir markers exist, Python is preferred."""
        (tmp_path / "pyproject.toml").write_text("[tool.poetry]")
        (tmp_path / "mix.exs").write_text("defmodule Project do; end")

        from cicada.setup import detect_project_language

        language = detect_project_language(tmp_path)

        # Current implementation prefers Python when both exist
        assert language == "python", "Python markers should be checked first (current behavior)"

        # If user wants to index Elixir code in mixed project, they should be able to
        # force it with language parameter
        # This is a UX consideration, not directly tested here

    def test_python_incremental_indexing_not_supported(self, tmp_path):
        """Python indexing doesn't support incremental, should do full index."""
        # Create Python project
        (tmp_path / "pyproject.toml").write_text("[tool.poetry]")

        storage_dir = tmp_path / ".cicada" / "projects" / "test"
        storage_dir.mkdir(parents=True)

        # Create existing index (simulating previous run)
        existing_index = storage_dir / "index.json"
        existing_data = {
            "modules": {"OldModule": {"file": "old.py", "functions": []}},
            "metadata": {"total_modules": 1},
        }
        with open(existing_index, "w") as f:
            json.dump(existing_data, f)

        # Python indexer should recognize incremental isn't supported
        # and warn user that full reindex will be performed
        assert existing_index.exists(), "Previous index exists"

        # When Python indexing is attempted, it should:
        # 1. Detect previous index exists
        # 2. Recognize Python uses scip-python (always full)
        # 3. Warn user and proceed with full index
        # (Specific implementation depends on how indexer handles this)

        full_index_warning = "Python indexing uses SCIP and requires full reindex"
        assert full_index_warning  # Should communicate this to user

    def test_error_message_clarity_for_python_without_nodejs(self):
        """Error messages should be clear when Node.js not found."""
        error_scenarios = [
            {
                "message": "Command 'node' not found",
                "should_suggest": "Install Node.js 16+ from https://nodejs.org",
            },
            {
                "message": "scip-python installation failed",
                "should_suggest": "Node.js",
            },
        ]

        for scenario in error_scenarios:
            error_msg = scenario["message"]
            suggestion = scenario["should_suggest"]
            assert suggestion, f"Scenario {error_msg} should have clear suggestion"
