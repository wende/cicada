"""
Storage management utilities for Cicada.

Handles creation and management of storage directories for index files.
"""

import hashlib
from pathlib import Path


def get_repo_hash(repo_path: str | Path) -> str:
    """
    Generate a unique hash for a repository path.

    Args:
        repo_path: Path to the repository

    Returns:
        Hex string hash of the repository path
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


def get_pr_index_path(repo_path: str | Path) -> Path:
    """
    Get the path to the PR index file for a repository.

    Args:
        repo_path: Path to the repository

    Returns:
        Path to the pr_index.json file
    """
    storage_dir = get_storage_dir(repo_path)
    return storage_dir / "pr_index.json"


def get_link_path(repo_path: str | Path) -> Path:
    """
    Get the path to the link file for a repository.

    Args:
        repo_path: Path to the repository

    Returns:
        Path to the link.yaml file
    """
    storage_dir = get_storage_dir(repo_path)
    return storage_dir / "link.yaml"


def is_linked(repo_path: str | Path) -> bool:
    """
    Check if a repository is linked to another repository.

    Args:
        repo_path: Path to the repository

    Returns:
        True if the repository is linked, False otherwise
    """
    link_path = get_link_path(repo_path)
    return link_path.exists()


def get_link_info(repo_path: str | Path) -> dict | None:
    """
    Get link information for a repository.

    Args:
        repo_path: Path to the repository

    Returns:
        Dictionary with link info (source_repo_path, source_storage_dir, linked_at) or None if not linked
    """
    import yaml

    link_path = get_link_path(repo_path)
    if not link_path.exists():
        return None

    try:
        with open(link_path) as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def resolve_storage_dir(repo_path: str | Path) -> Path:
    """
    Resolve the storage directory for a repository, following links if present.

    Args:
        repo_path: Path to the repository

    Returns:
        Path to the actual storage directory (source if linked, own if not)
    """
    link_info = get_link_info(repo_path)
    if link_info and "source_storage_dir" in link_info:
        return Path(link_info["source_storage_dir"])
    return get_storage_dir(repo_path)


def create_link(target_repo: str | Path, source_repo: str | Path) -> None:
    """
    Create a link from target repository to source repository's index.

    Args:
        target_repo: Path to the target repository (will use source's index)
        source_repo: Path to the source repository (has the index)

    Raises:
        ValueError: If source repository is not indexed or target is already linked
        FileNotFoundError: If source or target repository doesn't exist
    """
    from datetime import datetime, timezone

    import yaml

    # Resolve paths
    target_path = Path(target_repo).resolve()
    source_path = Path(source_repo).resolve()

    # Validate repositories exist
    if not target_path.exists():
        raise FileNotFoundError(f"Target repository not found: {target_path}")
    if not source_path.exists():
        raise FileNotFoundError(f"Source repository not found: {source_path}")

    # Check if source has an index
    source_index_path = get_index_path(source_path)
    if not source_index_path.exists():
        raise ValueError(
            f"Source repository is not indexed: {source_path}\n"
            f"Please run 'cicada index' in the source repository first."
        )

    # Check if target is already linked
    if is_linked(target_path):
        existing_link = get_link_info(target_path)
        raise ValueError(
            f"Target repository is already linked to: {existing_link.get('source_repo_path')}\n"  # type: ignore
            f"Run 'cicada unlink' first to remove the existing link."
        )

    # Create target storage directory if it doesn't exist
    create_storage_dir(target_path)

    # Get source storage directory
    source_storage_dir = get_storage_dir(source_path)

    # Create link file
    link_path = get_link_path(target_path)
    link_data = {
        "source_repo_path": str(source_path),
        "source_storage_dir": str(source_storage_dir),
        "linked_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(link_path, "w") as f:
        yaml.dump(link_data, f, default_flow_style=False)


def remove_link(repo_path: str | Path) -> bool:
    """
    Remove link from a repository.

    Args:
        repo_path: Path to the repository

    Returns:
        True if link was removed, False if no link existed
    """
    link_path = get_link_path(repo_path)
    if not link_path.exists():
        return False

    link_path.unlink()
    return True
