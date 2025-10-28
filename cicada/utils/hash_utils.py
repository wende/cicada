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
from typing import Dict, List, Tuple


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
        raise FileNotFoundError(f"File not found: {file_path}")
    except Exception as e:
        raise IOError(f"Error reading file {file_path}: {e}")


def load_file_hashes(cicada_dir: str) -> Dict[str, str]:
    """
    Load file hashes from .cicada/hashes.json.

    Args:
        cicada_dir: Path to the .cicada directory

    Returns:
        Dictionary mapping file paths to MD5 hashes.
        Returns empty dict if hashes.json doesn't exist.
    """
    hashes_path = Path(cicada_dir) / "hashes.json"

    if not hashes_path.exists():
        return {}

    try:
        with open(hashes_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("hashes", {})
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not load hashes.json: {e}")
        return {}


def save_file_hashes(cicada_dir: str, hashes: Dict[str, str]) -> None:
    """
    Save file hashes to .cicada/hashes.json.

    Args:
        cicada_dir: Path to the .cicada directory
        hashes: Dictionary mapping file paths to MD5 hashes
    """
    hashes_path = Path(cicada_dir) / "hashes.json"

    # Ensure .cicada directory exists
    os.makedirs(cicada_dir, exist_ok=True)

    data = {
        "version": "1.0",
        "hashes": hashes,
        "last_updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    try:
        with open(hashes_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        print(f"Warning: Could not save hashes.json: {e}")


def detect_file_changes(
    files: List[str], old_hashes: Dict[str, str], repo_path: str | None = None
) -> Tuple[List[str], List[str], List[str]]:
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
            except (FileNotFoundError, IOError) as e:
                # File might have been deleted after listing
                print(f"Warning: Could not hash {file_path}: {e}")
                deleted_files.append(file_path)

    return new_files, modified_files, deleted_files


def compute_hashes_for_files(
    files: List[str], repo_path: str | None = None
) -> Dict[str, str]:
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
        except (FileNotFoundError, IOError) as e:
            print(f"Warning: Could not hash {file_path}: {e}")

    return hashes
