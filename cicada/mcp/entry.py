import sys

from cicada.entry_utils import run_cli


def main() -> None:
    """Main entry point for cicada-mcp command."""

    # Install custom exception hook to suppress KeyboardInterrupt tracebacks
    def exception_hook(exc_type, exc_value, exc_traceback):
        """Custom exception hook that suppresses KeyboardInterrupt tracebacks."""
        if exc_type is KeyboardInterrupt:
            # Exit cleanly without printing traceback
            sys.exit(0)
        # For other exceptions, use default behavior
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = exception_hook

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
