"""Tests for the generic SCIP tool installer."""

import os
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from cicada.languages.scip.installer import (
    InstallConfig,
    InstallMethod,
    SCIPToolInstaller,
    _LOCAL_NODE_DIR,
)


class TestInstallConfig:
    """Test InstallConfig dataclass."""

    def test_defaults(self):
        config = InstallConfig(
            method=InstallMethod.NPM,
            package="@sourcegraph/scip-python",
            executable="scip-python",
        )
        assert config.runtime_check is None

    def test_with_runtime_check(self):
        config = InstallConfig(
            method=InstallMethod.GO,
            package="github.com/sourcegraph/scip-go@latest",
            executable="scip-go",
            runtime_check="go",
        )
        assert config.runtime_check == "go"


class TestSCIPToolInstallerRuntimeCheck:
    """Test runtime prerequisite checking."""

    def test_skips_when_runtime_missing(self):
        config = InstallConfig(
            method=InstallMethod.GO,
            package="github.com/sourcegraph/scip-go@latest",
            executable="scip-go",
            runtime_check="go",
        )
        with patch("cicada.languages.scip.installer.shutil.which", return_value=None):
            result = SCIPToolInstaller.try_install(config)
            assert result is None

    def test_proceeds_when_runtime_found(self):
        config = InstallConfig(
            method=InstallMethod.GO,
            package="github.com/sourcegraph/scip-go@latest",
            executable="scip-go",
            runtime_check="go",
        )
        with patch("cicada.languages.scip.installer.shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: {
                "go": "/usr/local/bin/go",
                "scip-go": None,
            }.get(cmd)
            with patch("cicada.languages.scip.installer.subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=1)
                result = SCIPToolInstaller.try_install(config)
                # Should have attempted install (even if it failed)
                mock_run.assert_called_once()

    def test_no_runtime_check_proceeds(self):
        config = InstallConfig(
            method=InstallMethod.COURSIER,
            package="scip-java",
            executable="scip-java",
        )
        with patch("cicada.languages.scip.installer.shutil.which") as mock_which:
            mock_which.return_value = None
            result = SCIPToolInstaller.try_install(config)
            # Coursier needs cs/coursier which isn't found
            assert result is None


class TestNPMInstall:
    """Test NPM installation method."""

    def test_success(self):
        config = InstallConfig(
            method=InstallMethod.NPM,
            package="@sourcegraph/scip-python",
            executable="scip-python",
            runtime_check="npm",
        )
        bin_path = _LOCAL_NODE_DIR / "node_modules" / ".bin" / "scip-python"
        with patch("cicada.languages.scip.installer.shutil.which", return_value="/usr/bin/npm"):
            with patch("cicada.languages.scip.installer.subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                with patch("pathlib.Path.mkdir"):
                    with patch("pathlib.Path.is_file", return_value=True):
                        with patch("os.access", return_value=True):
                            result = SCIPToolInstaller.try_install(config)
                            assert result == str(bin_path)

    def test_npm_failure(self):
        config = InstallConfig(
            method=InstallMethod.NPM,
            package="@sourcegraph/scip-python",
            executable="scip-python",
            runtime_check="npm",
        )
        with patch("cicada.languages.scip.installer.shutil.which", return_value="/usr/bin/npm"):
            with patch("cicada.languages.scip.installer.subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=1, stderr="npm ERR!")
                with patch("pathlib.Path.mkdir"):
                    result = SCIPToolInstaller.try_install(config)
                    assert result is None


class TestGOInstall:
    """Test Go installation method."""

    def test_success_gopath(self):
        config = InstallConfig(
            method=InstallMethod.GO,
            package="github.com/sourcegraph/scip-go/cmd/scip-go@latest",
            executable="scip-go",
            runtime_check="go",
        )
        with patch(
            "cicada.languages.scip.installer.shutil.which", return_value="/usr/local/bin/go"
        ):
            with patch("cicada.languages.scip.installer.subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                with patch.dict(os.environ, {"GOPATH": "/tmp/gopath"}):
                    with patch("pathlib.Path.is_file", return_value=True):
                        result = SCIPToolInstaller.try_install(config)
                        assert result == "/tmp/gopath/bin/scip-go"

    def test_failure(self):
        config = InstallConfig(
            method=InstallMethod.GO,
            package="github.com/sourcegraph/scip-go/cmd/scip-go@latest",
            executable="scip-go",
            runtime_check="go",
        )
        with patch(
            "cicada.languages.scip.installer.shutil.which", return_value="/usr/local/bin/go"
        ):
            with patch("cicada.languages.scip.installer.subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=1, stderr="error")
                result = SCIPToolInstaller.try_install(config)
                assert result is None


class TestGEMInstall:
    """Test Gem installation method."""

    def test_success(self):
        config = InstallConfig(
            method=InstallMethod.GEM,
            package="scip-ruby",
            executable="scip-ruby",
            runtime_check="gem",
        )
        with patch("cicada.languages.scip.installer.shutil.which") as mock_which:
            # First call: runtime check for "gem", then which("scip-ruby") after install
            mock_which.side_effect = lambda cmd: {
                "gem": "/usr/bin/gem",
                "scip-ruby": "/usr/local/bin/scip-ruby",
            }.get(cmd)
            with patch("cicada.languages.scip.installer.subprocess.run") as mock_run:
                # Handle multiple subprocess calls: gem install, then gem environment queries
                def subprocess_side_effect(cmd, **kwargs):
                    if cmd[0] == "gem" and cmd[1] == "install":
                        return Mock(returncode=0)
                    elif cmd[0] == "gem" and cmd[1] == "environment":
                        # Return empty string for gem environment queries
                        return Mock(returncode=0, stdout="")
                    return Mock(returncode=0)

                mock_run.side_effect = subprocess_side_effect
                result = SCIPToolInstaller.try_install(config)
                assert result == "/usr/local/bin/scip-ruby"

    def test_failure(self):
        config = InstallConfig(
            method=InstallMethod.GEM,
            package="scip-ruby",
            executable="scip-ruby",
            runtime_check="gem",
        )
        with patch("cicada.languages.scip.installer.shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: {
                "gem": "/usr/bin/gem",
                "scip-ruby": None,
            }.get(cmd)
            with patch("cicada.languages.scip.installer.subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=1, stderr="error")
                result = SCIPToolInstaller.try_install(config)
                assert result is None


class TestDartPubInstall:
    """Test Dart pub installation method."""

    def test_success_pub_cache(self):
        config = InstallConfig(
            method=InstallMethod.DART_PUB,
            package="scip_dart",
            executable="scip_dart",
            runtime_check="dart",
        )
        pub_cache_bin = Path.home() / ".pub-cache" / "bin" / "scip_dart"
        with patch("cicada.languages.scip.installer.shutil.which", return_value="/usr/bin/dart"):
            with patch("cicada.languages.scip.installer.subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                with patch("pathlib.Path.is_file", return_value=True):
                    result = SCIPToolInstaller.try_install(config)
                    assert result == str(pub_cache_bin)


class TestDotnetInstall:
    """Test Dotnet tool installation method."""

    def test_success_dotnet_tools(self):
        config = InstallConfig(
            method=InstallMethod.DOTNET,
            package="scip-dotnet",
            executable="scip-dotnet",
            runtime_check="dotnet",
        )
        dotnet_path = Path.home() / ".dotnet" / "tools" / "scip-dotnet"
        with patch("cicada.languages.scip.installer.shutil.which", return_value="/usr/bin/dotnet"):
            with patch("cicada.languages.scip.installer.subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                with patch("pathlib.Path.is_file", return_value=True):
                    result = SCIPToolInstaller.try_install(config)
                    assert result == str(dotnet_path)


class TestRustupInstall:
    """Test Rustup component installation method."""

    def test_success(self):
        config = InstallConfig(
            method=InstallMethod.RUSTUP,
            package="rust-analyzer",
            executable="rust-analyzer",
            runtime_check="rustup",
        )
        with patch("cicada.languages.scip.installer.shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: {
                "rustup": "/usr/bin/rustup",
                "rust-analyzer": "/usr/bin/rust-analyzer",
            }.get(cmd)
            with patch("cicada.languages.scip.installer.subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                result = SCIPToolInstaller.try_install(config)
                assert result == "/usr/bin/rust-analyzer"

    def test_failure(self):
        config = InstallConfig(
            method=InstallMethod.RUSTUP,
            package="rust-analyzer",
            executable="rust-analyzer",
            runtime_check="rustup",
        )
        with patch("cicada.languages.scip.installer.shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: {
                "rustup": "/usr/bin/rustup",
                "rust-analyzer": None,
            }.get(cmd)
            with patch("cicada.languages.scip.installer.subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=1, stderr="error")
                result = SCIPToolInstaller.try_install(config)
                assert result is None


class TestCoursierInstall:
    """Test Coursier installation method."""

    def test_success_with_cs(self):
        config = InstallConfig(
            method=InstallMethod.COURSIER,
            package="scip-java",
            executable="scip-java",
        )
        with patch("cicada.languages.scip.installer.shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: {
                "cs": "/usr/local/bin/cs",
                "coursier": None,
                "scip-java": "/usr/local/bin/scip-java",
            }.get(cmd)
            with patch("cicada.languages.scip.installer.subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                result = SCIPToolInstaller.try_install(config)
                assert result == "/usr/local/bin/scip-java"

    def test_no_cs_or_coursier(self):
        config = InstallConfig(
            method=InstallMethod.COURSIER,
            package="scip-java",
            executable="scip-java",
        )
        with patch("cicada.languages.scip.installer.shutil.which", return_value=None):
            result = SCIPToolInstaller.try_install(config)
            assert result is None


class TestConfigurableIndexerAutoInstall:
    """Test auto-install integration in ConfigurableSCIPIndexer._find_executable."""

    def test_auto_installs_when_executable_missing(self):
        from cicada.languages.scip.configurable_indexer import ConfigurableSCIPIndexer

        indexer = ConfigurableSCIPIndexer("go", verbose=False)
        installed_path = "/home/user/go/bin/scip-go"

        with patch("shutil.which", return_value=None):
            with patch(
                "cicada.languages.scip.installer.SCIPToolInstaller.try_install",
                return_value=installed_path,
            ):
                cmd, exe_path = indexer._find_executable()
                assert exe_path == installed_path
                assert cmd[0] == installed_path
                # Rest of command should be preserved
                assert cmd[1:] == ["index", "--output", "index.scip", "./..."]

    def test_skips_install_when_executable_found(self):
        from cicada.languages.scip.configurable_indexer import ConfigurableSCIPIndexer

        indexer = ConfigurableSCIPIndexer("go", verbose=False)

        with patch("shutil.which", return_value="/usr/local/bin/scip-go"):
            cmd, exe_path = indexer._find_executable()
            assert exe_path == "/usr/local/bin/scip-go"
            assert cmd == ["scip-go", "index", "--output", "index.scip", "./..."]

    def test_raises_when_install_fails(self):
        from cicada.languages.scip.configurable_indexer import ConfigurableSCIPIndexer

        indexer = ConfigurableSCIPIndexer("go", verbose=False)

        with patch("shutil.which", return_value=None):
            with patch(
                "cicada.languages.scip.installer.SCIPToolInstaller.try_install",
                return_value=None,
            ):
                with pytest.raises(RuntimeError, match="go indexer not found"):
                    indexer._find_executable()

    def test_raises_without_install_config(self):
        """Languages without install_config should raise immediately."""
        from cicada.languages.scip.configurable_indexer import ConfigurableSCIPIndexer

        indexer = ConfigurableSCIPIndexer("c", verbose=False)
        assert indexer.config.install_config is None

        with patch("shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="c indexer not found"):
                indexer._find_executable()


class TestRustIndexerAutoInstall:
    """Test auto-install integration in RustSCIPIndexer."""

    def test_auto_installs_rust_analyzer(self):
        from cicada.languages.rust.indexer import RustSCIPIndexer

        indexer = RustSCIPIndexer(verbose=False)

        with patch.object(indexer, "_is_rust_analyzer_installed", return_value=False):
            with patch(
                "cicada.languages.scip.installer.SCIPToolInstaller.try_install",
                return_value="/usr/bin/rust-analyzer",
            ):
                # Should not raise
                indexer._ensure_rust_analyzer_installed()

    def test_raises_when_auto_install_fails(self):
        from cicada.languages.rust.indexer import RustSCIPIndexer

        indexer = RustSCIPIndexer(verbose=False)

        with patch.object(indexer, "_is_rust_analyzer_installed", return_value=False):
            with patch(
                "cicada.languages.scip.installer.SCIPToolInstaller.try_install",
                return_value=None,
            ):
                with pytest.raises(RuntimeError, match="rust-analyzer is required"):
                    indexer._ensure_rust_analyzer_installed()

    def test_no_install_when_already_available(self):
        from cicada.languages.rust.indexer import RustSCIPIndexer

        indexer = RustSCIPIndexer(verbose=False)

        with patch.object(indexer, "_is_rust_analyzer_installed", return_value=True):
            with patch.object(indexer, "_get_rust_analyzer_version", return_value="0.3.2127"):
                # Should not attempt install
                indexer._ensure_rust_analyzer_installed()


class TestSubprocessTimeout:
    """Test that subprocess calls respect timeouts."""

    def test_npm_timeout(self):
        config = InstallConfig(
            method=InstallMethod.NPM,
            package="some-package",
            executable="some-exe",
            runtime_check="npm",
        )
        with patch("cicada.languages.scip.installer.shutil.which", return_value="/usr/bin/npm"):
            with patch("cicada.languages.scip.installer.subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.TimeoutExpired(cmd="npm", timeout=180)
                with patch("pathlib.Path.mkdir"):
                    with pytest.raises(subprocess.TimeoutExpired):
                        SCIPToolInstaller.try_install(config)
