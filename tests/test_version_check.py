"""
Tests for cicada/version_check.py
"""

import subprocess
from unittest.mock import Mock

import pytest

from cicada.version_check import (
    check_for_updates,
    compare_versions,
    extract_version_tag,
    get_current_version,
    get_latest_github_tag,
    version_mismatch,
)


class TestGetCurrentVersion:
    """Tests for get_current_version function"""

    def test_returns_current_version(self):
        """Should return the version from pyproject.toml"""
        version = get_current_version()
        # Verify it's a valid version string format
        assert isinstance(version, str)
        assert len(version.split(".")) >= 2  # At least major.minor
        # Verify it matches the version in __init__.py (both read from pyproject.toml)
        from cicada import __version__

        assert version == __version__


class TestGetLatestGithubTag:
    """Tests for get_latest_github_tag function"""

    @pytest.mark.parametrize(
        "stdout,expected",
        [
            ("v0.2.0\n", "0.2.0"),  # Remove v prefix
            ("v1.2.3", "1.2.3"),  # Remove v prefix (no newline)
            ("2.0.0", "2.0.0"),  # No v prefix
            ("  v0.3.0  \n", "0.3.0"),  # Strip whitespace
        ],
    )
    def test_tag_normalization(self, stdout, expected, monkeypatch):
        """Should normalize tags by removing 'v' prefix and whitespace"""
        mock_result = Mock(returncode=0, stdout=stdout)
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: mock_result)
        assert get_latest_github_tag() == expected

    @pytest.mark.parametrize(
        "returncode,stdout,expected",
        [
            (1, "v0.2.0", None),  # Non-zero return code
            (0, "", None),  # Empty stdout
            (0, "   \n", None),  # Whitespace-only
        ],
    )
    def test_failure_cases(self, returncode, stdout, expected, monkeypatch):
        """Should return None on failure"""
        mock_result = Mock(returncode=returncode, stdout=stdout)
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: mock_result)
        assert get_latest_github_tag() == expected

    @pytest.mark.parametrize(
        "exception",
        [
            subprocess.TimeoutExpired(cmd="gh", timeout=5),
            FileNotFoundError("gh command not found"),
            Exception("Unexpected error"),
        ],
    )
    def test_exception_handling(self, exception, monkeypatch):
        """Should return None on exceptions"""
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(exception))
        assert get_latest_github_tag() is None

    def test_custom_repo(self, monkeypatch):
        """Should use custom repository when specified"""
        calls = []
        mock_result = Mock(returncode=0, stdout="v1.0.0")

        def mock_run(*args, **kwargs):
            calls.append(args[0])
            return mock_result

        monkeypatch.setattr(subprocess, "run", mock_run)
        assert get_latest_github_tag(repo="custom/repo") == "1.0.0"
        assert "repos/custom/repo/tags" in calls[0]


class TestCompareVersions:
    """Tests for compare_versions function"""

    @pytest.mark.parametrize(
        "current,latest,expected",
        [
            # Newer versions
            ("0.1.0", "1.0.0", True),  # Major
            ("0.1.0", "0.2.0", True),  # Minor
            ("0.1.0", "0.1.1", True),  # Patch
            ("0.1", "0.1.1", True),  # Different lengths
            ("0.9.0", "0.10.0", True),  # Multi-digit
            ("1.99.99", "2.0.0", True),  # Large numbers
            # Same version
            ("0.1.0", "0.1.0", False),
            ("1.0", "1.0.0", False),  # Padded with zeros
            # Older versions
            ("2.0.0", "1.0.0", False),  # Major
            ("0.2.0", "0.1.0", False),  # Minor
            ("0.1.5", "0.1.2", False),  # Patch
            ("0.1.1", "0.1", False),  # Different lengths
            # Invalid versions
            ("invalid", "0.1.0", False),
            ("0.1.0", "invalid", False),
            ("invalid", "also-invalid", False),
            ("0.1.x", "0.2.0", False),
            ("", "0.1.0", False),
        ],
    )
    def test_version_comparison(self, current, latest, expected):
        """Should correctly compare version strings"""
        assert compare_versions(current, latest) == expected


