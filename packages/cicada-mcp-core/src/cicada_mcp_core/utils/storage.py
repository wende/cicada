"""
Storage management utilities for Cicada.

Handles creation and management of storage directories for index files.
This is the core storage module - linking functionality is in main cicada.
"""

import hashlib
from pathlib import Path


def get_repo_hash(repo_path: str | Path) -> str:
    """
    Generate a unique hash for a repository path.

    Args:
        repo_path: Path to the repository

    Returns:
        Hex string hash of the repository path (16 chars)
    """
    repo_path_str = str(Path(repo_path).resolve())
    return hashlib.sha256(repo_path_str.encode()).hexdigest()[:16]


def get_storage_dir(repo_path: str | Path) -> Path:
    """
    Get the storage directory for a repository.

    Storage structure:
        ~/.cicada/projects/<repo_hash>/

    Args:
        repo_path: Path to the repository

    Returns:
        Path to the storage directory for this repository
    """
    repo_hash = get_repo_hash(repo_path)
    storage_dir = Path.home() / ".cicada" / "projects" / repo_hash
    return storage_dir


def create_storage_dir(repo_path: str | Path) -> Path:
    """
    Create the storage directory for a repository if it doesn't exist.

    Args:
        repo_path: Path to the repository

    Returns:
        Path to the created storage directory
    """
    storage_dir = get_storage_dir(repo_path)
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


def get_index_path(repo_path: str | Path) -> Path:
    """
    Get the path to the index file for a repository.

    Args:
        repo_path: Path to the repository

    Returns:
        Path to the index.json file
    """
    storage_dir = get_storage_dir(repo_path)
    return storage_dir / "index.json"


def get_config_path(repo_path: str | Path) -> Path:
    """
    Get the path to the config file for a repository.

    Args:
        repo_path: Path to the repository

    Returns:
        Path to the config.yaml file
    """
    storage_dir = get_storage_dir(repo_path)
    return storage_dir / "config.yaml"


def get_hashes_path(repo_path: str | Path) -> Path:
    """
    Get the path to the hashes file for a repository.

    Args:
        repo_path: Path to the repository

    Returns:
        Path to the hashes.json file
    """
    storage_dir = get_storage_dir(repo_path)
    return storage_dir / "hashes.json"
