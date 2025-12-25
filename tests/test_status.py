"""Tests for cicada/status.py (indexing mode reporting)."""

from pathlib import Path
from unittest.mock import patch


def test_get_index_info_no_index(tmp_path):
    from cicada.status import get_index_info

    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    with (
        patch("cicada.status.get_index_path", return_value=repo_path / "index.json"),
        patch("cicada.status.get_config_path", return_value=repo_path / "config.yaml"),
    ):
        info = get_index_info(repo_path)

    assert info["exists"] is False
    assert info["mode"] is None


def test_get_index_info_with_mode(tmp_path):
    from cicada.status import get_index_info

    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    index_path = repo_path / "index.json"
    index_path.write_text("{}")
    config_path = repo_path / "config.yaml"
    config_path.write_text("indexing:\n  mode: embeddings\n")

    with (
        patch("cicada.status.get_index_path", return_value=index_path),
        patch("cicada.status.get_config_path", return_value=config_path),
    ):
        info = get_index_info(repo_path)

    assert info["exists"] is True
    assert info["mode"] == "embeddings"


def test_get_index_info_legacy_config_maps_keywords(tmp_path):
    from cicada.status import get_index_info

    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    index_path = repo_path / "index.json"
    index_path.write_text("{}")
    config_path = repo_path / "config.yaml"
    config_path.write_text("keyword_extraction:\n  method: regular\n")

    with (
        patch("cicada.status.get_index_path", return_value=index_path),
        patch("cicada.status.get_config_path", return_value=config_path),
    ):
        info = get_index_info(repo_path)

    assert info["mode"] == "keywords"
