import sys

from cicada.commands import get_argument_parser, handle_command


def main():
    """Main entry point for the unified cicada CLI."""
    if len(sys.argv) > 1:
        first_arg = sys.argv[1]
        known_commands = [
            "install",
            "server",
            "claude",
            "cursor",
            "vs",
            "index",
            "index-pr",
            "find-dead-code",
            "clean",
            "dir",
        ]
        if first_arg in ("--version", "-v"):
            from cicada.version_check import get_version_string

            print(f"cicada {get_version_string()}")
            sys.exit(0)

        if first_arg not in known_commands and not first_arg.startswith("-"):
            sys.argv.insert(1, "install")

    parser = get_argument_parser()
    args = parser.parse_args()

    if not handle_command(args):
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
