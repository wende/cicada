"""
Shared helper functions for indexer operations.

This module contains extracted helper functions used by both full and incremental
indexing to reduce code duplication and improve testability.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cicada.extractors.keybert import KeyBERTExtractor
    from cicada.extractors.keyword import RegularKeywordExtractor
    from cicada.git.helper import GitHelper
    from cicada.keyword_expander import KeywordExpander


# Constants for keyword expansion
DEFAULT_EXPANSION_TOP_N = 20
DEFAULT_EXPANSION_THRESHOLD = 0.3
STRING_KEYWORD_BOOST = 1.3


def initialize_keyword_extractor(
    repo_path: Path,
    verbose: bool = False,
) -> tuple[KeyBERTExtractor | RegularKeywordExtractor | None, KeywordExpander | None]:
    """
    Initialize keyword extractor and expander based on config.

    Args:
        repo_path: Path to the repository root
        verbose: Whether to print verbose messages

    Returns:
        Tuple of (keyword_extractor, keyword_expander), both None on failure
    """
    from cicada.tier import read_keyword_extraction_config

    try:
        extraction_method, expansion_method = read_keyword_extraction_config(repo_path)

        # Initialize extraction method
        if extraction_method == "bert":
            from cicada.extractors.keybert import KeyBERTExtractor

            keyword_extractor = KeyBERTExtractor(verbose=verbose)
        else:
            from cicada.extractors.keyword import RegularKeywordExtractor

            keyword_extractor = RegularKeywordExtractor(verbose=verbose)

        # Initialize expansion method
        from cicada.keyword_expander import KeywordExpander

        keyword_expander = KeywordExpander(expansion_type=expansion_method, verbose=verbose)

        return keyword_extractor, keyword_expander

    except Exception as e:
        if verbose:
            print(f"Warning: Could not initialize keyword extractor/expander: {e}")
            print("Continuing without keyword extraction...")
        return None, None


def initialize_git_helper(
    repo_path: Path,
    verbose: bool = False,
) -> GitHelper | None:
    """
    Initialize git helper for timestamp computation.

    Args:
        repo_path: Path to the repository root
        verbose: Whether to print verbose messages

    Returns:
        GitHelper instance or None on failure
    """
    try:
        from cicada.git.helper import GitHelper

        git_helper = GitHelper(str(repo_path))
        if verbose:
            print("Git history tracking enabled - computing function timestamps")
        return git_helper
    except Exception as e:
        if verbose:
            print(f"Warning: Could not initialize git helper: {e}")
            print("Continuing without timestamp computation...")
        return None


def initialize_string_extractor(
    verbose: bool = False,
):
    """
    Initialize string extractor for string keyword extraction.

    Args:
        verbose: Whether to print verbose messages

    Returns:
        StringExtractor instance or None on failure
    """
    try:
        from cicada.languages.elixir.extractors import StringExtractor

        extractor = StringExtractor(min_length=3)
        if verbose:
            print("String keyword extraction enabled")
        return extractor
    except Exception as e:
        if verbose:
            print(f"Warning: Could not initialize string extractor: {e}")
            print("Continuing without string keyword extraction...")
        return None


def extract_and_expand_keywords(
    text: str,
    extractor,
    expander,
    top_n: int = 10,
    expansion_top_n: int = DEFAULT_EXPANSION_TOP_N,
    expansion_threshold: float = DEFAULT_EXPANSION_THRESHOLD,
    boost: float = 1.0,
) -> tuple[dict[str, float], dict[str, float]]:
    """
    Extract keywords from text and optionally expand them.

    Args:
        text: The text to extract keywords from
        extractor: The keyword extractor instance
        expander: The keyword expander instance (optional)
        top_n: Number of top keywords to extract
        expansion_top_n: Number of top expanded keywords
        expansion_threshold: Minimum score threshold for expansion
        boost: Score multiplier (e.g., 1.3 for string keywords)

    Returns:
        Tuple of (extracted_keywords_dict, expanded_keywords_dict)
        extracted_keywords_dict: {word: score} before expansion
        expanded_keywords_dict: {word: score} after expansion (same as extracted if no expander)
    """
    if not extractor or not text:
        return {}, {}

    # Step 1: Extract keywords with scores
    extraction_result = extractor.extract_keywords(text, top_n=top_n)
    extracted_keywords_list = [kw for kw, _ in extraction_result["top_keywords"]]
    extracted_scores = {
        kw.lower(): score * boost for kw, score in extraction_result["top_keywords"]
    }

    # Step 2: Expand keywords if expander available
    if expander and extracted_keywords_list:
        expansion_result = expander.expand_keywords(
            extracted_keywords_list,
            top_n=expansion_top_n,
            threshold=expansion_threshold,
            keyword_scores=extracted_scores,
        )

        # Convert to dict: word -> max_score
        expanded_scores: dict[str, float] = {}
        if isinstance(expansion_result, dict):
            for item in expansion_result["words"]:
                word = item["word"]
                score = item["score"]
                if word not in expanded_scores or score > expanded_scores[word]:
                    expanded_scores[word] = score
        else:
            expanded_scores = extracted_scores
    else:
        expanded_scores = extracted_scores

    return extracted_scores, expanded_scores


def compute_function_timestamps(
    git_helper: GitHelper,
    file_path: str,
    functions: list[dict],
    repo_path: Path,
) -> int:
    """
    Compute and apply git timestamps to functions in-place.

    Args:
        git_helper: GitHelper instance
        file_path: Relative path to the file
        functions: List of function dictionaries to update
        repo_path: Path to the repository root

    Returns:
        Count of functions that had timestamps applied
    """
    if not git_helper or not functions:
        return 0

    count = 0
    try:
        # Batch query all functions in this file at once (10x faster)
        evolutions = git_helper.get_functions_evolution_batch(
            file_path=file_path,
            functions=functions,
        )

        # Apply evolution data to each function
        for func in functions:
            func_name = func.get("name")
            if func_name and func_name in evolutions:
                evolution = evolutions[func_name]
                if evolution:
                    func["created_at"] = evolution["created_at"]["date"]
                    func["last_modified_at"] = evolution["last_modified"]["date"]
                    func["last_modified_sha"] = evolution["last_modified"]["sha"]
                    if evolution["last_modified"].get("pr"):
                        func["last_modified_pr"] = evolution["last_modified"]["pr"]
                    func["modification_count"] = evolution["total_modifications"]
                    count += 1
    except Exception:
        # Silently skip timestamp computation errors for this file
        pass

    return count


def build_module_info(
    file_path: str,
    module_data: dict,
    functions: list[dict],
    module_dependencies: dict,
    module_keywords: dict | None = None,
    module_extracted_keywords: dict | None = None,
    module_string_keywords: dict | None = None,
    module_extracted_string_keywords: dict | None = None,
    module_string_sources: list | None = None,
) -> dict:
    """
    Assemble complete module info dictionary.

    Args:
        file_path: Relative path to the source file
        module_data: Parsed module data from the parser
        functions: List of function dictionaries
        module_dependencies: Dict with 'modules' key containing set of dependencies
        module_keywords: Expanded keywords dict (optional)
        module_extracted_keywords: Pre-expansion keywords for co-occurrence (optional)
        module_string_keywords: Keywords from string literals (optional)
        module_extracted_string_keywords: Pre-expansion string keywords (optional)
        module_string_sources: Source strings list (optional)

    Returns:
        Complete module info dictionary for the index
    """
    public_count = sum(1 for f in functions if f["type"] == "def")
    private_count = sum(1 for f in functions if f["type"] == "defp")

    module_info = {
        "file": file_path,
        "line": module_data["line"],
        "moduledoc": module_data.get("moduledoc"),
        "functions": functions,
        "total_functions": len(functions),
        "public_functions": public_count,
        "private_functions": private_count,
        "aliases": module_data.get("aliases", {}),
        "imports": module_data.get("imports", []),
        "requires": module_data.get("requires", []),
        "uses": module_data.get("uses", []),
        "behaviours": module_data.get("behaviours", []),
        "value_mentions": module_data.get("value_mentions", []),
        "calls": module_data.get("calls", []),
        "dependencies": [{"module": mod} for mod in sorted(module_dependencies["modules"])],
    }

    # Add optional keyword fields
    if module_keywords:
        module_info["keywords"] = module_keywords
    if module_extracted_keywords:
        module_info["extracted_keywords"] = module_extracted_keywords
    if module_string_keywords:
        module_info["string_keywords"] = module_string_keywords
    if module_extracted_string_keywords:
        module_info["extracted_string_keywords"] = module_extracted_string_keywords
    if module_string_sources:
        module_info["string_sources"] = module_string_sources

    return module_info


def extract_string_keywords_for_module(
    file_path: Path,
    module_name: str,
    functions: list[dict],
    string_extractor,
    keyword_extractor,
    keyword_expander,
    expansion_top_n: int = DEFAULT_EXPANSION_TOP_N,
    expansion_threshold: float = DEFAULT_EXPANSION_THRESHOLD,
) -> tuple[dict | None, dict | None, list]:
    """
    Extract string keywords for a module and its functions.

    This function parses the source file to extract string literals,
    then extracts keywords from those strings.

    Args:
        file_path: Path to the source file
        module_name: Name of the module to extract strings from
        functions: List of function dictionaries to update in-place
        string_extractor: StringExtractor instance
        keyword_extractor: Keyword extractor instance
        keyword_expander: Keyword expander instance (optional)
        expansion_top_n: Number of top expanded keywords
        expansion_threshold: Minimum score threshold for expansion

    Returns:
        Tuple of (module_string_keywords, module_extracted_string_keywords, module_string_sources)
        Functions are updated in-place with string_keywords and string_sources.
    """
    if not string_extractor or not keyword_extractor:
        return None, None, []

    import tree_sitter_elixir as ts_elixir
    from tree_sitter import Language, Parser

    from cicada.languages.elixir.extractors import extract_modules

    # Parse file to extract strings
    with open(file_path, "rb") as f:
        source_code = f.read()

    ts_parser = Parser(Language(ts_elixir.language()))  # type: ignore[deprecated]
    tree = ts_parser.parse(source_code)

    parsed_modules = extract_modules(tree.root_node, source_code)
    if not parsed_modules:
        return None, None, []

    # Find matching module
    for parsed_mod in parsed_modules:
        if parsed_mod["module"] != module_name:
            continue

        do_block = parsed_mod.get("do_block")
        if not do_block:
            continue

        # Extract strings from module
        extracted_strings = string_extractor.extract_from_module(do_block, source_code)

        # Group strings by function
        function_strings_map: dict[str, list] = {}
        module_level_strings = []

        for string_info in extracted_strings:
            func_name = string_info.get("function")
            if func_name:
                if func_name not in function_strings_map:
                    function_strings_map[func_name] = []
                function_strings_map[func_name].append(string_info)
            else:
                module_level_strings.append(string_info)

        # Extract keywords from module-level strings
        module_string_keywords = None
        module_extracted_string_keywords = None
        module_string_sources = []

        if module_level_strings:
            combined_text = " ".join([s["string"] for s in module_level_strings])
            module_extracted_string_keywords, module_string_keywords = extract_and_expand_keywords(
                combined_text,
                keyword_extractor,
                keyword_expander,
                expansion_top_n=expansion_top_n,
                expansion_threshold=expansion_threshold,
                boost=STRING_KEYWORD_BOOST,
            )
            module_string_sources = module_level_strings

        # Extract keywords from function strings
        for func in functions:
            func_name = func.get("name")
            if not func_name or func_name not in function_strings_map:
                continue

            func_string_list = function_strings_map[func_name]
            combined_text = " ".join([s["string"] for s in func_string_list])

            extracted, expanded = extract_and_expand_keywords(
                combined_text,
                keyword_extractor,
                keyword_expander,
                expansion_top_n=expansion_top_n,
                expansion_threshold=expansion_threshold,
                boost=STRING_KEYWORD_BOOST,
            )

            if extracted:
                func["extracted_string_keywords"] = extracted
            if expanded:
                func["string_keywords"] = expanded
            func["string_sources"] = func_string_list

        return module_string_keywords, module_extracted_string_keywords, module_string_sources

    return None, None, []


def enrich_function_keywords(
    func: dict,
    keyword_extractor,
    keyword_expander,
    module_name: str,
    verbose: bool = False,
) -> int:
    """
    Extract and apply keywords to a function in-place.

    Args:
        func: Function dictionary to update
        keyword_extractor: Keyword extractor instance
        keyword_expander: Keyword expander instance
        module_name: Name of the containing module (for error messages)
        verbose: Whether to print verbose messages

    Returns:
        1 if extraction failed, 0 otherwise
    """
    import sys

    func_name = func.get("name", "")
    doc_text = func.get("doc") or func.get("test_description")

    if not keyword_extractor or not doc_text:
        return 0

    try:
        # Include function name in text for keyword extraction
        text_for_keywords = f"{func_name} {doc_text}"

        extracted, expanded = extract_and_expand_keywords(
            text_for_keywords,
            keyword_extractor,
            keyword_expander,
        )

        if extracted:
            func["extracted_keywords"] = extracted
        if expanded:
            func["keywords"] = expanded

        return 0
    except Exception as e:
        if verbose:
            print(
                f"Warning: Keyword extraction failed for {module_name}.{func_name}: {e}",
                file=sys.stderr,
            )
        return 1
