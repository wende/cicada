"""
Documentation extraction logic.
"""

import textwrap

from .base import extract_string_from_arguments
from .common import _find_attribute_recursive


def extract_docs(node, source_code: bytes) -> dict:
    """Extract all @doc attributes from a module body."""
    docs = {}
    _find_attribute_recursive(node, source_code, docs, "doc", _parse_doc)
    return docs


def _parse_doc(doc_node, source_code: bytes, line: int) -> dict | None:
    """Parse a @doc attribute to extract its text and examples."""
    # @doc is represented as: doc("text") or doc(false)
    for child in doc_node.children:
        if child.type == "arguments":
            doc_text = extract_string_from_arguments(child, source_code)
            if doc_text:
                # Extract examples section if present
                doc_without_examples, examples = _extract_examples_from_doc(doc_text)
                result = {"line": line, "text": doc_without_examples}
                if examples:
                    result["examples"] = examples
                return result
    return None


def _extract_examples_from_doc(doc_text: str) -> tuple[str, str | None]:
    """
    Extract the ## Examples or # Examples section from doc text.

    Args:
        doc_text: The full @doc text

    Returns:
        Tuple of (doc_without_examples, examples_text)
    """
    import re

    # Look for ## Examples or # Examples heading (case-insensitive)
    # Match at the start of a line, possibly preceded by whitespace
    examples_pattern = r"^\s*#{1,2}\s+Examples?\s*$"

    lines = doc_text.split("\n")
    examples_start_idx = None

    # Find the line where examples section starts
    for i, line in enumerate(lines):
        if re.match(examples_pattern, line, re.IGNORECASE):
            examples_start_idx = i
            break

    # If no examples section found, return original doc with dedent
    if examples_start_idx is None:
        return textwrap.dedent(doc_text), None

    # Find where examples section ends (next ## heading or end of doc)
    examples_end_idx = len(lines)
    for i in range(examples_start_idx + 1, len(lines)):
        # Check if this line is another top-level heading (##)
        if re.match(r"^\s*##\s+\w+", lines[i]):
            examples_end_idx = i
            break

    # Extract the parts
    doc_lines = lines[:examples_start_idx]
    examples_lines = lines[examples_start_idx:examples_end_idx]
    remaining_lines = lines[examples_end_idx:]

    # Reconstruct doc without examples
    doc_without_examples = "\n".join(doc_lines + remaining_lines).strip()

    # Dedent the doc text
    if doc_without_examples:
        doc_without_examples = textwrap.dedent(doc_without_examples)

    # Extract just the examples content (without the heading)
    if len(examples_lines) <= 1:
        return doc_without_examples, None

    examples_lines_content = examples_lines[1:]

    # Find minimum indentation from non-empty lines
    min_indent: int | float = float("inf")
    for line in examples_lines_content:
        if line.strip():  # Skip blank lines
            indent = len(line) - len(line.lstrip())
            min_indent = min(min_indent, indent)

    # Remove the common indentation from all lines
    if min_indent < float("inf"):
        dedented_lines: list[str] = []
        min_indent_int = int(min_indent)
        for line in examples_lines_content:
            if line.strip():  # Non-empty line
                dedented_lines.append(line[min_indent_int:])
            else:  # Empty line
                dedented_lines.append(line)
        examples_content = "\n".join(dedented_lines).strip()
    else:
        examples_content = "\n".join(examples_lines_content).strip()

    return doc_without_examples, examples_content if examples_content else None


def match_docs_to_functions(functions: list, docs: dict):
    """Match @doc attributes to functions based on proximity."""
    # @doc appears before the function, possibly with @spec in between
    # Look back up to 50 lines to handle long docs and @spec attributes
    for func in functions:
        func_line = func["line"]
        # Look for @doc in the lines before the function (up to 50 lines)
        for offset in range(1, 51):
            doc_line = func_line - offset
            if doc_line in docs:
                # docs[doc_line] is now a dict with 'text' and optionally 'examples'
                doc_info = docs[doc_line]
                if isinstance(doc_info, dict):
                    func["doc"] = doc_info.get("text")
                    if "examples" in doc_info:
                        func["examples"] = doc_info["examples"]
                else:
                    # Backward compatibility: if it's just a string
                    func["doc"] = doc_info
                break
