from cicada.entry_utils import run_cli


def main():
    """Main entry point for the unified cicada CLI."""
    run_cli(
        prog_name="cicada",
        version_prog_name="cicada",
        default_on_unknown="install",
        default_on_none="install",
    )


if __name__ == "__main__":
    main()
