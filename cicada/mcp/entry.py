import sys

from cicada.entry_utils import run_cli


def main() -> None:
    """Main entry point for cicada-mcp command."""

    try:
        run_cli(
            prog_name="cicada-mcp",
            version_prog_name="cicada-mcp",
            default_on_unknown="server",
            default_on_none="server",
            default_on_unknown_args=["--keywords"],
            default_on_none_args=["--keywords"],
        )
    except KeyboardInterrupt:
        # Suppress traceback on Ctrl+C while allowing command-level cleanup
        sys.exit(0)


if __name__ == "__main__":
    main()
