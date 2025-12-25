"""
Tests for setup helpers with indexing mode configuration.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch


def test_create_config_yaml_defaults(tmp_path):
    from cicada.setup import create_config_yaml

    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()

    with (
        patch("cicada.setup.get_config_path", return_value=storage_dir / "config.yaml"),
        patch("cicada.setup.get_index_path", return_value=storage_dir / "index.json"),
    ):
        create_config_yaml(repo_path, storage_dir, verbose=False)

    config_content = (storage_dir / "config.yaml").read_text()
    assert "indexing:" in config_content
    assert "mode: keywords" in config_content


def test_create_config_yaml_embeddings(tmp_path):
    from cicada.setup import create_config_yaml

    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()

    with (
        patch("cicada.setup.get_config_path", return_value=storage_dir / "config.yaml"),
        patch("cicada.setup.get_index_path", return_value=storage_dir / "index.json"),
    ):
        create_config_yaml(repo_path, storage_dir, indexing_mode="embeddings", verbose=False)

    config_content = (storage_dir / "config.yaml").read_text()
    assert "mode: embeddings" in config_content


def test_setup_passes_indexing_mode(tmp_path):
    from cicada.setup import setup

    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "mix.exs").touch()
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()

    with (
        patch("cicada.setup.detect_project_language", return_value="elixir"),
        patch("cicada.setup.create_storage_dir", return_value=storage_dir),
        patch("cicada.setup.get_config_path", return_value=storage_dir / "config.yaml"),
        patch("cicada.setup.get_index_path", return_value=storage_dir / "index.json"),
        patch("cicada.setup.create_config_yaml") as mock_create,
    ):
        setup("claude", repo_path, indexing_mode="keywords", index_exists=True)

    call_args = mock_create.call_args[0]
    assert call_args[2] == "keywords"
