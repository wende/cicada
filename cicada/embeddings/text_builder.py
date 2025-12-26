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
        doc_text = moduledoc.strip()
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
) -> dict[str, Any]:
    """
    Build metadata dictionary for embedding storage.

    Args:
        doc_type: "module" or "function"
        module_name: Full module name
        file_path: Path to the source file
        line: Line number in the source file
        func_data: Function data (optional, for functions)

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
    else:
        meta["name"] = module_name

    return meta
