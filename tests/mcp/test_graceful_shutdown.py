#!/usr/bin/env python
"""Tests for graceful shutdown behavior in MCP server."""

import asyncio
import signal
from typing import Callable
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_shutdown_event_cancels_server_task(monkeypatch):
    """SIGINT should trigger shutdown_event and cancel the running server task."""
    from cicada.mcp import server as server_module

    # Capture signal callbacks registered by async_main
    loop = asyncio.get_running_loop()
    registered_handlers: dict[signal.Signals, Callable[[], None]] = {}

    def track_add_signal_handler(sig, callback):
        registered_handlers[sig] = callback

    monkeypatch.setattr(loop, "add_signal_handler", track_add_signal_handler)

    # Mock server that waits indefinitely until cancelled
    with patch.object(server_module, "CicadaServer") as mock_server_class:
        mock_server = mock_server_class.return_value
        server_started = asyncio.Event()

        async def mock_run():
            server_started.set()
            await asyncio.Event().wait()

        mock_server.run = AsyncMock(side_effect=mock_run)

        with patch.object(server_module, "_auto_setup_if_needed"):
            main_task = asyncio.create_task(server_module.async_main())

            await asyncio.wait_for(server_started.wait(), timeout=1.0)

            # Simulate SIGINT delivery
            assert signal.SIGINT in registered_handlers
            registered_handlers[signal.SIGINT]()

            await asyncio.wait_for(main_task, timeout=1.0)

    assert main_task.done()
    assert not main_task.cancelled()
    assert mock_server.run.await_count == 1


@pytest.mark.asyncio
async def test_server_exception_propagates_to_sys_exit(monkeypatch):
    """Exceptions from server.run should trigger sys.exit(1)."""
    from cicada.mcp import server as server_module

    with patch.object(server_module, "CicadaServer") as mock_server_class:
        mock_server = mock_server_class.return_value
        mock_server.run = AsyncMock(side_effect=RuntimeError("Test server error"))

        with patch.object(server_module, "_auto_setup_if_needed"):
            with patch("sys.exit") as mock_exit:
                await server_module.async_main()

    mock_exit.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_signal_handlers_use_asyncio_loop(monkeypatch):
    """async_main should register signal handlers via the running loop."""
    from cicada.mcp import server as server_module

    loop = asyncio.get_running_loop()
    signals_registered: list[signal.Signals] = []

    def record_handler(sig, _callback):
        signals_registered.append(sig)

    monkeypatch.setattr(loop, "add_signal_handler", record_handler)

    with patch.object(server_module, "CicadaServer") as mock_server_class:
        mock_server = mock_server_class.return_value
        mock_server.run = AsyncMock(return_value=None)

        with patch.object(server_module, "_auto_setup_if_needed"):
            await server_module.async_main()

    assert signal.SIGINT in signals_registered
    if hasattr(signal, "SIGTERM"):
        assert signal.SIGTERM in signals_registered


@pytest.mark.asyncio
async def test_shutdown_requested_during_setup_aborts(monkeypatch):
    """_auto_setup_if_needed should stop early when shutdown is requested."""
    from cicada.mcp import server as server_module

    shutdown_event = asyncio.Event()
    shutdown_event.set()

    with (
        patch("cicada.setup.detect_project_language") as detect_language,
        patch("cicada.utils.create_storage_dir") as create_storage,
        patch("cicada.setup.index_repository") as index_repo,
        patch("cicada.setup.create_config_yaml") as create_config,
    ):
        with pytest.raises(KeyboardInterrupt):
            server_module._auto_setup_if_needed(shutdown_event)

    detect_language.assert_not_called()
    create_storage.assert_not_called()
    index_repo.assert_not_called()
    create_config.assert_not_called()
