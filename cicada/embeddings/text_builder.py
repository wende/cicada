"""
Text building utilities for embeddings.

Builds text representations of modules and functions for embedding generation.
"""

from __future__ import annotations

from typing import Any


def build_module_text(module_name: str, module_data: dict[str, Any]) -> str:
    """
    Build text representation of a module for embedding.

    Combines module name, documentation, and context into a single text
    suitable for embedding generation.

    Args:
        module_name: Full module name (e.g., "MyApp.User")
        module_data: Module data from the index

    Returns:
        Text representation for embedding
    """
    parts: list[str] = []

    # Module name (tokenized for semantic understanding)
    # "MyApp.User" -> "MyApp User module"
    name_parts = module_name.split(".")
    parts.append(f"{' '.join(name_parts)} module")

    # Module documentation
    moduledoc = module_data.get("moduledoc")
    if moduledoc and isinstance(moduledoc, str):
        # Clean up the doc - take first paragraph
        doc_text = moduledoc.strip().split("\n\n")[0]
        if doc_text:
            parts.append(doc_text)

    # String keywords from the module (SQL, error messages, etc.)
    string_keywords = module_data.get("string_keywords", {})
    if string_keywords and isinstance(string_keywords, dict):
        strings = list(string_keywords.keys())[:10]  # Limit to avoid bloat
        if strings:
            parts.append(f"Contains: {', '.join(strings)}")

    return "\n\n".join(parts)


def build_function_text(module_name: str, func_data: dict[str, Any]) -> str:
    """
    Build text representation of a function for embedding.

    Combines function name, signature, documentation, and context into
    a single text suitable for embedding generation.

    Args:
        module_name: Full module name containing the function
        func_data: Function data from the index

    Returns:
        Text representation for embedding
    """
    parts: list[str] = []

    func_name = func_data.get("name", "unknown")
    arity = func_data.get("arity", 0)

    # Function signature with module context
    signature = func_data.get("signature")
    if signature:
        parts.append(f"{module_name}.{signature}")
    else:
        # Build a basic signature from name and arity
        parts.append(f"{module_name}.{func_name}/{arity}")

    # Function documentation
    doc = func_data.get("doc")
    if doc and isinstance(doc, str):
        doc_text = doc.strip()
        if doc_text:
            parts.append(doc_text)

    # Function arguments for context
    args = func_data.get("args", [])
    if args:
        parts.append(f"Parameters: {', '.join(args)}")

    # String literals from the function (SQL queries, error messages, etc.)
    string_keywords = func_data.get("string_keywords", {})
    if string_keywords and isinstance(string_keywords, dict):
        strings = list(string_keywords.keys())[:5]  # Limit to avoid bloat
        if strings:
            parts.append(f"Contains: {', '.join(strings)}")

    # Visibility context
    visibility = func_data.get("type", "def")
    if visibility == "defp":
        parts.append("(private function)")

    return "\n\n".join(parts)


def build_document_id(
    doc_type: str, module_name: str, func_data: dict[str, Any] | None = None
) -> str:
    """
    Build a unique document ID for embedding storage.

    Args:
        doc_type: "module" or "function"
        module_name: Full module name
        func_data: Function data (required for functions)

    Returns:
        Unique document ID string
    """
    if doc_type == "module":
        return f"module:{module_name}"
    elif doc_type == "function" and func_data:
        func_name = func_data.get("name", "unknown")
        arity = func_data.get("arity", 0)
        return f"function:{module_name}.{func_name}/{arity}"
    else:
        raise ValueError(f"Invalid doc_type: {doc_type}")


def build_metadata(
    doc_type: str,
    module_name: str,
    file_path: str,
    line: int,
    func_data: dict[str, Any] | None = None,
    module_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build metadata dictionary for embedding storage.

    Args:
        doc_type: "module" or "function"
        module_name: Full module name
        file_path: Path to the source file
        line: Line number in the source file
        func_data: Function data (optional, for functions)
        module_data: Module data (optional, for modules)

    Returns:
        Metadata dictionary for storage
    """
    meta: dict[str, Any] = {
        "type": doc_type,
        "module": module_name,
        "file": file_path,
        "line": line,
    }

    if doc_type == "function" and func_data:
        meta["name"] = (
            f"{module_name}.{func_data.get('name', 'unknown')}/{func_data.get('arity', 0)}"
        )
        meta["function"] = func_data.get("name", "unknown")
        meta["arity"] = func_data.get("arity", 0)
        meta["visibility"] = func_data.get("type", "def")
        # Include function doc for display in results
        doc = func_data.get("doc")
        if doc and isinstance(doc, str):
            meta["doc"] = doc.strip()
    else:
        meta["name"] = module_name
        # Include moduledoc for display in results
        if module_data:
            moduledoc = module_data.get("moduledoc")
            if moduledoc and isinstance(moduledoc, str):
                meta["doc"] = moduledoc.strip()

    return meta


def build_pr_text(pr_data: dict[str, Any]) -> str:
    """
    Build text representation of a PR for embedding.

    Combines PR title and description into a single text
    suitable for semantic search.

    Args:
        pr_data: PR data dictionary with 'title' and 'description' keys

    Returns:
        Text representation for embedding
    """
    parts: list[str] = []

    # PR title (most important for semantic matching)
    title = pr_data.get("title", "")
    if title:
        parts.append(f"PR: {title}")

    # PR description (stored as 'description' in pr_index.json)
    description = pr_data.get("description", "")
    if description and isinstance(description, str):
        # Clean up and truncate if needed (embeddings have token limits)
        desc_text = description.strip()
        if len(desc_text) > 2000:
            desc_text = desc_text[:2000] + "..."
        if desc_text:
            parts.append(desc_text)

    return "\n\n".join(parts) if parts else ""


def build_pr_document_id(pr_number: int) -> str:
    """
    Build a unique document ID for PR embedding storage.

    Args:
        pr_number: The PR number

    Returns:
        Unique document ID string
    """
    return f"pr:{pr_number}"


def build_pr_metadata(pr_data: dict[str, Any]) -> dict[str, Any]:
    """
    Build metadata dictionary for PR embedding storage.

    Args:
        pr_data: PR data dictionary

    Returns:
        Metadata dictionary for storage
    """
    pr_number = pr_data.get("number", 0)
    return {
        "type": "pr",
        "name": f"PR #{pr_number}",
        "pr_number": pr_number,
        "title": pr_data.get("title", ""),
        "state": pr_data.get("state", "unknown"),
        "author": pr_data.get("author", "unknown"),
        "merged_at": pr_data.get("merged_at"),
        "created_at": pr_data.get("created_at"),
    }
