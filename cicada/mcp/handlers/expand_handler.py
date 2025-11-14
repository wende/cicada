"""
Expand Handler.

Handles the expand_result tool for drilling down into search results.
"""

from typing import Any

from mcp.types import TextContent


class ExpandHandler:
    """Handler for result expansion tool."""

    def __init__(self, index: dict[str, Any], config: dict[str, Any]):
        """
        Initialize the expand handler.

        Args:
            index: The code index containing modules and functions
            config: Configuration dictionary
        """
        self.index = index
        self.config = config

    async def expand_result(
        self,
        identifier: str,
        result_type: str = "auto",
        include_code: bool = True,
        include_relationships: bool = True,
        output_format: str = "markdown",
    ) -> list[TextContent]:
        """
        Expand a search result to show full details.

        Args:
            identifier: Module name (e.g., "MyApp.Auth") or
                       function reference (e.g., "MyApp.Auth.verify_token/2")
            result_type: "module", "function", or "auto" (auto-detect)
            include_code: Include code snippets (default: True)
            include_relationships: Include call graph relationships (default: True)
            output_format: Output format ("markdown" or "json")

        Returns:
            TextContent with formatted expansion details
        """
        # Auto-detect type if needed
        if result_type == "auto":
            result_type = self._detect_type(identifier)

        # Route to appropriate handler
        if result_type == "module":
            return await self._expand_module(identifier, output_format)
        elif result_type == "function":
            return await self._expand_function(identifier, include_relationships, output_format)
        else:
            error_msg = f"Unknown result type: {result_type}. Use 'module', 'function', or 'auto'."
            return [TextContent(type="text", text=error_msg)]

    def _detect_type(self, identifier: str) -> str:
        """
        Detect whether identifier is a module or function.

        Args:
            identifier: The identifier to check

        Returns:
            "module" or "function"
        """
        # If it has arity notation (e.g., /2), it's a function
        if "/" in identifier:
            return "function"

        # Check if it exists as a module in the index
        if identifier in self.index.get("modules", {}):
            return "module"

        # If not found as module, assume function (will error appropriately later)
        return "function"

    async def _expand_module(self, module_name: str, output_format: str) -> list[TextContent]:
        """
        Expand a module to show full details.

        Args:
            module_name: Name of the module
            output_format: Output format

        Returns:
            TextContent with module details
        """
        from cicada.mcp.handlers.module_handlers import ModuleSearchHandler

        # Check if module exists
        if module_name not in self.index.get("modules", {}):
            error_msg = f"Module not found: {module_name}"
            return [TextContent(type="text", text=error_msg)]

        # Use existing module search handler
        handler = ModuleSearchHandler(self.index, self.config)
        return await handler.search_module(
            module_name,
            output_format=output_format,
            visibility="all",  # Show all functions (public and private)
            pr_info=None,
            staleness_info=None,
        )

    async def _expand_function(
        self,
        function_ref: str,
        include_relationships: bool,
        output_format: str,
    ) -> list[TextContent]:
        """
        Expand a function to show full details.

        Args:
            function_ref: Function reference (e.g., "MyApp.Auth.verify_token/2")
            include_relationships: Whether to include call graph relationships
            output_format: Output format

        Returns:
            TextContent with function details
        """
        from cicada.mcp.handlers.function_handlers import FunctionSearchHandler

        # Parse function reference to extract components
        function_name, module_path = self._parse_function_reference(function_ref)

        if not function_name:
            error_msg = f"Invalid function reference: {function_ref}"
            return [TextContent(type="text", text=error_msg)]

        # Use existing function search handler
        handler = FunctionSearchHandler(self.index, self.config)
        return await handler.search_function(
            function_name=function_name,
            output_format=output_format,
            include_usage_examples=include_relationships,  # Show usage if requested
            max_examples=5,
            usage_type="all",
            changed_since=None,
            show_relationships=include_relationships,
            module_path=module_path,
        )

    def _parse_function_reference(self, function_ref: str) -> tuple[str, str | None]:
        """
        Parse a function reference into name and module path.

        Args:
            function_ref: Function reference like "MyApp.Auth.verify_token/2"
                         or just "verify_token"

        Returns:
            Tuple of (function_name, module_path)
            function_name includes arity if present
            module_path is None if not specified
        """
        # If it contains a module path
        if "." in function_ref:
            # Split on the last dot to separate module from function
            parts = function_ref.rsplit(".", 1)
            if len(parts) == 2:
                module_path = parts[0]
                function_name = parts[1]
                return function_name, module_path

        # No module path, just function name (possibly with arity)
        return function_ref, None
