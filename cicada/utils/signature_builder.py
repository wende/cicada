"""
Function signature building utilities.

This module provides utilities for formatting function signatures,
eliminating duplication across the formatter module.
"""

from typing import Any


class SignatureBuilder:
    """
    Builds formatted function signatures from function data.

    This class consolidates signature formatting logic that appears
    in multiple places in the formatter module.
    """

    @staticmethod
    def build(func: dict[str, Any], language: str = "elixir") -> str:
        """
        Build a formatted function signature using language-specific templates.

        Creates signatures like:
        - Elixir: "func_name(arg1: type1, arg2: type2) :: return_type"
        - Python: "def func_name(arg1: type1, arg2: type2) -> return_type:"

        Args:
            func: Function dictionary with keys:
                - name: Function name
                - arity: Function arity
                - args: Optional list of argument names
                - args_with_types: Optional list of {name, type} dicts
                - return_type: Optional return type string
            language: Programming language for template selection (default: "elixir")

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
            sig = SignatureBuilder.build(func, language="elixir")
            # Returns: "create_user(attrs: map, opts: keyword) :: {:ok, User.t()} | {:error, Ecto.Changeset.t()}"

            sig = SignatureBuilder.build(func, language="python")
            # Returns: "def create_user(attrs: map, opts: keyword) -> {:ok, User.t()} | {:error, Ecto.Changeset.t()}:"
        """
        func_name = func["name"]

        # Prepare arguments string
        args_str = ""
        if "args_with_types" in func and func["args_with_types"]:
            args_str = SignatureBuilder._format_args_with_types(func["args_with_types"])
        elif "args" in func and func["args"]:
            args_str = ", ".join(func["args"])
        # else: args_str remains empty for functions with no args info

        # Prepare return type annotation based on language
        return_annotation = ""
        if "return_type" in func and func["return_type"]:
            if language == "python":
                return_annotation = f" -> {func['return_type']}:"
            else:  # Elixir and fallback
                return_annotation = f" :: {func['return_type']}"
        elif language == "python" and func.get("arity") is not None:
            # Python always needs a colon, even without return type
            return_annotation = ":"

        # Special case: fallback to name/arity notation for functions with no arg info and arity > 0
        # This is common in Elixir where we might not have detailed arg info
        if (
            not args_str
            and func.get("arity", 0) > 0
            and "args_with_types" not in func
            and "args" not in func
        ):
            # Use traditional Elixir name/arity notation
            signature = f"{func_name}/{func['arity']}"
            if return_annotation and language != "python":
                signature += return_annotation
            return signature

        # Use template renderer to format the signature
        # Import here to avoid circular imports (formatter imports utils imports format)
        from cicada.format.template_renderer import TemplateRenderer

        renderer = TemplateRenderer(language)

        try:
            signature = renderer.render(
                "signature", func_name=func_name, args=args_str, return_annotation=return_annotation
            )
            return signature
        except FileNotFoundError:
            # Fallback to simple format if template not found
            signature = f"{func_name}({args_str}){return_annotation}"
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
