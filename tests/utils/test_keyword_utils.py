"""
Tests for cicada/utils/keyword_utils.py
"""

from unittest.mock import patch

import pytest
import yaml

from cicada.utils.keyword_utils import (
    create_keyword_extractor,
    get_keyword_extractor_from_config,
    read_keyword_extraction_config,
)


def test_read_keyword_extraction_default(tmp_path, mock_home_dir):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    extraction_method, expansion_method = read_keyword_extraction_config(repo_path)

    assert extraction_method == "regular"
    assert expansion_method == "lemmi"


def test_read_keyword_extraction_embeddings_raises(tmp_path, mock_home_dir):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    storage_dir = mock_home_dir / ".cicada" / "projects" / "test_hash"
    storage_dir.mkdir(parents=True)
    config_path = storage_dir / "config.yaml"
    config_path.write_text("indexing:\n  mode: embeddings\n")

    with patch("cicada.utils.keyword_utils.get_config_path", return_value=config_path):
        with pytest.raises(NotImplementedError):
            read_keyword_extraction_config(repo_path)


def test_read_keyword_extraction_legacy_config(tmp_path, mock_home_dir):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    storage_dir = mock_home_dir / ".cicada" / "projects" / "test_hash"
    storage_dir.mkdir(parents=True)
    config_path = storage_dir / "config.yaml"

    config = {
        "keyword_extraction": {"method": "regular"},
        "keyword_expansion": {"method": "lemmi"},
    }
    with patch("cicada.utils.keyword_utils.get_config_path", return_value=config_path):
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        extraction_method, expansion_method = read_keyword_extraction_config(repo_path)

    assert extraction_method == "regular"
    assert expansion_method == "lemmi"


def test_create_keyword_extractor_regular():
    extractor = create_keyword_extractor("regular", "lemmi", verbose=False)
    assert extractor is not None


def test_get_keyword_extractor_from_config(tmp_path, mock_home_dir):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    extract_keywords, extractor = get_keyword_extractor_from_config(repo_path, verbose=False)

    assert extract_keywords is True
    assert extractor is not None
