"""
String literal extraction logic.

This module extracts string literals from function bodies for keyword-based
indexing and search. It filters out documentation strings and other non-relevant
string content.

Author: Claude Code
"""

from cicada.utils import extract_text_from_node, is_function_definition_call


class StringExtractor:
    """Extract string literals from Elixir AST nodes."""

    def __init__(self, min_length: int = 3):
        """
        Initialize the string extractor.

        Args:
            min_length: Minimum string length to extract (default: 3)
        """
        self.min_length = min_length
        self.current_function: str | None = None
        self.extracted_strings: list[dict] = []

    def extract_from_module(self, module_node, source_code: bytes) -> list[dict]:
        """
        Extract all string literals from a module's functions.

        Args:
            module_node: The module's do_block node from the AST
            source_code: The source code bytes

        Returns:
            List of dicts containing:
                - string: The string content
                - line: Line number where the string appears
                - function: Name of the function containing the string (or None)
        """
        self.extracted_strings = []
        self.current_function = None
        self._extract_strings_recursive(module_node, source_code, parent_context=None)
        return self.extracted_strings

    def _extract_strings_recursive(self, node, source_code: bytes, parent_context: str | None):
        """
        Recursively walk the AST to find and extract string literals.

        Args:
            node: Current AST node
            source_code: The source code bytes
            parent_context: Type of parent node (e.g., 'doc_attribute', 'moduledoc_attribute')
        """
        # Check if this is a function definition to track context
        if node.type == "call" and is_function_definition_call(node, source_code):
            # Extract function name
            func_name = self._extract_function_name(node, source_code)
            prev_function = self.current_function
            self.current_function = func_name

            # Process the function body
            for child in node.children:
                self._extract_strings_recursive(child, source_code, parent_context)

            # Restore previous function context
            self.current_function = prev_function
            return

        # Check if this is a @doc or @moduledoc attribute
        if node.type == "unary_operator":
            is_doc_attr = self._is_doc_attribute(node, source_code)
            if is_doc_attr:
                # Mark children as documentation context to skip them
                for child in node.children:
                    self._extract_strings_recursive(child, source_code, is_doc_attr)
                return

        # Extract string if this is a string node and not in doc context
        if node.type == "string" and parent_context not in [
            "doc_attribute",
            "moduledoc_attribute",
        ]:
            string_content = self._extract_string_content(node, source_code)

            # Apply filters (only length check)
            if string_content and len(string_content) >= self.min_length:
                self.extracted_strings.append(
                    {
                        "string": string_content,
                        "line": node.start_point[0] + 1,
                        "function": self.current_function,
                    }
                )

        # Recursively process children
        for child in node.children:
            self._extract_strings_recursive(child, source_code, parent_context)

    def _extract_function_name(self, call_node, source_code: bytes) -> str | None:
        """
        Extract function name from a def/defp call node.

        Args:
            call_node: A call node representing def or defp
            source_code: The source code bytes

        Returns:
            Function name or None
        """
        for child in call_node.children:
            if child.type == "arguments":
                # Look for function name in arguments
                for arg_child in child.children:
                    if arg_child.type == "call":
                        # Function with parameters
                        for call_child in arg_child.children:
                            if call_child.type == "identifier":
                                return extract_text_from_node(call_child, source_code)
                    elif arg_child.type == "identifier":
                        # Function without parameters
                        return extract_text_from_node(arg_child, source_code)
                    elif arg_child.type == "binary_operator":
                        # Function with guards: func_name(params) when guard
                        for op_child in arg_child.children:
                            if op_child.type == "call":
                                for call_child in op_child.children:
                                    if call_child.type == "identifier":
                                        return extract_text_from_node(call_child, source_code)
        return None

    def _is_doc_attribute(self, unary_op_node, source_code: bytes) -> str | None:
        """
        Check if a unary_operator node is a @doc or @moduledoc attribute.

        Args:
            unary_op_node: A unary_operator node
            source_code: The source code bytes

        Returns:
            'doc_attribute' if @doc, 'moduledoc_attribute' if @moduledoc, None otherwise
        """
        is_at_operator = False
        call_node = None

        for child in unary_op_node.children:
            if child.type == "@":
                is_at_operator = True
            elif child.type == "call" and is_at_operator:
                call_node = child
                break

        if not call_node:
            return None

        # Check the identifier in the call
        for child in call_node.children:
            if child.type == "identifier":
                attr_name = extract_text_from_node(child, source_code)
                if attr_name == "doc":
                    return "doc_attribute"
                elif attr_name == "moduledoc":
                    return "moduledoc_attribute"

        return None

    def _extract_string_content(self, string_node, source_code: bytes) -> str | None:
        """
        Extract the content of a string node.

        Args:
            string_node: A string node from the AST
            source_code: The source code bytes

        Returns:
            String content (without quotes) or None
        """
        string_content = []

        for child in string_node.children:
            if child.type == "quoted_content":
                content = extract_text_from_node(child, source_code)
                string_content.append(content)

        return "".join(string_content) if string_content else None
