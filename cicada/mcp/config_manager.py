"""
Configuration Management for Cicada MCP Server.

Handles loading and resolving configuration paths.
"""

import os
from pathlib import Path

import yaml

from cicada.utils import get_config_path


class ConfigManager:
    """Manages configuration loading and path resolution."""

    @staticmethod
    def get_config_path() -> str:
        """
        Determine the config file path from environment or defaults.

        Returns:
            Path to the config file
        """
        # Check if CICADA_CONFIG_DIR is set (direct path to storage directory)
        config_dir = os.environ.get("CICADA_CONFIG_DIR")
        if config_dir:
            # Check if this storage directory contains a link
            storage_path = Path(config_dir)
            link_file = storage_path / "link.yaml"

            if link_file.exists():
                # This is a linked repository - resolve to source storage
                try:
                    with open(link_file) as f:
                        link_data = yaml.safe_load(f)
                        if link_data and "source_storage_dir" in link_data:
                            source_dir = link_data["source_storage_dir"]
                            # Validate value is a non-empty string
                            if isinstance(source_dir, str) and source_dir.strip():
                                # Use the source storage directory's config
                                return str(Path(source_dir) / "config.yaml")
                except (yaml.YAMLError, OSError, KeyError, TypeError):
                    # If link is corrupted, fall through to using config_dir directly
                    pass

            return str(Path(config_dir) / "config.yaml")

        # Determine repository path from environment or current directory
        repo_path = None

        # Check if WORKSPACE_FOLDER_PATHS is available (Cursor-specific)
        workspace_paths = os.environ.get("WORKSPACE_FOLDER_PATHS")
        if workspace_paths:
            # WORKSPACE_FOLDER_PATHS might be a single path or multiple paths
            # Take the first one if multiple
            # Use os.pathsep for platform-aware splitting (';' on Windows, ':' on Unix)
            repo_path = (
                workspace_paths.split(os.pathsep)[0]
                if os.pathsep in workspace_paths
                else workspace_paths
            )

        # Fall back to current working directory
        if not repo_path:
            repo_path = str(Path.cwd().resolve())

        # Calculate config path from repository path
        config_path = get_config_path(repo_path)
        return str(config_path)

    @staticmethod
    def load_config(config_path: str) -> dict:
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to the configuration file

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(
                f"Config file not found: {config_path}\n\n"
                f"Please run setup first:\n"
                f"  cicada cursor  # For Cursor\n"
                f"  cicada claude  # For Claude Code\n"
                f"  cicada vs      # For VS Code"
            )

        with open(config_file) as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
