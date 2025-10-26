"""
Index file loading and saving utilities.

This module provides centralized functions for loading and saving
JSON index files with consistent error handling.
"""

import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any, Union


def load_index(
    index_path: Union[str, Path],
    verbose: bool = False,
    raise_on_error: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Load a JSON index file.

    Args:
        index_path: Path to the index file
        verbose: If True, print warning messages
        raise_on_error: If True, raise exceptions instead of returning None

    Returns:
        Index dictionary, or None if file doesn't exist or can't be loaded

    Raises:
        FileNotFoundError: If raise_on_error=True and file doesn't exist
        json.JSONDecodeError: If raise_on_error=True and JSON is invalid
        IOError: If raise_on_error=True and file can't be read
    """
    index_file = Path(index_path)

    if not index_file.exists():
        if raise_on_error:
            raise FileNotFoundError(f"Index file not found: {index_path}")
        if verbose:
            print(f"Warning: Index not found at {index_path}", file=sys.stderr)
        return None

    try:
        with open(index_file, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        if raise_on_error:
            raise
        if verbose:
            print(f"Warning: Could not parse index: {e}", file=sys.stderr)
        return None
    except IOError as e:
        if raise_on_error:
            raise
        if verbose:
            print(f"Warning: Could not read index: {e}", file=sys.stderr)
        return None


def save_index(
    index: Dict[str, Any],
    output_path: Union[str, Path],
    indent: int = 2,
    create_dirs: bool = True,
    verbose: bool = False,
) -> None:
    """
    Save an index dictionary to a JSON file.

    Args:
        index: Index dictionary to save
        output_path: Path where the index will be saved
        indent: JSON indentation (default: 2 spaces)
        create_dirs: Create parent directories if they don't exist
        verbose: If True, print confirmation message

    Raises:
        IOError: If file cannot be written
        json.JSONEncodeError: If index cannot be serialized to JSON
    """
    output_file = Path(output_path)

    if create_dirs:
        output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(index, f, indent=indent)

    if verbose:
        print(f"Index saved to: {output_path}")


def validate_index_structure(
    index: Dict[str, Any],
    required_keys: Optional[list[str]] = None,
) -> tuple[bool, Optional[str]]:
    """
    Validate the structure of an index dictionary.

    Args:
        index: Index dictionary to validate
        required_keys: List of required top-level keys (default: ['modules', 'metadata'])

    Returns:
        Tuple of (is_valid, error_message)
        error_message is None if index is valid

    Example:
        valid, error = validate_index_structure(index)
        if not valid:
            print(f"Invalid index: {error}")
    """
    if not isinstance(index, dict):
        return False, "Index must be a dictionary"

    if required_keys is None:
        required_keys = ["modules", "metadata"]

    for key in required_keys:
        if key not in index:
            return False, f"Missing required key: {key}"

    # Validate modules structure
    if "modules" in index and not isinstance(index["modules"], dict):
        return False, "'modules' must be a dictionary"

    # Validate metadata structure
    if "metadata" in index and not isinstance(index["metadata"], dict):
        return False, "'metadata' must be a dictionary"

    return True, None


def merge_indexes(
    *indexes: Dict[str, Any],
    strategy: str = "last_wins",
) -> Dict[str, Any]:
    """
    Merge multiple index dictionaries.

    Args:
        *indexes: Variable number of index dictionaries to merge
        strategy: Merge strategy ('last_wins' or 'first_wins')
            - 'last_wins': Later indexes override earlier ones
            - 'first_wins': Earlier indexes take precedence

    Returns:
        Merged index dictionary

    Example:
        merged = merge_indexes(index1, index2, index3, strategy='last_wins')
    """
    if not indexes:
        return {}

    # Start with empty structure
    merged = {
        "modules": {},
        "metadata": {},
    }

    if strategy == "last_wins":
        index_list = list(indexes)
    elif strategy == "first_wins":
        index_list = list(reversed(indexes))
    else:
        raise ValueError(f"Unknown merge strategy: {strategy}")

    # Merge modules
    for index in index_list:
        if "modules" in index:
            merged["modules"].update(index["modules"])

    # Merge metadata (later ones override)
    for index in index_list:
        if "metadata" in index:
            merged["metadata"].update(index["metadata"])

    return merged


def get_index_stats(index: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get statistics about an index.

    Args:
        index: Index dictionary

    Returns:
        Dictionary with statistics:
        - total_modules: Number of modules
        - total_functions: Total function count
        - public_functions: Public function count
        - private_functions: Private function count

    Example:
        stats = get_index_stats(index)
        print(f"Index contains {stats['total_modules']} modules")
    """
    stats = {
        "total_modules": 0,
        "total_functions": 0,
        "public_functions": 0,
        "private_functions": 0,
    }

    if "modules" not in index:
        return stats

    modules = index["modules"]
    stats["total_modules"] = len(modules)

    for module_data in modules.values():
        if "functions" in module_data:
            functions = module_data["functions"]
            stats["total_functions"] += len(functions)

            for func in functions:
                if func.get("type") == "def":
                    stats["public_functions"] += 1
                elif func.get("type") == "defp":
                    stats["private_functions"] += 1

    return stats
