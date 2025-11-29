"""
Function signature building utilities.

This module provides utilities for formatting function signatures,
eliminating duplication across the formatter module.

Note: Language-specific formatting (like function identifiers) has been moved
to language-specific formatters in cicada/languages/<language>/formatter.py.
Use cicada.languages.formatter_registry.get_language_formatter() for that.
"""

from typing import Any


class SignatureBuilder:
    """
    Builds formatted function signatures from function data.

    This class consolidates signature formatting logic that appears
    in multiple places in the formatter module.
    """

    @staticmethod
    def build(func: dict[str, Any]) -> str:
        """
        Build a formatted function signature.

        Creates signatures like:
        - "func_name(arg1: type1, arg2: type2) :: return_type"
        - "func_name(arg1, arg2)"
        - "func_name/2"

        Args:
            func: Function dictionary with keys:
                - name: Function name
                - arity: Function arity
                - signature: Optional pre-formatted signature string (SCIP-generated)
                - args: Optional list of argument names
                - args_with_types: Optional list of {name, type} dicts
                - return_type: Optional return type string

        Returns:
            Formatted signature string

        Example:
            func = {
                'name': 'create_user',
                'arity': 2,
                'args_with_types': [
                    {'name': 'attrs', 'type': 'map'},
                    {'name': 'opts', 'type': 'keyword'}
                ],
                'return_type': '{:ok, User.t()} | {:error, Ecto.Changeset.t()}'
            }
            sig = SignatureBuilder.build(func)
            # Returns: "create_user(attrs: map, opts: keyword) :: {:ok, User.t()} | {:error, Ecto.Changeset.t()}"
        """
        func_name = func["name"]
        signature = ""

        # If we have a pre-formatted signature (from SCIP), use it directly
        if "signature" in func and func["signature"]:
            return func["signature"]

        # If we have args_with_types, use that for rich signatures
        if "args_with_types" in func and func["args_with_types"]:
            args_str = SignatureBuilder._format_args_with_types(func["args_with_types"])
            signature = f"{func_name}({args_str})"

        # Otherwise, fallback to args without types
        elif "args" in func and func["args"]:
            args_str = ", ".join(func["args"])
            signature = f"{func_name}({args_str})"

        # No args, just show function name with empty parens or /0
        elif func["arity"] == 0:
            signature = f"{func_name}()"

        # Fallback to name/arity notation
        else:
            signature = f"{func_name}/{func['arity']}"

        # Append return type if available
        if "return_type" in func and func["return_type"]:
            signature += f" :: {func['return_type']}"

        return signature

    @staticmethod
    def _format_args_with_types(args_with_types: list[dict[str, str]]) -> str:
        """
        Format arguments with type annotations.

        Args:
            args_with_types: List of dicts with 'name' and 'type' keys

        Returns:
            Comma-separated string of "name: type" pairs

        Example:
            args = [
                {'name': 'attrs', 'type': 'map'},
                {'name': 'opts', 'type': 'keyword'}
            ]
            formatted = SignatureBuilder._format_args_with_types(args)
            # Returns: "attrs: map, opts: keyword"
        """
        formatted_args: list[str] = []
        for arg in args_with_types:
            if arg.get("type"):
                formatted_args.append(f"{arg['name']}: {arg['type']}")
            else:
                formatted_args.append(arg["name"])

        return ", ".join(formatted_args)

    @staticmethod
    def get_return_type(func: dict[str, Any]) -> str | None:
        """
        Extract just the return type from a function.

        Args:
            func: Function dictionary

        Returns:
            Return type string or None if not available
        """
        return func.get("return_type")
