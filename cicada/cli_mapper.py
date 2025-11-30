"""CLI Mapper - Converts MCP tool schemas to CLI arguments and vice versa.

This module provides automatic conversion between:
1. JSON schemas (from tools.py) to argparse arguments
2. argparse namespaces to handler keyword arguments

This ensures CLI behavior is identical to MCP behavior with a single source of truth.
"""

import argparse
from typing import Any

from mcp.types import Tool


def _parse_bool_or_none(value: str) -> bool | None:
    """Parse nullable boolean: 'true', 'false', or 'null'/'none'."""
    if value.lower() in ("null", "none", ""):
        return None
    if value.lower() in ("true", "yes", "1"):
        return True
    if value.lower() in ("false", "no", "0"):
        return False
    raise argparse.ArgumentTypeError(
        f"Invalid boolean value: {value}. Use 'true', 'false', or 'null'."
    )


def schema_to_argparse(
    param_name: str,
    schema: dict,
    parser: argparse.ArgumentParser,
    positional: bool = False,
    default: Any = None,
    nullable_bool: bool = False,
) -> None:
    """Convert a JSON schema property to an argparse argument.

    Args:
        param_name: Name of the parameter (converted from snake_case to kebab-case for CLI options)
        schema: JSON schema property definition
        parser: argparse parser to add argument to
        positional: Whether this should be a positional argument
        default: Default value if not provided
        nullable_bool: Whether this is a nullable boolean type (tri-state)
    """
    # For options, convert underscores to hyphens
    # For positional args, keep the name as-is (argparse uses it as dest automatically)
    cli_param_name = param_name.replace("_", "-") if not positional else param_name
    arg_dest = param_name  # Store as snake_case in namespace

    # Handle nullable boolean special case (tri-state: true/false/null)
    if nullable_bool or schema.get("type") == ["boolean", "null"]:
        # Nullable booleans are typically optional flags, not positional
        parser.add_argument(
            f"--{cli_param_name}",
            nargs="?",
            const=True,
            type=_parse_bool_or_none,
            dest=arg_dest,
            default=default,
            help=schema.get("description", ""),
        )
        return

    # Handle anyOf types (e.g., string | array)
    if "anyOf" in schema:
        types = [t.get("type") for t in schema.get("anyOf", [])]
        if "array" in types:
            # Treat as array (nargs='+' for multiple values)
            if positional:
                parser.add_argument(
                    cli_param_name,
                    nargs="+",
                    help=schema.get("description", ""),
                )
            else:
                parser.add_argument(
                    f"--{cli_param_name}",
                    nargs="+",
                    dest=arg_dest,
                    help=schema.get("description", ""),
                )
            return

    # Get the base type
    param_type = schema.get("type", "string")

    # Handle array types
    if param_type == "array":
        if positional:
            parser.add_argument(
                cli_param_name,
                nargs="+",
                help=schema.get("description", ""),
            )
        else:
            parser.add_argument(
                f"--{cli_param_name}",
                nargs="+",
                dest=arg_dest,
                help=schema.get("description", ""),
            )
        return

    # Handle boolean types
    if param_type == "boolean":
        # Check if this boolean has a True default (needs both --flag and --no-flag)
        has_true_default = default is True

        # Booleans are always flags, never positional. Always use kebab-case.
        flag_name = param_name.replace("_", "-")

        # Add positive flag
        parser.add_argument(
            f"--{flag_name}",
            action="store_true",
            dest=arg_dest,
            default=default,
            help=schema.get("description", ""),
        )
        # If True default, also add negative flag
        if has_true_default:
            parser.add_argument(
                f"--no-{flag_name}",
                action="store_false",
                dest=arg_dest,
                help=f"Do not {schema.get('description', param_name)}",
            )
        return

    # Handle enum types
    if "enum" in schema:
        choices = schema.get("enum")
        if positional:
            parser.add_argument(
                cli_param_name,
                choices=choices,
                help=schema.get("description", ""),
            )
        else:
            parser.add_argument(
                f"--{cli_param_name}",
                choices=choices,
                default=default,
                dest=arg_dest,
                help=schema.get("description", ""),
            )
        return

    # Handle typed parameters (string, integer, etc.)
    type_map = {
        "string": str,
        "integer": int,
        "number": float,
    }
    python_type = type_map.get(param_type, str)

    if positional:
        parser.add_argument(
            cli_param_name,
            type=python_type,
            help=schema.get("description", ""),
        )
    else:
        arg_kwargs: dict[str, Any] = {
            "type": python_type,
            "dest": arg_dest,
            "help": schema.get("description", ""),
        }
        if default is not None:
            arg_kwargs["default"] = default
        parser.add_argument(f"--{cli_param_name}", **arg_kwargs)


def register_tool_subparsers(
    subparsers: argparse._SubParsersAction,
    tools: list[Tool],
) -> None:
    """Register all tool subparsers from MCP tool definitions.

    Args:
        subparsers: argparse subparsers action to register to
        tools: List of MCP Tool definitions from get_tool_definitions()
    """
    for tool in tools:
        # Convert tool name from snake_case to kebab-case for CLI
        cli_tool_name = tool.name.replace("_", "-")

        # Create subparser for this tool
        short_help = tool.description.split("\n")[0] if tool.description else tool.name
        tool_parser = subparsers.add_parser(
            cli_tool_name,
            help=short_help,
            description=tool.description,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        # Get schema properties
        schema = tool.inputSchema
        required_params = schema.get("required", [])
        properties = schema.get("properties", {})

        # Add arguments for each property
        for param_name, param_schema in properties.items():
            is_required = param_name in required_params

            # Determine if this should be positional (required params are typically positional)
            positional = is_required

            # Get default value from schema if specified
            default = param_schema.get("default")

            # Check for nullable boolean
            nullable_bool = param_schema.get("type") == ["boolean", "null"]

            # Add the argument
            schema_to_argparse(
                param_name=param_name,
                schema=param_schema,
                parser=tool_parser,
                positional=positional,
                default=default,
                nullable_bool=nullable_bool,
            )


def parse_cli_args_to_handler_kwargs(
    args: argparse.Namespace,
    tool_name: str,
) -> dict[str, Any]:
    """Convert argparse namespace to handler keyword arguments.

    Args:
        args: argparse.Namespace from parsed CLI arguments
        tool_name: Name of the tool (e.g., "query", "search-module")

    Returns:
        Dictionary of keyword arguments to pass to handler

    Raises:
        ValueError: If required parameters are missing or validation fails
    """
    # Normalize tool name (kebab-case to snake_case for internal use)
    normalized_tool_name = tool_name.replace("-", "_")

    # Get all attributes from namespace
    kwargs = {}

    for key, value in vars(args).items():
        # Skip special argparse-added attributes
        if key in ("command", "tool", "verbose"):
            continue

        # Skip None values (optional params not provided)
        if value is None:
            continue

        # Skip empty lists
        if isinstance(value, list) and len(value) == 0:
            continue

        # Add to kwargs
        kwargs[key] = value

    # Tool-specific validation
    # Note: Most required parameter validation is handled by argparse (positional args).
    # search_module is special: neither param is required in schema, but at least one
    # must be provided. This "at least one of" constraint can't be expressed in argparse.
    if (
        normalized_tool_name == "search_module"
        and not kwargs.get("module_name")
        and not kwargs.get("file_path")
    ):
        raise ValueError("search-module requires either --module-name or --file-path")

    return kwargs
