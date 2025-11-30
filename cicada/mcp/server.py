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
from cicada.mcp.config_manager import ConfigManager
from cicada.mcp.router import create_tool_router
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

        # Create router using shared factory
        self.router, self.index_manager, self.git_helper = create_tool_router(self.config)

        # Expose handlers for test access (these are also available via router)
        self.module_handler = self.router.module_handler
        self.function_handler = self.router.function_handler
        self.git_handler = self.router.git_handler
        self.pr_handler = self.router.pr_handler
        self.analysis_handler = self.router.analysis_handler

        # Initialize MCP server
        self.server = Server("cicada")

        # Initialize command logger with repo path for per-project tracking
        repo_path = self.config.get("repository", {}).get("path", ".")
        self.logger = get_logger(repo_path=repo_path)

        # Register handlers
        _ = self.server.list_tools()(self.list_tools)
        _ = self.server.call_tool()(self.call_tool_with_logging)

    async def list_tools(self) -> list[Tool]:
        """List available MCP tools."""
        return get_tool_definitions()

    async def call_tool_with_logging(self, name: str, arguments: dict) -> list[TextContent]:
        """Wrapper for call_tool that logs execution details."""
        # Reload index if it has been modified (e.g., by background refresh)
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

            # Trigger background refresh check after tool completes (non-blocking)
            # This schedules a refresh if source files have changed since last index
            self.index_manager.request_background_refresh_if_stale()

    async def call_tool(self, name: str, arguments: dict) -> list[TextContent]:
        """Handle tool calls."""
        # Route to appropriate handler with callbacks for PR info, staleness, and refresh
        return await self.router.route_tool(
            name=name,
            arguments=arguments,
            pr_info_callback=self.pr_handler.get_recent_pr_info,
            staleness_info_callback=self.index_manager.check_staleness,
            refresh_callback=self.index_manager.force_refresh,
        )

    async def run(self):
        """Run the MCP server."""
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream, write_stream, self.server.create_initialization_options()
                )
        finally:
            # Clean up background refresh manager on shutdown
            self.index_manager.stop_background_refresh()


async def async_main():
    """Async main entry point."""
    import asyncio
    from contextlib import suppress

    # Create a shutdown event for clean async cancellation
    shutdown_event = asyncio.Event()

    loop = asyncio.get_running_loop()

    def request_shutdown(*args, **_kwargs) -> None:
        """Signal the server to shut down."""

        shutdown_event.set()

    try:
        # Check if setup is needed before starting server
        # Redirect stdout to stderr during setup to avoid polluting MCP protocol
        original_stdout = sys.stdout
        try:
            sys.stdout = sys.stderr
            # Pass shutdown_event to allow interruption (e.g., if running in executor or checking later)
            # Note: Standard KeyboardInterrupt handles aborts during synchronous setup
            _auto_setup_if_needed(shutdown_event)
        finally:
            sys.stdout = original_stdout

        if shutdown_event.is_set():
            return

        # Prefer asyncio-native signal handling to avoid race conditions
        # Register handlers AFTER synchronous setup to avoid blocking them or handling signals too early
        signals_to_handle = [signal.SIGINT]
        if hasattr(signal, "SIGTERM"):
            signals_to_handle.append(signal.SIGTERM)

        for sig in signals_to_handle:
            try:
                loop.add_signal_handler(sig, request_shutdown)
            except (NotImplementedError, RuntimeError):
                # Fallback for platforms without add_signal_handler support
                signal.signal(sig, lambda *_: loop.call_soon_threadsafe(request_shutdown))
        server = CicadaServer()

        # Run server with shutdown event monitoring
        server_task = asyncio.create_task(server.run())
        shutdown_task = asyncio.create_task(shutdown_event.wait())

        # Wait for either server completion or shutdown signal
        done, pending = await asyncio.wait(
            [server_task, shutdown_task], return_when=asyncio.FIRST_COMPLETED
        )

        # Propagate exceptions from completed tasks
        for task in done:
            if task.cancelled():
                continue
            exception = task.exception()
            if exception:
                raise exception

        # Cancel any remaining tasks (e.g., server_task during shutdown)
        for task in pending:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    except Exception as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        sys.exit(1)


def _auto_setup_if_needed(shutdown_event=None):
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

    def _ensure_not_shutdown():
        if shutdown_event and shutdown_event.is_set():
            raise KeyboardInterrupt

    _ensure_not_shutdown()

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
    # Validate it's a supported project type
    from cicada.setup import detect_project_language

    _ensure_not_shutdown()

    try:
        language = detect_project_language(repo_path)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    _ensure_not_shutdown()

    try:
        # Create storage directory
        storage_dir = create_storage_dir(repo_path)

        _ensure_not_shutdown()

        # Index repository (silent mode)
        index_repository(repo_path, language, verbose=False)

        _ensure_not_shutdown()

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

    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        # Suppress traceback on Ctrl+C, exit cleanly
        sys.exit(0)


if __name__ == "__main__":
    main()
