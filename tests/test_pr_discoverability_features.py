#!/usr/bin/env python
"""
Tests for PR #70 discoverability features:
- Fuzzy matching for module suggestions
- Error messages with "did you mean" suggestions
- Index staleness warnings
- PR context in search results
"""

import json
import os
import time
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

from cicada.format.formatter import ModuleFormatter
from cicada.mcp.server import CicadaServer
from cicada.utils.storage import get_pr_index_path, get_storage_dir


class TestFindSimilarNames:
    """Test fuzzy matching for module name suggestions."""

    def test_exact_match(self):
        """Should return exact match with high similarity"""
        names = ["MyApp.User", "MyApp.UserController", "OtherApp.User"]
        results = ModuleFormatter._find_similar_names("MyApp.User", names)

        assert len(results) == 1
        assert results[0][0] == "MyApp.User"
        assert results[0][1] == 1.0

    def test_case_insensitive_exact_match(self):
        """Should match case-insensitively for exact matches"""
        names = ["MyApp.User", "MyApp.UserController"]
        results = ModuleFormatter._find_similar_names("myapp.user", names)

        assert len(results) == 1
        assert results[0][0] == "MyApp.User"
        assert results[0][1] == 1.0

    def test_partial_match(self):
        """Should find partial matches with boosted scores"""
        names = ["MyApp.Authentication.TokenService", "MyApp.User", "OtherApp.Session"]
        results = ModuleFormatter._find_similar_names("Auth", names)

        # Should find Authentication
        assert len(results) > 0
        assert "Authentication" in results[0][0]
        assert results[0][1] >= 0.6  # Boosted score

    def test_substring_match(self):
        """Should boost substring matches"""
        names = ["MyApp.User", "MyApp.UserController", "MyApp.UserService"]
        results = ModuleFormatter._find_similar_names("User", names)

        assert len(results) >= 3
        for name, score in results:
            assert "User" in name
            assert score >= 0.7  # Substring boost

    def test_below_threshold(self):
        """Should not return results below similarity threshold"""
        names = ["CompletelyDifferentModule", "AnotherModule"]
        results = ModuleFormatter._find_similar_names("MyApp", names)

        # Results should be empty or have low scores filtered out
        for name, score in results:
            assert score > 0.4

    def test_limits_max_suggestions(self):
        """Should limit results to max_suggestions"""
        names = [f"MyApp.User{i}" for i in range(20)]
        results = ModuleFormatter._find_similar_names("User", names, max_suggestions=5)

        assert len(results) <= 5

    def test_performance_with_large_index(self):
        """Should handle large indices efficiently by limiting search space"""
        # Create a large list of names
        names = [f"Module{i}.Submodule{i}.Function{i}" for i in range(1000)]

        start_time = time.time()
        results = ModuleFormatter._find_similar_names("Module500", names)
        end_time = time.time()

        # Should complete quickly (under 1 second even with 1000 modules)
        assert end_time - start_time < 1.0

        # Should still find something reasonable
        assert len(results) > 0


class TestErrorMessagesWithSuggestions:
    """Test error message formatting with suggestions."""

    def test_error_with_suggestions(self):
        """Should include 'Did you mean?' suggestions"""
        available = ["MyApp.User", "MyApp.UserController", "MyApp.Authentication"]
        result = ModuleFormatter.format_error_markdown("MyApp.Usr", 10, available)

        assert "Did you mean?" in result
        assert "MyApp.User" in result
        assert "Query:" in result
        assert "MyApp.Usr" in result

    def test_error_with_no_close_matches(self):
        """Should still provide helpful alternatives when no close matches"""
        available = ["CompletelyDifferent.Module"]
        result = ModuleFormatter.format_error_markdown("MyApp.User", 1, available)

        # Should still have Try section with alternatives
        assert "Try:" in result
        assert "Wildcard search:" in result
        assert "Semantic search:" in result

    def test_error_includes_total_modules(self):
        """Should show total available modules"""
        result = ModuleFormatter.format_error_markdown("Missing", 42, [])

        assert "42" in result
        assert "Total modules" in result

    def test_error_with_empty_module_name(self):
        """Should handle empty module names gracefully"""
        result = ModuleFormatter.format_error_markdown("", 10, ["MyApp.User"])

        # Should not crash and should still provide guidance
        assert "Try:" in result
        assert "case-sensitive" in result

    def test_error_with_dots_only(self):
        """Should handle edge case of dots-only module name"""
        result = ModuleFormatter.format_error_markdown("...", 10, ["MyApp.User"])

        # Should not crash
        assert "Try:" in result


