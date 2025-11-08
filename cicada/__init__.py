"""Cicada - An Elixir module search MCP server."""

import sys
from pathlib import Path

# Python 3.11+ has tomllib built-in, 3.10 needs tomli
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


def _get_version() -> str:
    """
    Read version from build-time generated file, falling back to pyproject.toml.

    During development (before build), reads from pyproject.toml.
    After build/install, uses VERSION baked into _version_hash.py.
    """
    # Try to get version from build-time generated file first
    try:
        from cicada._version_hash import VERSION

        if VERSION and VERSION != "unknown":
            return VERSION
    except (ImportError, AttributeError):
        pass

    # Fallback: read from pyproject.toml (for development)
    if tomllib is None:
        return "unknown"

    try:
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)
            return pyproject_data["project"]["version"]
    except (FileNotFoundError, KeyError, Exception):
        return "unknown"


__version__ = _get_version()
