from cicada.entry_utils import run_cli


def main() -> None:
    """Main entry point for cicada-mcp command."""
    run_cli(
        prog_name="cicada-mcp",
        version_prog_name="cicada-mcp",
        default_on_unknown="server",
        default_on_none="server",
        default_on_unknown_args=["--fast"],
        default_on_none_args=["--fast"],
    )


if __name__ == "__main__":
    main()
