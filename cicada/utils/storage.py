"""
Storage management utilities for Cicada.

Handles creation and management of storage directories for index files.
"""

import hashlib
from pathlib import Path
from typing import TypedDict


class LinkInfo(TypedDict):
    """Type definition for link information."""

    source_repo_path: str
    source_storage_dir: str
    linked_at: str


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

    If the repository is linked, returns the path to the source repository's index.

    Args:
        repo_path: Path to the repository

    Returns:
        Path to the index.json file
    """
    storage_dir = resolve_storage_dir(repo_path)
    return storage_dir / "index.json"


def get_config_path(repo_path: str | Path) -> Path:
    """
    Get the path to the config file for a repository.

    If the repository is linked, returns the path to the source repository's config.

    Args:
        repo_path: Path to the repository

    Returns:
        Path to the config.yaml file
    """
    storage_dir = resolve_storage_dir(repo_path)
    return storage_dir / "config.yaml"


def get_hashes_path(repo_path: str | Path) -> Path:
    """
    Get the path to the hashes file for a repository.

    If the repository is linked, returns the path to the source repository's hashes.

    Args:
        repo_path: Path to the repository

    Returns:
        Path to the hashes.json file
    """
    storage_dir = resolve_storage_dir(repo_path)
    return storage_dir / "hashes.json"


def get_pr_index_path(repo_path: str | Path) -> Path:
    """
    Get the path to the PR index file for a repository.

    If the repository is linked, returns the path to the source repository's PR index.

    Args:
        repo_path: Path to the repository

    Returns:
        Path to the pr_index.json file
    """
    storage_dir = resolve_storage_dir(repo_path)
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


def get_link_info(repo_path: str | Path) -> LinkInfo | None:
    """
    Get link information for a repository.

    Args:
        repo_path: Path to the repository

    Returns:
        LinkInfo dictionary with link info (source_repo_path, source_storage_dir, linked_at) or None if not linked
    """
    import yaml

    link_path = get_link_path(repo_path)
    if not link_path.exists():
        return None

    try:
        with open(link_path) as f:
            return yaml.safe_load(f)
    except (yaml.YAMLError, OSError, KeyError):
        # Return None for corrupted YAML, I/O errors, or missing keys
        return None


def resolve_storage_dir(repo_path: str | Path) -> Path:
    """Resolve the storage directory for a repository, following link chains if present."""

    current_repo = Path(repo_path).resolve()
    visited: set[str] = set()
    last_link_info: LinkInfo | None = None
    missing_storage: Path | None = None

    while True:
        repo_key = str(current_repo)
        if repo_key in visited:
            break
        visited.add(repo_key)

        link_info = get_link_info(current_repo)
        if not link_info:
            return get_storage_dir(current_repo)

        last_link_info = link_info

        source_storage_dir = link_info.get("source_storage_dir")
        if isinstance(source_storage_dir, str) and source_storage_dir.strip():
            source_storage = Path(source_storage_dir)
            if (source_storage / "index.json").exists():
                return source_storage
            # Broken link detected - raise immediately
            source_repo = link_info.get("source_repo_path", "unknown")
            raise ValueError(
                f"Link is broken: source index not found at {source_storage}\n"
                f"Source repository: {source_repo}\n"
                f"Run 'cicada unlink' to remove the broken link, then re-index or re-link."
            )

        source_repo_path = link_info.get("source_repo_path")
        if source_repo_path:
            current_repo = Path(source_repo_path).resolve()
            continue

        break

    source_repo = last_link_info.get("source_repo_path", "unknown") if last_link_info else "unknown"

    if missing_storage is None and last_link_info:
        raw_path = last_link_info.get("source_storage_dir")
        if isinstance(raw_path, str) and raw_path.strip():
            missing_storage = Path(raw_path)

    if missing_storage is None:
        missing_storage = get_storage_dir(current_repo)

    raise ValueError(
        f"Link is broken: source index not found at {missing_storage}\n"
        f"Source repository: {source_repo}\n"
        f"Run 'cicada unlink' to remove the broken link, then re-index or re-link."
    )


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
        source_path_str = (
            existing_link.get("source_repo_path", "unknown") if existing_link else "unknown"
        )
        raise ValueError(
            f"Target repository is already linked to: {source_path_str}\n"
            f"Run 'cicada unlink' first to remove the existing link."
        )

    # Check for circular links: prevent cycles of any length (A → B → ... → A)
    def detect_cycle(start_path: Path, target_path: Path) -> bool:
        """
        Detect if linking target_path to start_path would create a cycle.
        Follows the chain of links from start_path and checks if target_path is encountered.
        """
        visited = set()
        current_path = start_path
        while True:
            if current_path.resolve() == target_path.resolve():
                return True
            if str(current_path.resolve()) in visited:
                # Already visited, break to avoid infinite loop
                break
            visited.add(str(current_path.resolve()))
            link_info = get_link_info(current_path)
            if not link_info:
                break
            next_repo_path = link_info.get("source_repo_path")
            if not next_repo_path:
                break
            current_path = Path(next_repo_path)
        return False

    if detect_cycle(source_path, target_path):
        raise ValueError(
            f"Cannot create circular link: linking '{target_path.name}' to '{source_path.name}' "
            f"would create a cycle in the repository links.\n"
            f"This would create a circular reference."
        )

    # Create target storage directory if it doesn't exist
    create_storage_dir(target_path)

    # Get source storage directory (resolve to handle chained links)
    source_storage_dir = resolve_storage_dir(source_path)

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
