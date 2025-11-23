import signal
import sys

from cicada.entry_utils import run_cli


def main() -> None:
    """Main entry point for cicada-mcp command."""

    # Install signal handler early to suppress tracebacks on Ctrl+C
    def signal_handler(signum, _frame):
        """Handle SIGINT/SIGTERM by exiting cleanly without traceback."""
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        run_cli(
            prog_name="cicada-mcp",
            version_prog_name="cicada-mcp",
            default_on_unknown="server",
            default_on_none="server",
            default_on_unknown_args=["--fast"],
            default_on_none_args=["--fast"],
        )
    except KeyboardInterrupt:
        # Suppress traceback on Ctrl+C
        sys.exit(0)


if __name__ == "__main__":
    main()
