"""Tests for Ruby SCIP indexer."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

from cicada.languages.ruby.indexer import RubySCIPIndexer


class TestRubySCIPIndexerInit:
    """Test RubySCIPIndexer initialization."""

    def test_indexer_creates_with_defaults(self):
        """Should create indexer with default settings."""
        indexer = RubySCIPIndexer()
        assert indexer.verbose is False
        assert isinstance(indexer.excluded_dirs, set)

    def test_indexer_creates_with_verbose(self):
        """Should create indexer with verbose enabled."""
        indexer = RubySCIPIndexer(verbose=True)
        assert indexer.verbose is True

    def test_get_language_name(self):
        """Should return 'ruby' as language name."""
        indexer = RubySCIPIndexer()
        assert indexer.get_language_name() == "ruby"

    def test_get_file_extensions(self):
        """Should return Ruby file extensions."""
        indexer = RubySCIPIndexer()
        extensions = indexer.get_file_extensions()
        assert ".rb" in extensions
        assert ".rake" in extensions
        assert ".gemspec" in extensions

    def test_get_excluded_dirs(self):
        """Should return excluded directories."""
        indexer = RubySCIPIndexer()
        excluded = indexer.get_excluded_dirs()
        assert "vendor" in excluded
        assert ".bundle" in excluded
        assert "tmp" in excluded
        assert ".git" in excluded


class TestRubySCIPIndexerEnsureInstalled:
    """Test scip-ruby installation checking."""

    def test_ensure_scip_ruby_installed_when_present(self):
        """Should succeed when scip-ruby is already installed."""
        indexer = RubySCIPIndexer()
        with patch(
            "cicada.languages.ruby.scip_installer.SCIPRubyInstaller.is_scip_ruby_installed",
            return_value=True,
        ):
            with patch(
                "cicada.languages.ruby.scip_installer.SCIPRubyInstaller.get_scip_ruby_version",
                return_value="0.3.0",
            ):
                # Should not raise
                indexer._ensure_scip_ruby_installed()

    def test_ensure_scip_ruby_installed_auto_installs(self):
        """Should auto-install scip-ruby when not present."""
        indexer = RubySCIPIndexer()
        with patch(
            "cicada.languages.ruby.scip_installer.SCIPRubyInstaller.is_scip_ruby_installed",
            return_value=False,
        ):
            with patch(
                "cicada.languages.ruby.scip_installer.SCIPRubyInstaller.is_gem_available",
                return_value=True,
            ):
                with patch(
                    "cicada.languages.ruby.scip_installer.SCIPRubyInstaller.install_scip_ruby",
                    return_value=True,
                ):
                    with patch("builtins.print"):
                        indexer._ensure_scip_ruby_installed()

    def test_ensure_scip_ruby_installed_no_gem(self):
        """Should raise RuntimeError when gem is not available."""
        indexer = RubySCIPIndexer()
        with patch(
            "cicada.languages.ruby.scip_installer.SCIPRubyInstaller.is_scip_ruby_installed",
            return_value=False,
        ):
            with patch(
                "cicada.languages.ruby.scip_installer.SCIPRubyInstaller.is_gem_available",
                return_value=False,
            ):
                with pytest.raises(RuntimeError, match="gem is required"):
                    indexer._ensure_scip_ruby_installed()

    def test_ensure_scip_ruby_installed_install_fails(self):
        """Should raise RuntimeError when installation fails."""
        indexer = RubySCIPIndexer()
        with patch(
            "cicada.languages.ruby.scip_installer.SCIPRubyInstaller.is_scip_ruby_installed",
            return_value=False,
        ):
            with patch(
                "cicada.languages.ruby.scip_installer.SCIPRubyInstaller.is_gem_available",
                return_value=True,
            ):
                with patch(
                    "cicada.languages.ruby.scip_installer.SCIPRubyInstaller.install_scip_ruby",
                    return_value=False,
                ):
                    with patch("builtins.print"):
                        with pytest.raises(RuntimeError, match="Failed to install"):
                            indexer._ensure_scip_ruby_installed()


class TestRubySCIPIndexerRunScipRuby:
    """Test running scip-ruby indexer."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Create a temporary Ruby repository."""
        repo = tmp_path / "test_repo"
        repo.mkdir()
        (repo / "test.rb").write_text("class Test\nend")
        return repo

    def test_run_scip_ruby_with_gemfile_uses_bundle(self, temp_repo):
        """Should use bundle exec when Gemfile is present."""
        (temp_repo / "Gemfile").write_text("source 'https://rubygems.org'")
        indexer = RubySCIPIndexer()

        with patch(
            "cicada.languages.ruby.scip_installer.SCIPRubyInstaller.is_bundle_available",
            return_value=True,
        ):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stderr="")

                # Mock the scip file creation
                with patch("tempfile.NamedTemporaryFile") as mock_temp:
                    temp_file = MagicMock()
                    temp_file.name = str(temp_repo / "test.scip")
                    mock_temp.return_value.__enter__.return_value = temp_file

                    # Create the actual file so exists() returns True
                    scip_path = Path(temp_file.name)
                    scip_path.write_text("mock scip content")

                    try:
                        result = indexer._run_scip_ruby(temp_repo)
                        assert "bundle" in mock_run.call_args[0][0]
                        assert "exec" in mock_run.call_args[0][0]
                        assert "scip-ruby" in mock_run.call_args[0][0]
                    finally:
                        if scip_path.exists():
                            scip_path.unlink()

    def test_run_scip_ruby_without_gemfile_uses_direct(self, temp_repo):
        """Should use direct scip-ruby when no Gemfile."""
        indexer = RubySCIPIndexer()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="")

            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                temp_file = MagicMock()
                temp_file.name = str(temp_repo / "test.scip")
                mock_temp.return_value.__enter__.return_value = temp_file

                scip_path = Path(temp_file.name)
                scip_path.write_text("mock scip content")

                try:
                    result = indexer._run_scip_ruby(temp_repo)
                    cmd = mock_run.call_args[0][0]
                    assert cmd[0] == "scip-ruby"
                    assert "bundle" not in cmd
                finally:
                    if scip_path.exists():
                        scip_path.unlink()

    def test_run_scip_ruby_handles_failure(self, temp_repo):
        """Should raise RuntimeError when scip-ruby fails."""
        indexer = RubySCIPIndexer()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="Error message")

            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                temp_file = MagicMock()
                temp_file.name = str(temp_repo / "test.scip")
                mock_temp.return_value.__enter__.return_value = temp_file

                with pytest.raises(RuntimeError, match="scip-ruby indexing failed"):
                    indexer._run_scip_ruby(temp_repo)

    def test_run_scip_ruby_handles_timeout(self, temp_repo):
        """Should raise RuntimeError when scip-ruby times out."""
        indexer = RubySCIPIndexer()

        with patch("subprocess.run") as mock_run:
            import subprocess

            mock_run.side_effect = subprocess.TimeoutExpired("scip-ruby", 600)

            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                temp_file = MagicMock()
                temp_file.name = str(temp_repo / "test.scip")
                mock_temp.return_value.__enter__.return_value = temp_file

                scip_path = Path(temp_file.name)
                scip_path.write_text("mock")

                try:
                    with pytest.raises(RuntimeError, match="timed out"):
                        indexer._run_scip_ruby(temp_repo)
                finally:
                    if scip_path.exists():
                        scip_path.unlink()


