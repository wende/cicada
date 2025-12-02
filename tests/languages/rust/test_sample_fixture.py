"""Tests that exercise the sample_rust fixture to guide upcoming Rust work."""

from pathlib import Path

import pytest

from cicada.languages.rust.indexer import RustSCIPIndexer


@pytest.fixture
def sample_rust_repo(fixtures_dir) -> Path:
    repo = fixtures_dir / "sample_rust"
    if not repo.exists():
        pytest.skip("sample_rust fixture is missing")
    return repo


def test_indexer_discovers_rust_sources(sample_rust_repo):
    """_find_source_files should return the .rs files in src/ (and nowhere else)."""
    indexer = RustSCIPIndexer()
    files = indexer._find_source_files(sample_rust_repo)

    relative_paths = [path.relative_to(sample_rust_repo) for path in files]
    assert relative_paths == [
        Path("src/lib.rs"),
        Path("src/operations.rs"),
        Path("src/utils.rs"),
    ]


def test_indexer_skips_target_directory(sample_rust_repo):
    """Ensure the indexer never recurses into the Cargo target directory."""
    indexer = RustSCIPIndexer()
    files = indexer._find_source_files(sample_rust_repo)

    for file_path in files:
        assert "target" not in file_path.parts