class TestStalenessWarnings:
    """Test index staleness detection and warnings."""

    @pytest.fixture
    def test_server(self, tmp_path):
        """Create a test server with a fresh index"""
        index = {
            "modules": {
                "TestModule": {
                    "file": "test.ex",
                    "functions": [],
                    "line": 1,
                }
            },
            "metadata": {"total_modules": 1},
        }

        # Create the test file FIRST (before index)
        test_file = tmp_path / "test.ex"
        test_file.write_text("defmodule TestModule do\nend")

        # Small delay to ensure clear time difference
        time.sleep(0.01)

        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        server = CicadaServer(str(config_path))
        return server

    def test_fresh_index_no_warning(self, test_server):
        """Should not show warning for fresh index"""
        staleness = test_server._check_index_staleness()

        # Fresh index - should be None or not stale
        # (index was created after the file, so it should be fresh)
        assert staleness is None or staleness.get("is_stale") is False

    def test_stale_index_shows_warning(self, test_server, tmp_path):
        """Should detect stale index when files are modified"""
        # Wait a moment to ensure time difference
        time.sleep(0.1)

        # Modify the file
        test_file = tmp_path / "test.ex"
        test_file.write_text("defmodule TestModule do\n  def new_func, do: :ok\nend")

        staleness = test_server._check_index_staleness()

        # Should detect staleness
        assert staleness is not None
        assert staleness["is_stale"] is True
        assert "age_str" in staleness

    def test_staleness_age_formatting_minutes(self, test_server, tmp_path):
        """Should format age in minutes for recent indices"""
        # Make index appear a few minutes old
        index_path = Path(test_server.config["storage"]["index_path"])
        old_time = time.time() - 180  # 3 minutes ago
        os.utime(index_path, (old_time, old_time))

        # Touch the file to make it newer
        test_file = tmp_path / "test.ex"
        test_file.touch()

        staleness = test_server._check_index_staleness()

        if staleness:
            assert "minutes" in staleness["age_str"]

    def test_staleness_age_formatting_hours(self, test_server, tmp_path):
        """Should format age in hours for older indices"""
        # Make index appear a few hours old
        index_path = Path(test_server.config["storage"]["index_path"])
        old_time = time.time() - 7200  # 2 hours ago
        os.utime(index_path, (old_time, old_time))

        # Touch the file to make it newer
        test_file = tmp_path / "test.ex"
        test_file.touch()

        staleness = test_server._check_index_staleness()

        if staleness:
            assert "hours" in staleness["age_str"]

    def test_staleness_warning_in_module_format(self):
        """Should include staleness warning in formatted output"""
        module_data = {
            "file": "test.ex",
            "line": 1,
            "functions": [],
            "public_functions": 0,
            "private_functions": 0,
        }

        staleness_info = {
            "is_stale": True,
            "age_str": "2 hours",
        }

        result = ModuleFormatter.format_module_markdown(
            "TestModule", module_data, staleness_info=staleness_info
        )

        assert "⚠️" in result
        assert "may be stale" in result
        assert "2 hours" in result
        assert "Please ask the user to run: cicada index" in result

    def test_staleness_warning_in_function_format(self):
        """Should include staleness warning in function search results"""
        staleness_info = {
            "is_stale": True,
            "age_str": "3 days",
        }

        results = []  # Empty results

        result = ModuleFormatter.format_function_results_markdown(
            "test_function", results, staleness_info=staleness_info
        )

        assert "⚠️" in result
        assert "may be stale" in result
        assert "3 days" in result

    def test_staleness_uses_random_sampling(self, test_server, tmp_path):
        """Should use random sampling for large indices"""
        # Create a larger index
        index = {"modules": {}, "metadata": {"total_modules": 100}}

        for i in range(100):
            file_name = f"test_{i}.ex"
            index["modules"][f"Module{i}"] = {
                "file": file_name,
                "functions": [],
                "line": 1,
            }
            # Create the file
            (tmp_path / file_name).write_text(f"defmodule Module{i} do\nend")

        index_path = Path(test_server.config["storage"]["index_path"])
        with open(index_path, "w") as f:
            json.dump(index, f)

        # Reload index
        test_server.index = test_server._load_index()

        # This should not crash and should complete quickly
        staleness = test_server._check_index_staleness()

        # Should complete without error
        assert staleness is None or isinstance(staleness, dict)


