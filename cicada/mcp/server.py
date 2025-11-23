async def async_main():
    """Async main entry point."""
    import asyncio
    from contextlib import suppress

    # Create a shutdown event for clean async cancellation
    shutdown_event = asyncio.Event()

    loop = asyncio.get_running_loop()

    def request_shutdown() -> None:
        """Signal the server to shut down."""

        shutdown_event.set()

    try:
        # Check if setup is needed before starting server
        # Redirect stdout to stderr during setup to avoid polluting MCP protocol
        original_stdout = sys.stdout
        try:
            sys.stdout = sys.stderr
            _auto_setup_if_needed(shutdown_event)
        finally:
            sys.stdout = original_stdout

        if shutdown_event.is_set():
            return

        # Prefer asyncio-native signal handling to avoid race conditions
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
