"""EDoc extraction from Erlang comments.

Erlang uses EDoc format for documentation:
    %% @doc This is a function description.
    %% @param Name The name parameter
    %% @returns ok

Comments are siblings in the AST, not children of declarations.
We associate docs by proximity (doc block immediately before declaration).
"""

import re
from typing import Any


def collect_comments(root_node: Any, source: bytes) -> list[dict]:
    """
    Collect all comment nodes from the AST.

    Args:
        root_node: Tree-sitter root node
        source: Source code bytes

    Returns:
        List of comment dicts with line, end_line, and text
    """
    comments = []
    for child in root_node.children:
        if child.type == "comment":
            text = child.text.decode("utf-8")
            comments.append(
                {
                    "line": child.start_point[0] + 1,
                    "end_line": child.end_point[0] + 1,
                    "text": text,
                }
            )
    return comments


def group_consecutive_comments(comments: list[dict]) -> list[dict]:
    """
    Group consecutive comment lines into blocks.

    Args:
        comments: List of individual comment dicts

    Returns:
        List of comment block dicts with start_line, end_line, and combined text
    """
    if not comments:
        return []

    blocks: list[dict] = []
    current_block: dict | None = None

    for comment in comments:
        if current_block is None:
            current_block = {
                "start_line": comment["line"],
                "end_line": comment["end_line"],
                "lines": [comment["text"]],
            }
        elif comment["line"] == current_block["end_line"] + 1:
            # Consecutive line - extend block
            current_block["end_line"] = comment["end_line"]
            current_block["lines"].append(comment["text"])
        else:
            # Gap - save current block and start new one
            blocks.append(current_block)
            current_block = {
                "start_line": comment["line"],
                "end_line": comment["end_line"],
                "lines": [comment["text"]],
            }

    if current_block:
        blocks.append(current_block)

    return blocks


def parse_edoc_block(block: dict) -> dict | None:
    """
    Parse EDoc tags from a comment block.

    Args:
        block: Comment block with lines list

    Returns:
        Dict with doc text and tags, or None if no @doc found
    """
    lines = block["lines"]
    doc_lines = []
    params = []
    returns = None
    in_doc = False

    for line in lines:
        # Strip leading % and whitespace
        stripped = re.sub(r"^%+\s*", "", line)

        if stripped.startswith("@doc"):
            in_doc = True
            # Extract text after @doc
            doc_text = stripped[4:].strip()
            if doc_text:
                doc_lines.append(doc_text)
        elif stripped.startswith("@param"):
            # @param Name Description
            match = re.match(r"@param\s+(\w+)\s*(.*)", stripped)
            if match:
                params.append({"name": match.group(1), "desc": match.group(2).strip()})
        elif stripped.startswith(("@returns", "@return")):
            # @returns description
            returns = re.sub(r"@returns?\s*", "", stripped).strip()
        elif stripped.startswith("@"):
            # Other tag - stop doc accumulation
            in_doc = False
        elif in_doc:
            # Continue doc text
            doc_lines.append(stripped)

    if not doc_lines:
        return None

    result = {
        "start_line": block["start_line"],
        "end_line": block["end_line"],
        "doc": " ".join(doc_lines).strip(),
    }

    if params:
        result["params"] = params
    if returns:
        result["returns"] = returns

    return result


def extract_docs_from_comments(root_node, source: bytes) -> list[dict]:
    """
    Extract all EDoc blocks from source.

    Args:
        root_node: Tree-sitter root node
        source: Source code bytes

    Returns:
        List of parsed doc blocks with line positions
    """
    comments = collect_comments(root_node, source)
    blocks = group_consecutive_comments(comments)

    docs = []
    for block in blocks:
        parsed = parse_edoc_block(block)
        if parsed:
            docs.append(parsed)

    return docs


def match_docs_to_declarations(
    docs: list[dict],
    modules: list[dict],
    functions: list[dict],
    max_gap: int = 5,
) -> None:
    """
    Match doc blocks to following declarations by proximity.

    Modifies modules and functions in place, adding 'doc' field.

    Args:
        docs: List of parsed doc blocks
        modules: List of module dicts (modified in place)
        functions: List of function dicts (modified in place)
        max_gap: Maximum lines between doc end and declaration start
    """
    # Build a list of all declarations with their line numbers
    all_decls: list[tuple[int, dict]] = []

    for module in modules:
        all_decls.append((module["line"], module))

    for func in functions:
        all_decls.append((func["line"], func))

    # Sort by line number
    all_decls.sort(key=lambda x: x[0])

    # For each doc block, find the next declaration within max_gap
    for doc in docs:
        doc_end = doc["end_line"]

        for decl_line, decl in all_decls:
            if decl_line > doc_end and decl_line <= doc_end + max_gap:
                # Found a declaration immediately after this doc
                decl["doc"] = doc["doc"]
                if "params" in doc:
                    decl["params"] = doc["params"]
                if "returns" in doc:
                    decl["returns"] = doc["returns"]
                break