class TestRubySCIPIndexerSaveIndex:
    """Test saving index to file."""

    def test_save_index_creates_directory(self, tmp_path):
        """Should create parent directory if it doesn't exist."""
        indexer = RubySCIPIndexer()
        output_path = tmp_path / "nested" / "path" / "index.json"
        index_data = {"modules": {}, "metadata": {}}

        indexer._save_index(index_data, output_path)

        assert output_path.exists()
        assert output_path.parent.exists()

    def test_save_index_writes_json(self, tmp_path):
        """Should write valid JSON to file."""
        import json

        indexer = RubySCIPIndexer()
        output_path = tmp_path / "index.json"
        index_data = {
            "modules": {"TestClass": {"functions": []}},
            "metadata": {"language": "ruby"},
        }

        indexer._save_index(index_data, output_path)

        with open(output_path) as f:
            loaded = json.load(f)
            assert loaded == index_data


class TestRubySCIPIndexerIntegration:
    """Integration tests for the full indexing process."""

    @pytest.fixture
    def sample_ruby_repo(self, fixtures_dir):
        """Path to sample Ruby test fixture."""
        return fixtures_dir / "sample_ruby"

    def test_index_repository_with_mock_scip(self, tmp_path):
        """Should successfully index a repository (mocked)."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        (repo_path / "test.rb").write_text("class Test\nend")

        output_path = tmp_path / "index.json"

        indexer = RubySCIPIndexer(verbose=False)

        # Mock all the dependencies
        with patch.object(indexer, "_ensure_scip_ruby_installed"):
            with patch.object(indexer, "_run_scip_ruby") as mock_run:
                # Create a mock scip file
                scip_file = tmp_path / "test.scip"
                scip_file.write_text("")
                mock_run.return_value = scip_file

                with patch(
                    "cicada.languages.scip.reader.SCIPReader.read_index"
                ) as mock_read:
                    # Mock SCIP index
                    from cicada.languages.scip import scip_pb2

                    mock_index = scip_pb2.Index()
                    mock_doc = mock_index.documents.add()
                    mock_doc.relative_path = "test.rb"
                    mock_read.return_value = mock_index

                    with patch(
                        "cicada.utils.keyword_utils.get_keyword_extractor_from_config"
                    ) as mock_kw:
                        mock_kw.return_value = (False, None)

                        result = indexer.index_repository(
                            repo_path=repo_path,
                            output_path=output_path,
                            verbose=False,
                        )

                        assert result["success"] is True
                        assert output_path.exists()

    def test_index_repository_handles_errors(self, tmp_path):
        """Should handle errors gracefully."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        output_path = tmp_path / "index.json"

        indexer = RubySCIPIndexer(verbose=False)

        with patch.object(indexer, "_ensure_scip_ruby_installed"):
            with patch.object(indexer, "_run_scip_ruby") as mock_run:
                mock_run.side_effect = Exception("Test error")

                result = indexer.index_repository(
                    repo_path=repo_path, output_path=output_path, verbose=False
                )

                assert result["success"] is False
                assert len(result["errors"]) > 0
                assert "Test error" in str(result["errors"][0])
