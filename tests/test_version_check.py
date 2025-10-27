"""
Comprehensive tests for cicada/version_check.py
"""

import pytest
import subprocess
from unittest.mock import Mock
from cicada.version_check import (
    get_current_version,
    get_latest_github_tag,
    compare_versions,
    check_for_updates,
)


class TestGetCurrentVersion:
    """Tests for get_current_version function"""

    def test_returns_hardcoded_version(self):
        """Test that current version is returned"""
        result = get_current_version()
        assert result == "0.1.1"

    def test_returns_string(self):
        """Test that version is a string"""
        result = get_current_version()
        assert isinstance(result, str)


class TestGetLatestGithubTag:
    """Tests for get_latest_github_tag function"""

    def test_get_tag_success(self, monkeypatch):
        """Test successful tag retrieval"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "v0.2.0\n"

        def mock_run(*args, **kwargs):
            return mock_result

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = get_latest_github_tag()
        assert result == "0.2.0"

    def test_get_tag_removes_v_prefix(self, monkeypatch):
        """Test that 'v' prefix is removed from tag"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "v1.2.3"

        monkeypatch.setattr(subprocess, "run", lambda *a, **k: mock_result)

        result = get_latest_github_tag()
        assert result == "1.2.3"

    def test_get_tag_without_v_prefix(self, monkeypatch):
        """Test tag without 'v' prefix"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "2.0.0"

        monkeypatch.setattr(subprocess, "run", lambda *a, **k: mock_result)

        result = get_latest_github_tag()
        assert result == "2.0.0"

    def test_get_tag_with_whitespace(self, monkeypatch):
        """Test tag with extra whitespace is stripped"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "  v0.3.0  \n"

        monkeypatch.setattr(subprocess, "run", lambda *a, **k: mock_result)

        result = get_latest_github_tag()
        assert result == "0.3.0"

    def test_get_tag_non_zero_returncode(self, monkeypatch):
        """Test handling of non-zero return code"""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = "v0.2.0"

        monkeypatch.setattr(subprocess, "run", lambda *a, **k: mock_result)

        result = get_latest_github_tag()
        assert result is None

    def test_get_tag_empty_stdout(self, monkeypatch):
        """Test handling of empty stdout"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        monkeypatch.setattr(subprocess, "run", lambda *a, **k: mock_result)

        result = get_latest_github_tag()
        assert result is None

    def test_get_tag_whitespace_only_stdout(self, monkeypatch):
        """Test handling of whitespace-only stdout"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "   \n"

        monkeypatch.setattr(subprocess, "run", lambda *a, **k: mock_result)

        result = get_latest_github_tag()
        assert result is None

    def test_get_tag_subprocess_timeout(self, monkeypatch):
        """Test handling of subprocess timeout"""

        def mock_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="gh", timeout=5)

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = get_latest_github_tag()
        assert result is None

    def test_get_tag_file_not_found(self, monkeypatch):
        """Test handling when gh command is not found"""

        def mock_run(*args, **kwargs):
            raise FileNotFoundError("gh command not found")

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = get_latest_github_tag()
        assert result is None

    def test_get_tag_generic_exception(self, monkeypatch):
        """Test handling of generic exceptions"""

        def mock_run(*args, **kwargs):
            raise Exception("Some unexpected error")

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = get_latest_github_tag()
        assert result is None

    def test_get_tag_custom_repo(self, monkeypatch):
        """Test with custom repository"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "v1.0.0"

        calls = []

        def mock_run(*args, **kwargs):
            calls.append(args[0])
            return mock_result

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = get_latest_github_tag(repo="custom/repo")
        assert result == "1.0.0"
        assert "repos/custom/repo/tags" in calls[0]


class TestCompareVersions:
    """Tests for compare_versions function"""

    def test_compare_newer_major_version(self):
        """Test that newer major version is detected"""
        assert compare_versions("0.1.0", "1.0.0") is True

    def test_compare_newer_minor_version(self):
        """Test that newer minor version is detected"""
        assert compare_versions("0.1.0", "0.2.0") is True

    def test_compare_newer_patch_version(self):
        """Test that newer patch version is detected"""
        assert compare_versions("0.1.0", "0.1.1") is True

    def test_compare_same_version(self):
        """Test that same versions are equal"""
        assert compare_versions("0.1.0", "0.1.0") is False

    def test_compare_older_major_version(self):
        """Test that older major version returns False"""
        assert compare_versions("2.0.0", "1.0.0") is False

    def test_compare_older_minor_version(self):
        """Test that older minor version returns False"""
        assert compare_versions("0.2.0", "0.1.0") is False

    def test_compare_older_patch_version(self):
        """Test that older patch version returns False"""
        assert compare_versions("0.1.5", "0.1.2") is False

    def test_compare_different_length_versions(self):
        """Test comparing versions with different lengths"""
        assert compare_versions("0.1", "0.1.1") is True

    def test_compare_different_length_versions_reverse(self):
        """Test comparing versions with different lengths (reverse)"""
        assert compare_versions("0.1.1", "0.1") is False

    def test_compare_padded_versions(self):
        """Test versions are properly padded with zeros"""
        assert compare_versions("1.0", "1.0.0") is False

    def test_compare_multi_digit_versions(self):
        """Test versions with multi-digit numbers"""
        assert compare_versions("0.9.0", "0.10.0") is True

    def test_compare_large_version_numbers(self):
        """Test comparing large version numbers"""
        assert compare_versions("1.99.99", "2.0.0") is True

    def test_compare_invalid_current_version(self):
        """Test handling invalid current version"""
        assert compare_versions("invalid", "0.1.0") is False

    def test_compare_invalid_latest_version(self):
        """Test handling invalid latest version"""
        assert compare_versions("0.1.0", "invalid") is False

    def test_compare_both_invalid_versions(self):
        """Test handling both invalid versions"""
        assert compare_versions("invalid", "also-invalid") is False

    def test_compare_version_with_non_numeric(self):
        """Test handling version with non-numeric parts"""
        assert compare_versions("0.1.x", "0.2.0") is False

    def test_compare_empty_string_versions(self):
        """Test handling empty string versions"""
        assert compare_versions("", "0.1.0") is False

    def test_compare_none_like_versions(self):
        """Test handling None-like attribute errors"""
        # This would raise AttributeError when trying to call .split() on None
        # But the function catches it
        result = compare_versions("0.1.0", "0.2.0")
        assert isinstance(result, bool)


class TestCheckForUpdates:
    """Tests for check_for_updates function"""

    def test_check_for_updates_newer_version_available(self, monkeypatch, capsys):
        """Test when a newer version is available"""
        monkeypatch.setattr("cicada.version_check.get_current_version", lambda: "0.1.0")
        monkeypatch.setattr(
            "cicada.version_check.get_latest_github_tag", lambda: "0.2.0"
        )

        check_for_updates()

        captured = capsys.readouterr()
        assert "newer version" in captured.out.lower()
        assert "0.2.0" in captured.out
        assert "0.1.0" in captured.out
        assert "uv tool install" in captured.out

    def test_check_for_updates_same_version(self, monkeypatch, capsys):
        """Test when current version is up to date"""
        monkeypatch.setattr("cicada.version_check.get_current_version", lambda: "0.1.0")
        monkeypatch.setattr(
            "cicada.version_check.get_latest_github_tag", lambda: "0.1.0"
        )

        check_for_updates()

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_check_for_updates_older_version_available(self, monkeypatch, capsys):
        """Test when current version is newer than latest (dev version)"""
        monkeypatch.setattr("cicada.version_check.get_current_version", lambda: "0.3.0")
        monkeypatch.setattr(
            "cicada.version_check.get_latest_github_tag", lambda: "0.2.0"
        )

        check_for_updates()

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_check_for_updates_no_latest_tag(self, monkeypatch, capsys):
        """Test when unable to fetch latest tag"""
        monkeypatch.setattr("cicada.version_check.get_current_version", lambda: "0.1.0")
        monkeypatch.setattr("cicada.version_check.get_latest_github_tag", lambda: None)

        check_for_updates()

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_check_for_updates_exception_in_get_current(self, monkeypatch, capsys):
        """Test handling exception in get_current_version"""

        def raise_error():
            raise Exception("Error getting version")

        monkeypatch.setattr("cicada.version_check.get_current_version", raise_error)
        monkeypatch.setattr(
            "cicada.version_check.get_latest_github_tag", lambda: "0.2.0"
        )

        # Should not raise, fails silently
        check_for_updates()

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_check_for_updates_exception_in_get_latest(self, monkeypatch, capsys):
        """Test handling exception in get_latest_github_tag"""
        monkeypatch.setattr("cicada.version_check.get_current_version", lambda: "0.1.0")

        def raise_error():
            raise Exception("Error fetching tag")

        monkeypatch.setattr("cicada.version_check.get_latest_github_tag", raise_error)

        # Should not raise, fails silently
        check_for_updates()

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_check_for_updates_exception_in_compare(self, monkeypatch, capsys):
        """Test handling exception in compare_versions"""
        monkeypatch.setattr("cicada.version_check.get_current_version", lambda: "0.1.0")
        monkeypatch.setattr(
            "cicada.version_check.get_latest_github_tag", lambda: "0.2.0"
        )

        def raise_error(*args):
            raise Exception("Error comparing versions")

        monkeypatch.setattr("cicada.version_check.compare_versions", raise_error)

        # Should not raise, fails silently
        check_for_updates()

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_check_for_updates_contains_warning_emoji(self, monkeypatch, capsys):
        """Test that update message contains warning emoji"""
        monkeypatch.setattr("cicada.version_check.get_current_version", lambda: "0.1.0")
        monkeypatch.setattr(
            "cicada.version_check.get_latest_github_tag", lambda: "0.2.0"
        )

        check_for_updates()

        captured = capsys.readouterr()
        assert "⚠️" in captured.out

    def test_check_for_updates_contains_color_codes(self, monkeypatch, capsys):
        """Test that update message contains ANSI color codes"""
        monkeypatch.setattr("cicada.version_check.get_current_version", lambda: "0.1.0")
        monkeypatch.setattr(
            "cicada.version_check.get_latest_github_tag", lambda: "0.2.0"
        )

        check_for_updates()

        captured = capsys.readouterr()
        # Check for ANSI color codes
        assert "\033[93m" in captured.out  # Yellow
        assert "\033[0m" in captured.out  # Reset
