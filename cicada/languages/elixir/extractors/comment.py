"""
Inline comment extraction logic.

This module extracts inline comments (# ...) from Elixir source code for
keyword-based indexing and search.
"""

from cicada.utils import extract_text_from_node, is_function_definition_call


class CommentExtractor:
    """Extract inline comments from Elixir AST nodes."""

    def __init__(self, min_length: int = 3, merge_consecutive: bool = True):
        """
        Initialize the comment extractor.

        Args:
            min_length: Minimum comment length after stripping # (default: 3)
            merge_consecutive: Merge consecutive comment lines into blocks (default: True)
        """
        self.min_length = min_length
        self.merge_consecutive = merge_consecutive

    def extract_from_module(
        self, module_node, source_code: bytes, functions: list[dict]
    ) -> dict[str, list[dict]]:
        """
        Extract all inline comments from a module and associate with functions.

        Args:
            module_node: The module's do_block node from the AST
            source_code: The source code bytes
            functions: List of function dicts with 'name' and 'line' keys

        Returns:
            Dict mapping function names to lists of comment dicts:
                {
                    "function_name": [
                        {
                            "comment": "Comment text without # prefix",
                            "line": 42,
                            "is_block": False
                        }
                    ]
                }
        """
        # Step 1: Extract all comments with their context (stateless recursion)
        all_comments: list[dict] = []
        self._extract_comments_recursive(module_node, source_code, all_comments, None)

        # Step 2: Merge consecutive comments if enabled
        if self.merge_consecutive:
            all_comments = self._merge_consecutive_comments(all_comments)

        # Step 3: Associate comments with functions
        comments_by_function = self._associate_with_functions(all_comments, functions)

        return comments_by_function

    def _extract_comments_recursive(
        self,
        node,
        source_code: bytes,
        all_comments: list[dict],
        current_function: str | None,
    ):
        """
        Recursively walk the AST to find and extract comment nodes.

        Args:
            node: Current AST node
            source_code: The source code bytes
            all_comments: Collector list for extracted comments
            current_function: Name of the function currently being traversed (if any)
        """
        # Track function context
        if node.type == "call" and is_function_definition_call(node, source_code):
            # Extract function name
            func_name = self._extract_function_name(node, source_code)

            # Process children within this function context
            for child in node.children:
                self._extract_comments_recursive(child, source_code, all_comments, func_name)
            return

        # Extract comment if this is a comment node
        if node.type == "comment":
            comment_text = self._extract_comment_content(node, source_code)

            # Apply min_length filter
            if comment_text and len(comment_text) >= self.min_length:
                all_comments.append(
                    {
                        "comment": comment_text,
                        "line": node.start_point[0] + 1,  # 1-indexed
                        "start_line": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                        "function": current_function,  # Can be None for module-level
                        "is_block": False,  # Will be updated if merged
                    }
                )

        # Recursively process children
        for child in node.children:
            self._extract_comments_recursive(child, source_code, all_comments, current_function)

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

    def _extract_comment_content(self, comment_node, source_code: bytes) -> str | None:
        """
        Extract the content of a comment node and strip # prefix.

        Args:
            comment_node: A comment node from the AST
            source_code: The source code bytes

        Returns:
            Comment content (without # prefix and stripped) or None
        """
        comment_text = extract_text_from_node(comment_node, source_code)

        if not comment_text:
            return None

        # Strip # prefix and whitespace
        if comment_text.startswith("#"):
            comment_text = comment_text[1:].strip()

        return comment_text or None

    def _merge_consecutive_comments(self, comments: list[dict]) -> list[dict]:
        """
        Merge consecutive comment lines into blocks.

        Args:
            comments: List of comment dicts with 'line' and 'comment' keys

        Returns:
            List of comment dicts with consecutive lines merged
        """
        if not comments:
            return []

        # Sort by line number
        sorted_comments = sorted(comments, key=lambda c: c["line"])

        merged = []
        i = 0

        while i < len(sorted_comments):
            current = sorted_comments[i]
            consecutive_group = [current]

            # Look for consecutive comments (same function context, consecutive lines)
            j = i + 1
            while j < len(sorted_comments):
                next_comment = sorted_comments[j]

                # Check if consecutive (line numbers differ by 1 and same function)
                if (
                    next_comment["line"] == consecutive_group[-1]["line"] + 1
                    and next_comment["function"] == current["function"]
                ):
                    consecutive_group.append(next_comment)
                    j += 1
                else:
                    break

            # If we have multiple consecutive comments, merge them
            if len(consecutive_group) > 1:
                merged_comment = {
                    "comment": "\n".join(c["comment"] for c in consecutive_group),
                    "line": consecutive_group[0]["line"],  # Start line (backward compatibility)
                    "start_line": consecutive_group[0]["start_line"],
                    "end_line": consecutive_group[-1]["end_line"],
                    "function": current["function"],
                    "is_block": True,
                }
                merged.append(merged_comment)
                i = j
            else:
                # Single comment, keep as is
                merged.append(current)
                i += 1

        return merged

    def _associate_with_functions(
        self, comments: list[dict], functions: list[dict]
    ) -> dict[str, list[dict]]:
        """
        Associate comments with functions.

        Logic:
        1. Comments with function != None → already associated (inside function body)
        2. Comments with function == None → associate with next function based on line number
        3. If no functions, return empty dict

        Args:
            comments: List of comment dicts with 'line' and 'function' keys
            functions: List of function dicts with 'name' and 'line' keys

        Returns:
            Dict mapping function names to comment lists
        """
        if not functions:
            return {}

        # Sort functions by line number
        sorted_funcs = sorted(functions, key=lambda f: f["line"])

        # Build result dict
        result: dict[str, list[dict]] = {}

        for comment in comments:
            # If comment already has a function (was inside function body), use that
            if comment["function"]:
                func_name = comment["function"]
            else:
                # Module-level comment - associate with next function
                func_name = self._find_next_function(comment["line"], sorted_funcs)

            if func_name:
                if func_name not in result:
                    result[func_name] = []

                # Create a clean comment dict without the 'function' key
                clean_comment = {
                    "comment": comment["comment"],
                    "line": comment["line"],
                    "start_line": comment.get("start_line", comment["line"]),
                    "end_line": comment.get("end_line", comment["line"]),
                    "is_block": comment.get("is_block", False),
                }
                result[func_name].append(clean_comment)

        return result

    def _find_next_function(self, comment_line: int, sorted_functions: list[dict]) -> str | None:
        """
        Find the next function after a given line number.

        Args:
            comment_line: Line number of the comment
            sorted_functions: List of functions sorted by line number

        Returns:
            Name of the next function, or None if not found
        """
        # Find the first function whose line is >= comment_line
        for func in sorted_functions:
            if func["line"] >= comment_line:
                return func["name"]

        # If no function found after the comment, associate with last function
        return sorted_functions[-1]["name"] if sorted_functions else None
