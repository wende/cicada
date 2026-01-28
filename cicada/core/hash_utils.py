"""
Utilities for computing and managing file hashes for incremental indexing.

This module provides MD5-based file hashing to detect changes in the codebase
and enable incremental reindexing, avoiding reprocessing of unchanged files.
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def compute_file_hash(file_path: str) -> str:
    """
    Compute MD5 hash of a file's content.

    Args:
        file_path: Path to the file to hash

    Returns:
        MD5 hash as hexadecimal string

    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file cannot be read
    """
    # Note: MD5 is used here for speed, not security. This is for content-based
    # change detection, not cryptographic purposes. MD5 is significantly faster
    # than SHA256 and collision risk is negligible for our use case.
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            # Read in chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}") from None
    except Exception as e:
        raise OSError(f"Error reading file {file_path}: {e}") from e


def load_file_hashes(path: str) -> dict[str, str]:
    """
    Load file hashes from a hashes.json file.

    Args:
        path: Path to the hashes.json file OR the directory containing it.
              If a directory is passed, appends 'hashes.json' for backwards compatibility.

    Returns:
        Dictionary mapping file paths to MD5 hashes.
        Returns empty dict if hashes.json doesn't exist.
    """
    hashes_path = Path(path)
    # Backwards compatibility: if directory passed, append hashes.json
    if hashes_path.is_dir() or not str(path).endswith(".json"):
        hashes_path = hashes_path / "hashes.json"

    if not hashes_path.exists():
        return {}

    try:
        with open(hashes_path, encoding="utf-8") as f:
            data = json.load(f)
            return data.get("hashes", {})
    except (OSError, json.JSONDecodeError) as e:
        print(f"Warning: Could not load hashes.json: {e}")
        return {}


def save_file_hashes(path: str, hashes: dict[str, str]) -> None:
    """
    Save file hashes to a hashes.json file.

    Args:
        path: Path to the hashes.json file OR the directory containing it.
              If a directory is passed, appends 'hashes.json' for backwards compatibility.
        hashes: Dictionary mapping file paths to MD5 hashes
    """
    hashes_path = Path(path)
    # Backwards compatibility: if directory passed, append hashes.json
    if hashes_path.is_dir() or not str(path).endswith(".json"):
        hashes_path = hashes_path / "hashes.json"

    # Ensure parent directory exists
    os.makedirs(hashes_path.parent, exist_ok=True)

    data = {
        "version": "1.0",
        "hashes": hashes,
        "last_updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    try:
        with open(hashes_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        print(f"Warning: Could not save hashes.json: {e}")


def detect_file_changes(
    files: list[str], old_hashes: dict[str, str], repo_path: str | None = None
) -> tuple[list[str], list[str], list[str]]:
    """
    Detect new, modified, and deleted files by comparing hashes.

    Args:
        files: List of current file paths (relative to repo root)
        old_hashes: Dictionary of file paths to their previous MD5 hashes
        repo_path: Optional repository root path. If provided, file paths
                   will be resolved relative to this path.

    Returns:
        Tuple of (new_files, modified_files, deleted_files)
        - new_files: Files that didn't exist in old_hashes
        - modified_files: Files whose hash changed
        - deleted_files: Files in old_hashes but not in current files list
    """
    new_files = []
    modified_files = []

    current_file_set = set(files)
    old_file_set = set(old_hashes.keys())

    # Detect deleted files
    deleted_files = list(old_file_set - current_file_set)

    # Detect new and modified files
    for file_path in files:
        # Resolve full path if repo_path provided
        full_path = os.path.join(repo_path, file_path) if repo_path else file_path

        if file_path not in old_hashes:
            # New file
            new_files.append(file_path)
        else:
            # Check if modified
            # Note: Race condition possible if file modified between this check
            # and actual indexing, but impact is minimal (re-detected next run)
            try:
                current_hash = compute_file_hash(full_path)
                if current_hash != old_hashes[file_path]:
                    modified_files.append(file_path)
            except (OSError, FileNotFoundError) as e:
                # File might have been deleted after listing
                print(f"Warning: Could not hash {file_path}: {e}")
                deleted_files.append(file_path)

    return new_files, modified_files, deleted_files


def compute_hashes_for_files(files: list[str], repo_path: str | None = None) -> dict[str, str]:
    """
    Compute MD5 hashes for a list of files.

    Args:
        files: List of file paths (relative to repo root)
        repo_path: Optional repository root path. If provided, file paths
                   will be resolved relative to this path.

    Returns:
        Dictionary mapping file paths to MD5 hashes
    """
    hashes = {}

    for file_path in files:
        # Resolve full path if repo_path provided
        full_path = os.path.join(repo_path, file_path) if repo_path else file_path

        try:
            hashes[file_path] = compute_file_hash(full_path)
        except (OSError, FileNotFoundError) as e:
            print(f"Warning: Could not hash {file_path}: {e}")

    return hashes