class TestExtractVersionTag:
    """Tests for extract_version_tag function"""

    @pytest.mark.parametrize(
        "version_string,expected",
        [
            ("0.2.2 (v0.2.2/0991325)", "0.2.2"),
            ("0.2.1 (v0.2.1/478f5cd)", "0.2.1"),
            ("0.2.2", "0.2.2"),
            ("", ""),
            ("1.0.0 (v1.0.0/abc1234)", "1.0.0"),
        ],
    )
    def test_extract_version_tag(self, version_string, expected):
        """Should extract pyproject version from version string"""
        assert extract_version_tag(version_string) == expected


class TestVersionMismatch:
    """Tests for version_mismatch function"""

    @pytest.mark.parametrize(
        "stored_version,current_version,expected",
        [
            # Different major/minor versions - should trigger reindex
            ("0.2.1 (v0.2.1/478f5cd)", "0.2.2 (v0.2.2/0991325)", True),
            ("0.1.0", "0.2.0", True),
            # Same version (ignore git hash/tag differences) - no reindex
            ("0.2.2 (v0.2.2/0991325)", "0.2.2 (v0.2.2/different)", False),
            ("0.2.2", "0.2.2 (v0.2.2/0991325)", False),
            # Missing stored version - should trigger reindex
            (None, "0.2.2 (v0.2.2/0991325)", True),
            ("", "0.2.2 (v0.2.2/0991325)", True),
        ],
    )
    def test_version_mismatch(self, stored_version, current_version, expected):
        """Should detect version mismatches correctly"""
        assert version_mismatch(stored_version, current_version) == expected


class TestCheckForUpdates:
    """Tests for check_for_updates function"""

    def test_newer_version_available(self, monkeypatch, capsys):
        """Should display update message when newer version available"""
        monkeypatch.setattr("cicada.version_check.get_current_version", lambda: "0.1.0")
        monkeypatch.setattr("cicada.version_check.get_latest_github_tag", lambda: "0.2.0")

        check_for_updates()

        captured = capsys.readouterr()
        assert "newer version" in captured.out.lower()
        assert "0.2.0" in captured.out
        assert "0.1.0" in captured.out
        assert "uv tool install" in captured.out
        assert "⚠️" in captured.out

    @pytest.mark.parametrize(
        "current_version,latest_version",
        [
            ("0.1.0", "0.1.0"),  # Same version
            ("0.3.0", "0.2.0"),  # Dev version (newer)
            ("0.1.0", None),  # Unable to fetch latest
        ],
    )
    def test_no_update_message(self, current_version, latest_version, monkeypatch, capsys):
        """Should not display message when no update needed"""
        monkeypatch.setattr("cicada.version_check.get_current_version", lambda: current_version)
        monkeypatch.setattr("cicada.version_check.get_latest_github_tag", lambda: latest_version)

        check_for_updates()

        captured = capsys.readouterr()
        assert captured.out == ""

    @pytest.mark.parametrize(
        "failing_function,exception",
        [
            ("get_current_version", Exception("Error getting version")),
            ("get_latest_github_tag", Exception("Error fetching tag")),
            ("compare_versions", Exception("Error comparing")),
        ],
    )
    def test_exception_handling(self, failing_function, exception, monkeypatch, capsys):
        """Should fail silently on exceptions"""
        monkeypatch.setattr("cicada.version_check.get_current_version", lambda: "0.1.0")
        monkeypatch.setattr("cicada.version_check.get_latest_github_tag", lambda: "0.2.0")

        if failing_function == "get_current_version":
            monkeypatch.setattr(
                "cicada.version_check.get_current_version",
                lambda: (_ for _ in ()).throw(exception),
            )
        elif failing_function == "get_latest_github_tag":
            monkeypatch.setattr(
                "cicada.version_check.get_latest_github_tag",
                lambda: (_ for _ in ()).throw(exception),
            )
        else:
            monkeypatch.setattr(
                "cicada.version_check.compare_versions",
                lambda *a: (_ for _ in ()).throw(exception),
            )

        check_for_updates()  # Should not raise

        captured = capsys.readouterr()
        assert captured.out == ""
