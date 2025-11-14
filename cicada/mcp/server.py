#!/usr/bin/env python
"""
Cicada MCP Server - Elixir Module Search.

Provides an MCP tool to search for Elixir modules and their functions.

Author: Cursor(Auto)
"""

import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from cicada.command_logger import get_logger
from cicada.git import GitHelper
from cicada.mcp.config_manager import ConfigManager
from cicada.mcp.handlers import (
    AnalysisHandler,
    DependencyHandler,
    FunctionSearchHandler,
    GitHistoryHandler,
    ModuleSearchHandler,
    PRHistoryHandler,
)
from cicada.mcp.handlers.index_manager import IndexManager
from cicada.mcp.router import ToolRouter
from cicada.mcp.tools import get_tool_definitions


class CicadaServer:
    """MCP server for Elixir module search."""

    def __init__(self, config_path: str | None = None):
        """
        Initialize the server with configuration.

        Args:
            config_path: Path to config file. If None, uses environment variables
                        or default path.
        """
        # Load configuration
        if config_path is None:
            config_path = ConfigManager.get_config_path()
        self.config = ConfigManager.load_config(config_path)

        # Initialize index manager
        self.index_manager = IndexManager(self.config)

        # Initialize git helper
        repo_path = self.config.get("repository", {}).get("path", ".")
        self.git_helper: GitHelper | None = None
        try:
            self.git_helper = GitHelper(repo_path)
        except Exception as e:
            # If git initialization fails, set to None
            # (e.g., not a git repository)
            print(f"Warning: Git helper not available: {e}", file=sys.stderr)

        # Initialize handlers
        self.module_handler = ModuleSearchHandler(self.index_manager.index, self.config)
        self.function_handler = FunctionSearchHandler(self.index_manager.index, self.config)
        self.git_handler = GitHistoryHandler(self.git_helper, self.config)
        self.pr_handler = PRHistoryHandler(self.index_manager.pr_index, self.config)
        self.dependency_handler = DependencyHandler(self.index_manager.index, self.config)
        self.analysis_handler = AnalysisHandler(
            self.index_manager.index, self.index_manager.has_keywords
        )

        # Initialize router
        self.router = ToolRouter(
            module_handler=self.module_handler,
            function_handler=self.function_handler,
            git_handler=self.git_handler,
            pr_handler=self.pr_handler,
            dependency_handler=self.dependency_handler,
            analysis_handler=self.analysis_handler,
        )

        # Initialize MCP server
        self.server = Server("cicada")

        # Initialize command logger
        self.logger = get_logger()

        # Register handlers
        _ = self.server.list_tools()(self.list_tools)
        _ = self.server.call_tool()(self.call_tool_with_logging)

    async def list_tools(self) -> list[Tool]:
        """List available MCP tools."""
        return get_tool_definitions()

    async def call_tool_with_logging(self, name: str, arguments: dict) -> list[TextContent]:
        """Wrapper for call_tool that logs execution details."""
        # Reload index if it has been modified
        self.index_manager.reload_if_changed()

        # Record start time
        start_time = time.perf_counter()
        timestamp = datetime.now()
        error_msg = None
        response = None

        try:
            # Call the actual tool handler
            response = await self.call_tool(name, arguments)
            return response
        except Exception as e:
            # Capture error if tool execution fails
            error_msg = str(e)
            raise
        finally:
            # Calculate execution time in milliseconds
            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000

            # Log the command execution (async to prevent event loop blocking)
            await self.logger.log_command_async(
                tool_name=name,
                arguments=arguments,
                response=response,
                execution_time_ms=execution_time_ms,
                timestamp=timestamp,
                error=error_msg,
            )

    async def call_tool(self, name: str, arguments: dict) -> list[TextContent]:
        """Handle tool calls."""
        # Route to appropriate handler with callbacks for PR info and staleness check
        return await self.router.route_tool(
            name=name,
            arguments=arguments,
            pr_info_callback=self.pr_handler.get_recent_pr_info,
            staleness_info_callback=self.index_manager.check_staleness,
        )

    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream, write_stream, self.server.create_initialization_options()
            )


async def async_main():
    """Async main entry point."""

    # Set up signal handlers for clean shutdown
    def signal_handler(signum, _frame):
        """Handle signals by exiting cleanly."""
        print(f"Received signal {signum}, shutting down...", file=sys.stderr)
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Check if setup is needed before starting server
        # Redirect stdout to stderr during setup to avoid polluting MCP protocol
        original_stdout = sys.stdout
        try:
            sys.stdout = sys.stderr
            _auto_setup_if_needed()
        finally:
            sys.stdout = original_stdout

        server = CicadaServer()
        await server.run()
    except KeyboardInterrupt:
        print("Server interrupted, shutting down...", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        sys.exit(1)


def _auto_setup_if_needed():
    """
    Automatically run setup if the repository hasn't been indexed yet.

    This enables zero-config MCP usage - just point the MCP config to cicada-server
    and it will index the repository on first run.
    """
    from cicada.setup import create_config_yaml, index_repository
    from cicada.utils import (
        create_storage_dir,
        get_config_path,
        get_index_path,
    )

    # Determine repository path from environment or current directory
    repo_path_str = None

    # First check if repo path was provided via positional argument (internal env var)
    repo_path_str = os.environ.get("_CICADA_REPO_PATH_ARG")

    # Fall back to WORKSPACE_FOLDER_PATHS (Cursor-specific)
    if not repo_path_str:
        workspace_paths = os.environ.get("WORKSPACE_FOLDER_PATHS")
        if workspace_paths:
            # WORKSPACE_FOLDER_PATHS might be a single path or multiple paths
            # Take the first one if multiple
            # Use os.pathsep for platform-aware splitting (';' on Windows, ':' on Unix)
            repo_path_str = (
                workspace_paths.split(os.pathsep)[0]
                if os.pathsep in workspace_paths
                else workspace_paths
            )

    repo_path = Path(repo_path_str).resolve() if repo_path_str else Path.cwd().resolve()

    # Check if config and index already exist
    config_path = get_config_path(repo_path)
    index_path = get_index_path(repo_path)

    if config_path.exists() and index_path.exists():
        # Already set up, nothing to do
        return

    # Setup needed - create storage and index (silent mode)
    # Validate it's an Elixir project
    if not (repo_path / "mix.exs").exists():
        print(
            f"Error: {repo_path} does not appear to be an Elixir project (mix.exs not found)",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        # Create storage directory
        storage_dir = create_storage_dir(repo_path)

        # Index repository (silent mode)
        index_repository(repo_path, verbose=False)

        # Create config.yaml (silent mode)
        create_config_yaml(repo_path, storage_dir, verbose=False)

    except Exception as e:
        print(f"Cicada auto-setup error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Synchronous entry point for use with setuptools console_scripts."""
    import asyncio
    import sys

    # Accept optional positional argument for repo path
    if len(sys.argv) > 1:
        repo_path = sys.argv[1]
        # Convert to absolute path
        from pathlib import Path

        from cicada.utils.storage import resolve_storage_dir

        abs_path = Path(repo_path).resolve()
        # Set environment variables for both storage directory and repo path
        # The repo path is needed by _auto_setup_if_needed() for first-time setup
        # resolve_storage_dir will follow links if the repository is linked
        storage_dir = resolve_storage_dir(abs_path)
        os.environ["CICADA_CONFIG_DIR"] = str(storage_dir)
        os.environ["_CICADA_REPO_PATH_ARG"] = str(abs_path)

    asyncio.run(async_main())


if __name__ == "__main__":
    main()
