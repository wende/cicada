from __future__ import annotations

import sys
from collections.abc import Callable, Sequence

from cicada import commands as _commands_module
from cicada.logging_utils import configure_logging, get_verbose_flag

KNOWN_SUBCOMMANDS_SET = getattr(_commands_module, "KNOWN_SUBCOMMANDS_SET", frozenset())
get_argument_parser = _commands_module.get_argument_parser
handle_command = _commands_module.handle_command

DefaultResolver = Callable[[], str | None] | str | None


def prepare_argv(
    argv: Sequence[str],
    *,
    default_on_unknown: str | None,
    default_on_none: DefaultResolver,
    default_on_unknown_args: Sequence[str] | None = None,
    default_on_none_args: Sequence[str] | None = None,
) -> list[str]:
    """
    Normalize argv so both entry points share identical subcommand routing.

    - If the first argument is an unknown token (and not a flag), inject the default subcommand and any associated args.
    - If no arguments are provided, append the default-on-none subcommand (with optional extra args).
    """
    normalized = list(argv)

    if len(normalized) > 1:
        first_arg = normalized[1]
        if (
            default_on_unknown
            and first_arg not in KNOWN_SUBCOMMANDS_SET
            and not first_arg.startswith("-")
        ):
            extras = list(default_on_unknown_args or ())
            normalized[1:1] = [default_on_unknown, *extras]
    elif len(normalized) == 1:
        default_command = _resolve_default(default_on_none)
        if default_command:
            extras = list(default_on_none_args or ())
            normalized.append(default_command)
            if extras:
                normalized.extend(extras)

    return normalized


def run_cli(
    *,
    prog_name: str,
    version_prog_name: str,
    default_on_unknown: str | None,
    default_on_none: DefaultResolver,
    default_on_unknown_args: Sequence[str] | None = None,
    default_on_none_args: Sequence[str] | None = None,
) -> None:
    """Shared entry-point runner for cicada and cicada-mcp."""
    argv = list(sys.argv)
    _maybe_print_version(argv, version_prog_name)

    normalized = prepare_argv(
        argv,
        default_on_unknown=default_on_unknown,
        default_on_none=default_on_none,
        default_on_unknown_args=default_on_unknown_args,
        default_on_none_args=default_on_none_args,
    )

    parser = get_argument_parser()
    parser.prog = prog_name
    args = parser.parse_args(normalized[1:])

    # Configure logging based on verbose flag
    configure_logging(verbose=get_verbose_flag(args))

    if not handle_command(args):
        parser.print_help()
        sys.exit(1)


def _resolve_default(spec: DefaultResolver) -> str | None:
    if callable(spec):
        return spec()
    return spec


def _maybe_print_version(argv: Sequence[str], prog_name: str) -> None:
    if len(argv) > 1 and argv[1] in ("--version", "-v"):
        from cicada.version_check import get_version_string

        print(f"{prog_name} {get_version_string()}")
        sys.exit(0)
