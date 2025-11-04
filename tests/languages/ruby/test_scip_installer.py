"""Tests for Ruby SCIP installer utilities."""

import pytest
from unittest.mock import Mock, patch
import subprocess

from cicada.languages.ruby.scip_installer import SCIPRubyInstaller


class TestSCIPRubyInstallerAvailability:
    """Test availability check methods."""

    def test_is_gem_available_when_present(self):
        """Should return True when gem is in PATH."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/gem"
            assert SCIPRubyInstaller.is_gem_available() is True
            mock_which.assert_called_once_with("gem")

    def test_is_gem_available_when_absent(self):
        """Should return False when gem is not in PATH."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None
            assert SCIPRubyInstaller.is_gem_available() is False

    def test_is_bundle_available_when_present(self):
        """Should return True when bundle is in PATH."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/bundle"
            assert SCIPRubyInstaller.is_bundle_available() is True
            mock_which.assert_called_once_with("bundle")

    def test_is_bundle_available_when_absent(self):
        """Should return False when bundle is not in PATH."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None
            assert SCIPRubyInstaller.is_bundle_available() is False


class TestSCIPRubyInstallerDetection:
    """Test scip-ruby installation detection."""

    def test_is_scip_ruby_installed_via_direct_binary(self):
        """Should detect scip-ruby when available as direct binary."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/scip-ruby"
            assert SCIPRubyInstaller.is_scip_ruby_installed() is True

    def test_is_scip_ruby_installed_via_bundle_exec(self):
        """Should detect scip-ruby when available via bundle exec."""
        with patch("shutil.which") as mock_which:
            # First call checks for direct binary (not found)
            # Second call checks for bundle
            mock_which.side_effect = [None, "/usr/bin/bundle"]

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                assert SCIPRubyInstaller.is_scip_ruby_installed() is True

    def test_is_scip_ruby_installed_not_found(self):
        """Should return False when scip-ruby is not available."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None
            assert SCIPRubyInstaller.is_scip_ruby_installed() is False

    def test_is_scip_ruby_installed_bundle_exec_fails(self):
        """Should return False when bundle exec check fails."""
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = [None, "/usr/bin/bundle"]

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=1)
                assert SCIPRubyInstaller.is_scip_ruby_installed() is False


class TestSCIPRubyInstallerInstallation:
    """Test scip-ruby installation process."""

    def test_install_scip_ruby_success(self):
        """Should successfully install scip-ruby."""
        with patch.object(SCIPRubyInstaller, "is_gem_available", return_value=True):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stderr="")
                result = SCIPRubyInstaller.install_scip_ruby(verbose=False)
                assert result is True
                mock_run.assert_called_once()
                args = mock_run.call_args[0][0]
                assert args == ["gem", "install", "scip-ruby"]

    def test_install_scip_ruby_failure(self):
        """Should return False when installation fails."""
        with patch.object(SCIPRubyInstaller, "is_gem_available", return_value=True):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=1, stderr="Error")
                result = SCIPRubyInstaller.install_scip_ruby(verbose=False)
                assert result is False

    def test_install_scip_ruby_no_gem(self):
        """Should raise RuntimeError when gem is not available."""
        with patch.object(SCIPRubyInstaller, "is_gem_available", return_value=False):
            with pytest.raises(RuntimeError, match="gem is required"):
                SCIPRubyInstaller.install_scip_ruby()

    def test_install_scip_ruby_verbose_output(self):
        """Should print progress when verbose is True."""
        with patch.object(SCIPRubyInstaller, "is_gem_available", return_value=True):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stderr="")
                with patch("builtins.print") as mock_print:
                    SCIPRubyInstaller.install_scip_ruby(verbose=True)
                    mock_print.assert_called()


class TestSCIPRubyInstallerVersion:
    """Test version detection."""

    def test_get_scip_ruby_version_when_not_installed(self):
        """Should return None when scip-ruby is not installed."""
        with patch.object(
            SCIPRubyInstaller, "is_scip_ruby_installed", return_value=False
        ):
            assert SCIPRubyInstaller.get_scip_ruby_version() is None

    def test_get_scip_ruby_version_via_direct_binary(self):
        """Should get version from direct binary."""
        with patch.object(
            SCIPRubyInstaller, "is_scip_ruby_installed", return_value=True
        ):
            with patch("shutil.which") as mock_which:
                mock_which.return_value = "/usr/local/bin/scip-ruby"
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = Mock(
                        returncode=0, stdout="scip-ruby 0.3.0\n"
                    )
                    version = SCIPRubyInstaller.get_scip_ruby_version()
                    assert version == "scip-ruby 0.3.0"

    def test_get_scip_ruby_version_via_bundle_exec(self):
        """Should get version via bundle exec when direct binary not available."""
        with patch.object(
            SCIPRubyInstaller, "is_scip_ruby_installed", return_value=True
        ):
            with patch("shutil.which") as mock_which:
                # First call checks for direct binary (not found)
                # Second call checks for bundle
                mock_which.side_effect = [None, "/usr/bin/bundle"]
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = Mock(
                        returncode=0, stdout="scip-ruby 0.3.0\n"
                    )
                    with patch.object(
                        SCIPRubyInstaller, "is_bundle_available", return_value=True
                    ):
                        version = SCIPRubyInstaller.get_scip_ruby_version()
                        assert version == "scip-ruby 0.3.0"

    def test_get_scip_ruby_version_command_fails(self):
        """Should return None when version command fails."""
        with patch.object(
            SCIPRubyInstaller, "is_scip_ruby_installed", return_value=True
        ):
            with patch("shutil.which") as mock_which:
                mock_which.return_value = "/usr/local/bin/scip-ruby"
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = Mock(returncode=1, stdout="")
                    with patch.object(
                        SCIPRubyInstaller, "is_bundle_available", return_value=False
                    ):
                        version = SCIPRubyInstaller.get_scip_ruby_version()
                        assert version is None