class TestPRContextInResults:
    """Test PR context inclusion in search results."""

    @pytest.fixture
    def server_with_pr_index(self, tmp_path):
        """Create a server with PR index"""
        index = {
            "modules": {
                "TestModule": {
                    "file": "lib/test.ex",
                    "line": 1,
                    "functions": [
                        {
                            "name": "test_func",
                            "arity": 0,
                            "line": 5,
                            "type": "def",
                        }
                    ],
                    "public_functions": 1,
                    "private_functions": 0,
                }
            },
            "metadata": {"total_modules": 1},
        }

        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        # Create PR index in the correct storage location
        pr_index = {
            "file_to_prs": {
                "lib/test.ex": [123, 456],
            },
            "prs": {
                "123": {
                    "number": 123,
                    "title": "Add test functionality",
                    "author": "developer",
                    "url": "https://github.com/test/repo/pull/123",
                    "merged": True,
                    "comments": [{"path": "lib/test.ex", "body": "Looks good!"}],
                },
                "456": {
                    "number": 456,
                    "title": "Update test module",
                    "author": "contributor",
                    "url": "https://github.com/test/repo/pull/456",
                    "merged": True,
                    "comments": [],
                },
            },
        }

        # Use the storage utility to get the correct PR index path
        storage_dir = get_storage_dir(tmp_path)
        storage_dir.mkdir(parents=True, exist_ok=True)
        pr_index_path = get_pr_index_path(tmp_path)

        with open(pr_index_path, "w") as f:
            json.dump(pr_index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {
                "index_path": str(index_path),
            },
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        server = CicadaServer(str(config_path))
        return server

    def test_pr_info_retrieval(self, server_with_pr_index):
        """Should retrieve PR info for a file"""
        pr_info = server_with_pr_index._get_recent_pr_info("lib/test.ex")

        assert pr_info is not None
        assert pr_info["number"] == 456  # Most recent
        assert pr_info["title"] == "Update test module"
        assert pr_info["author"] == "contributor"
        assert pr_info["comment_count"] == 0

    def test_pr_info_with_comments(self, server_with_pr_index):
        """Should count comments for the file"""
        # Manually get the first PR which has comments
        pr_index = server_with_pr_index.pr_index
        prs_data = pr_index.get("prs", {})
        pr = prs_data.get("123")

        comments = pr.get("comments", [])
        file_comments = [c for c in comments if c.get("path") == "lib/test.ex"]

        assert len(file_comments) == 1

    def test_pr_info_no_prs(self, server_with_pr_index):
        """Should return None when no PRs found"""
        pr_info = server_with_pr_index._get_recent_pr_info("nonexistent.ex")

        assert pr_info is None

    def test_pr_context_in_module_output(self, server_with_pr_index):
        """Should include PR context in module search output"""
        module_data = server_with_pr_index.index["modules"]["TestModule"]
        pr_info = server_with_pr_index._get_recent_pr_info(module_data["file"])

        result = ModuleFormatter.format_module_markdown("TestModule", module_data, pr_info=pr_info)

        assert "📝 Last modified:" in result
        assert "PR #456" in result
        assert "Update test module" in result
        assert "@contributor" in result


class TestExceptionHandling:
    """Test improved exception handling."""

    @pytest.fixture
    def server_with_bad_config(self, tmp_path):
        """Create a server with problematic configuration"""
        index = {"modules": {}, "metadata": {"total_modules": 0}}
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        config = {
            "repository": {"path": "/nonexistent/path"},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        server = CicadaServer(str(config_path))
        return server

    def test_staleness_check_handles_missing_files(self, server_with_bad_config):
        """Should handle missing files gracefully"""
        # Should not crash, just return None
        staleness = server_with_bad_config._check_index_staleness()

        # Should handle the error and return None
        assert staleness is None

    def test_staleness_check_handles_permission_errors(self, tmp_path):
        """Should handle permission errors gracefully"""
        index = {
            "modules": {"Test": {"file": "test.ex", "functions": [], "line": 1}},
            "metadata": {"total_modules": 1},
        }

        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        server = CicadaServer(str(config_path))

        # Make index file unreadable (if running as non-root)
        try:
            os.chmod(index_path, 0o000)
            staleness = server._check_index_staleness()
            assert staleness is None
        finally:
            # Restore permissions
            os.chmod(index_path, 0o644)
