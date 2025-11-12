#!/usr/bin/env python
"""
Formatter Module - Formats module search results in various formats.

This module provides formatting utilities for Cicada MCP server responses,
supporting both Markdown and JSON output formats.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from cicada.utils import (
    CallSiteFormatter,
    FunctionGrouper,
    SignatureBuilder,
    find_similar_names,
)
from cicada.utils.truncation import TruncationHelper


class ModuleFormatter:
    """Formats Cicada module data in various output formats."""

    @staticmethod
    def _group_functions_by_visibility(
        data: dict[str, Any],
    ) -> tuple[
        dict[tuple[str, int], list[dict[str, Any]]], dict[tuple[str, int], list[dict[str, Any]]]
    ]:
        """
        Helper to group public and private functions once for reuse.

        Args:
            data: Module data dictionary from the index (with "functions" key)

        Returns:
            Tuple of (public_grouped, private_grouped) dictionaries keyed by (name, arity)
        """
        functions = data.get("functions", [])
        public_funcs = [f for f in functions if f["type"] == "def"]
        private_funcs = [f for f in functions if f["type"] == "defp"]

        return (
            FunctionGrouper.group_by_name_arity(public_funcs),
            FunctionGrouper.group_by_name_arity(private_funcs),
        )

    @staticmethod
    def _count_functions(data: dict[str, Any]) -> tuple[int, int]:
        """Return (public_count, private_count) for a module."""
        public_grouped, private_grouped = ModuleFormatter._group_functions_by_visibility(data)
        return len(public_grouped), len(private_grouped)

    @staticmethod
    def _split_call_sites(
        call_sites: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Split call sites into code (non-test files) and test buckets."""
        code_sites = [site for site in call_sites if "test" not in site["file"].lower()]
        test_sites = [site for site in call_sites if "test" in site["file"].lower()]
        return code_sites, test_sites

    @staticmethod
    def _group_call_sites_by_caller(call_sites):
        """Group call sites by caller (proxy to CallSiteFormatter for testing)."""
        return CallSiteFormatter.group_by_caller(call_sites)

    @staticmethod
    def _format_caller_name(site: dict[str, Any]) -> str:
        """Format caller name from a call site.

        Args:
            site: Call site dictionary with 'calling_module' and optionally 'calling_function'

        Returns:
            Formatted caller string (e.g., "Module.func/2" or "Module")
        """
        calling_func = site.get("calling_function")
        if calling_func:
            return f"{site['calling_module']}.{calling_func['name']}/{calling_func['arity']}"
        return site["calling_module"]

    @staticmethod
    def _find_similar_names(
        query: str,
        candidate_names: list[str],
        max_suggestions: int = 5,
        threshold: float = 0.4,
    ) -> list[tuple[str, float]]:
        """
        Proxy to the shared fuzzy-matching helper so tests can exercise the logic in isolation.
        """
        if not candidate_names:
            return []
        return find_similar_names(
            query=query,
            candidates=candidate_names,
            max_suggestions=max_suggestions,
            threshold=threshold,
        )

    @staticmethod
    def _format_pr_context(
        pr_info: dict | None, file_path: str, _function_name: str | None = None
    ) -> list[str]:
        """Format PR context if available (function name kept for compatibility)."""
        if not pr_info:
            return []

        lines = [
            "",
            f"Last modified: PR #{pr_info['number']} \"{pr_info['title']}\" by @{pr_info['author']}",
        ]
        if pr_info["comment_count"] > 0:
            lines.append(
                f"{pr_info['comment_count']} review comment(s) • Use: get_file_pr_history(\"{file_path}\")"
            )
        return lines

    @staticmethod
    def _append_function_section(
        lines: list[str],
        grouped_funcs: dict[tuple[str, int], list[dict[str, Any]]],
        title: str,
    ) -> bool:
        """Append a formatted function section. Returns True if anything was added."""
        if not grouped_funcs:
            return False

        lines.extend(["", f"{title}:", ""])
        for (_, _), clauses in sorted(grouped_funcs.items(), key=lambda x: x[1][0]["line"]):
            func = clauses[0]
            func_sig = SignatureBuilder.build(func)
            lines.append(f"{func['line']:>5}: {func_sig}")
        return True

    @staticmethod
    def format_module_compact(module_name: str, data: dict[str, Any]) -> str:
        """
        Format module data in compact format (for lists of 4+ modules).

        Args:
            module_name: The name of the module
            data: The module data dictionary from the index

        Returns:
            Compact formatted string (file, name, counts only)
        """
        public_count, private_count = ModuleFormatter._count_functions(data)
        return f"{data['file']}\n{module_name} - {public_count} public - {private_count} private"

    @staticmethod
    def format_module_markdown(
        module_name: str,
        data: dict[str, Any],
        visibility: str = "public",
        pr_info: dict | None = None,
        staleness_info: dict | None = None,
    ) -> str:
        """
        Format module data as Markdown.

        Args:
            module_name: The name of the module
            data: The module data dictionary from the index
            visibility: Which functions to show: 'public' (default), 'private', or 'all'
            pr_info: Optional PR context (number, title, comment_count)
            staleness_info: Optional staleness info (is_stale, age_str)

        Returns:
            Formatted Markdown string
        """
        public_grouped, private_grouped = ModuleFormatter._group_functions_by_visibility(data)

        # Count unique functions, not function clauses
        public_count = len(public_grouped)
        private_count = len(private_grouped)

        # Build the markdown output - compact format
        lines = [
            f"{data['file']}:{data['line']}",
            f"{module_name} • {public_count} public • {private_count} private",
        ]

        # Add staleness warning if applicable
        if staleness_info and staleness_info.get("is_stale"):
            lines.append("")
            lines.append(
                f"WARNING: Index may be stale (index is {staleness_info['age_str']} old, files have been modified)"
            )
            lines.append("   Please ask the user to run: cicada index")
            lines.append("")
            lines.append("   Recent changes might be in merged PRs:")
            lines.append(f"      get_file_pr_history(\"{data['file']}\")")

        # Add PR context if available
        lines.extend(ModuleFormatter._format_pr_context(pr_info, data["file"]))

        # Add moduledoc if present (first paragraph only for brevity)
        if data.get("moduledoc"):
            doc = data["moduledoc"].strip()
            # Get first paragraph (up to double newline or first 200 chars)
            first_para = doc.split("\n\n")[0].strip()
            if len(first_para) > 200:
                first_para = first_para[:200] + "..."
            lines.extend(["", first_para])

        private_shown = False

        if visibility != "private":
            ModuleFormatter._append_function_section(lines, public_grouped, "Public")

        if visibility in ["all", "private"]:
            private_shown = ModuleFormatter._append_function_section(
                lines, private_grouped, "Private"
            )

        if visibility == "private" and not private_shown:
            lines.extend(["", "*No private functions found*"])

        return "\n".join(lines)

    @staticmethod
    def format_module_json(
        module_name: str, data: dict[str, Any], visibility: str = "public"
    ) -> str:
        """
        Format module data as JSON.

        Args:
            module_name: The name of the module
            data: The module data dictionary from the index
            visibility: Which functions to show: 'public' (default), 'private', or 'all'

        Returns:
            Formatted JSON string
        """
        public_grouped, private_grouped = ModuleFormatter._group_functions_by_visibility(data)

        # Filter functions based on visibility parameter
        if visibility == "public":
            grouped = public_grouped
        elif visibility == "private":
            grouped = private_grouped
        else:  # "all"
            grouped = {**public_grouped, **private_grouped}

        # Compact function format - one entry per unique name/arity
        functions = [
            {
                "signature": SignatureBuilder.build(clauses[0]),
                "line": clauses[0]["line"],
                "type": clauses[0]["type"],
            }
            for (_, _), clauses in sorted(grouped.items())
        ]

        result = {
            "module": module_name,
            "location": f"{data['file']}:{data['line']}",
            "moduledoc": data.get("moduledoc"),
            "counts": {
                "public": data["public_functions"],
                "private": data["private_functions"],
            },
            "functions": functions,
        }
        return json.dumps(result, indent=2)

    @staticmethod
    def format_error_markdown(
        module_name: str, total_modules: int, suggestions: list[str] | None = None
    ) -> str:
        """
        Format error message as Markdown with suggestions.

        Args:
            module_name: The queried module name
            total_modules: Total number of modules in the index
            suggestions: Optional list of suggested similar module names (pre-computed)

        Returns:
            Formatted Markdown error message
        """
        lines = [
            "Module Not Found",
            "",
            f"**Query:** `{module_name}`",
            "",
        ]

        # Add "did you mean" suggestions if provided
        if suggestions:
            lines.append("## Did you mean?")
            lines.append("")
            for name in suggestions:
                lines.append(f"  • `{name}`")
            lines.append("")

        # Add alternative search strategies
        lines.extend(
            [
                "## Try:",
                "",
            ]
        )

        # Add wildcard and semantic search suggestions if module_name is valid
        if module_name and module_name.strip():
            last_component = module_name.split(".")[-1] if "." in module_name else module_name
            if last_component and last_component.strip():
                lines.append(f"  • Wildcard search: search_module('*{last_component}*')")
                lines.append(
                    f"  • Semantic search: search_by_features(['{last_component.lower()}'])"
                )

        lines.extend(
            [
                "  • Check exact spelling and capitalization (module names are case-sensitive)",
                "",
                f"Total modules in index: **{total_modules}**",
            ]
        )

        return "\n".join(lines)

    @staticmethod
    def format_error_json(module_name: str, total_modules: int) -> str:
        """
        Format error message as JSON.

        Args:
            module_name: The queried module name
            total_modules: Total number of modules in the index

        Returns:
            Formatted JSON error message
        """
        error_result = {
            "error": "Module not found",
            "query": module_name,
            "hint": "Use the exact module name as it appears in the code",
            "total_modules_available": total_modules,
        }
        return json.dumps(error_result, indent=2)

    @staticmethod
    def _format_call_site_section(
        label: str,
        sites: list[dict[str, Any]],
        indent: str,
        *,
        prepend_blank: bool = False,
        include_examples: bool = False,
    ) -> list[str]:
        if not sites:
            return []

        lines: list[str] = []
        if prepend_blank:
            lines.append("")

        grouped_sites = CallSiteFormatter.group_by_caller(sites)
        site_count = sum(len(site["lines"]) for site in grouped_sites)

        truncated_sites, truncation_msg = TruncationHelper.truncate_call_sites(grouped_sites)

        lines.append(f"{indent}{label} ({site_count}):")
        lines.extend(
            ModuleFormatter._format_grouped_sites(truncated_sites, indent, include_examples)
        )

        if truncation_msg:
            lines.append(f"{indent}{truncation_msg}")

        return lines

    @staticmethod
    def _format_remaining_sites(
        label: str, sites: list[dict[str, Any]], indent: str, prepend_blank: bool = False
    ) -> list[str]:
        if not sites:
            return []

        lines = []
        if prepend_blank:
            lines.append("")

        grouped_sites = CallSiteFormatter.group_by_caller(sites)
        remaining_count = sum(len(site["lines"]) for site in grouped_sites)
        lines.append(f"{indent}{label} ({remaining_count}):")
        for site in grouped_sites:
            caller = ModuleFormatter._format_caller_name(site)
            line_list = ", ".join(f":{line}" for line in site["lines"])
            lines.append(f"{indent}- {caller} at {site['file']}{line_list}")
        return lines

    @staticmethod
    def _format_grouped_sites(grouped_sites, indent, include_examples: bool) -> list[str]:
        lines: list[str] = []
        for site in grouped_sites:
            caller = ModuleFormatter._format_caller_name(site)

            # Show consolidated line numbers only if multiple lines (with automatic truncation)
            if len(site["lines"]) > 1:
                line_list = TruncationHelper.truncate_line_numbers(site["lines"])
                lines.append(f"{indent}- {caller} at {site['file']}{line_list}")
            else:
                lines.append(f"{indent}- {caller} at {site['file']}")

            # Add the actual code lines if available
            if include_examples and site.get("code_lines"):
                for code_entry in site["code_lines"]:
                    # Properly indent each line of the code block
                    code_lines = code_entry["code"].split("\n")
                    for code_line in code_lines:
                        lines.append(f"{indent}  {code_line}")
        return lines

    @staticmethod
    def _format_remaining_call_sites(call_sites, call_sites_with_examples, indent):
        lines = []
        # Create a set of call sites that were shown with examples
        shown_call_lines = set()
        for site in call_sites_with_examples:
            shown_call_lines.add((site["file"], site["line"]))

        # Filter to get call sites not yet shown
        remaining_call_sites = [
            site for site in call_sites if (site["file"], site["line"]) not in shown_call_lines
        ]

        if remaining_call_sites:
            # Separate into code and test
            remaining_code = [s for s in remaining_call_sites if "test" not in s["file"].lower()]
            remaining_test = [s for s in remaining_call_sites if "test" in s["file"].lower()]

            lines.append("")
            lines.append(f"{indent}Other Call Sites:")

            if remaining_code:
                lines.extend(
                    ModuleFormatter._format_remaining_sites("Code", remaining_code, indent)
                )

            if remaining_test:
                lines.extend(
                    ModuleFormatter._format_remaining_sites(
                        "Test", remaining_test, indent, prepend_blank=bool(remaining_code)
                    )
                )
        return lines

    @staticmethod
    def _format_call_sites_without_examples(call_sites, indent):
        lines = []
        code_sites, test_sites = ModuleFormatter._split_call_sites(call_sites)

        call_count = len(call_sites)
        lines.append("")
        lines.append(f"{indent}Called {call_count} times:")
        lines.append("")

        if code_sites:
            lines.extend(
                ModuleFormatter._format_call_site_section(
                    "Code", code_sites, indent, include_examples=False
                )
            )

        if test_sites:
            lines.extend(
                ModuleFormatter._format_call_site_section(
                    "Test",
                    test_sites,
                    indent,
                    prepend_blank=bool(code_sites),
                    include_examples=False,
                )
            )
        lines.append("")
        return lines

    @staticmethod
    def _format_call_sites_with_examples(call_sites, call_sites_with_examples, indent):
        lines = []
        code_sites_with_examples, test_sites_with_examples = ModuleFormatter._split_call_sites(
            call_sites_with_examples
        )

        lines.append(f"{indent}Usage Examples:")

        if code_sites_with_examples:
            lines.extend(
                ModuleFormatter._format_call_site_section(
                    "Code",
                    code_sites_with_examples,
                    indent,
                    include_examples=True,
                )
            )

        if test_sites_with_examples:
            lines.extend(
                ModuleFormatter._format_call_site_section(
                    "Test",
                    test_sites_with_examples,
                    indent,
                    prepend_blank=bool(code_sites_with_examples),
                    include_examples=True,
                )
            )

        lines.extend(
            ModuleFormatter._format_remaining_call_sites(
                call_sites, call_sites_with_examples, indent
            )
        )
        return lines

    @staticmethod
    def _format_call_sites(call_sites, call_sites_with_examples, indent):
        lines = []
        # Check if we have usage examples (code lines)
        has_examples = len(call_sites_with_examples) > 0

        if has_examples:
            lines.extend(
                ModuleFormatter._format_call_sites_with_examples(
                    call_sites, call_sites_with_examples, indent
                )
            )
        else:
            lines.extend(ModuleFormatter._format_call_sites_without_examples(call_sites, indent))
        return lines

    @staticmethod
    def _format_function_entry(
        result: dict[str, Any], single_result: bool, show_relationships: bool
    ) -> list[str]:
        """Format a single function search result (either single or multi layout)."""
        module_name = result["module"]
        func = result["function"]
        file_path = result["file"]
        pr_info = result.get("pr_info")
        sig = SignatureBuilder.build(func)
        call_sites = result.get("call_sites", [])
        call_sites_with_examples = result.get("call_sites_with_examples", [])

        lines: list[str] = []

        if single_result:
            lines.extend(
                [
                    f"{file_path}:{func['line']}",
                    f"{module_name}.{func['name']}/{func['arity']}",
                    f"Type: {sig}",
                ]
            )
            lines.extend(ModuleFormatter._format_pr_context(pr_info, file_path))
        else:
            lines.extend(
                [
                    "",
                    "---",
                    "",
                    f"{module_name}.{func['name']}/{func['arity']}",
                    f"{file_path}:{func['line']} • {func['type']}",
                    "",
                    "Signature:",
                    f"{sig}",
                ]
            )
            pr_lines = ModuleFormatter._format_pr_context(pr_info, file_path)
            if pr_info and pr_info.get("comment_count", 0) > 0 and len(pr_lines) > 2:
                pr_lines[-1] = f"{pr_info['comment_count']} review comment(s) available"
            lines.extend(pr_lines)

        if func.get("doc"):
            doc_lines = ['Documentation: """', func["doc"], '"""']
            if single_result:
                lines.extend(doc_lines)
            else:
                lines.extend(["", *doc_lines])

        if func.get("examples"):
            lines.extend(["", "Examples:", "", func["examples"]])

        if func.get("guards"):
            guards_str = ", ".join(func["guards"])
            if single_result:
                lines.append(f"  Guards: when {guards_str}")
            else:
                lines.extend(["", f"**Guards:** `when {guards_str}`"])

        if show_relationships:
            dependencies = result.get("dependencies", [])
            if dependencies:
                lines.append("")
                lines.append("Calls these functions:")
                for dep in dependencies[:5]:
                    dep_module = dep.get("module", "?")
                    dep_func = dep.get("function", "?")
                    dep_arity = dep.get("arity", "?")
                    dep_line = dep.get("line", "?")
                    lines.append(f"   • {dep_module}.{dep_func}/{dep_arity} :{dep_line}")
                if len(dependencies) > 5:
                    lines.append(f"   ... and {len(dependencies) - 5} more")

        if call_sites:
            lines.extend(
                ModuleFormatter._format_call_sites(call_sites, call_sites_with_examples, "")
            )
        else:
            lines.append("*No call sites found*")
            lines.append("")
            lines.append("Possible reasons:")
            lines.append("   • Dead code → Use find_dead_code() to verify")
            lines.append("   • Public API → Not called internally but used by clients")
            lines.append("   • New code → Check when added with get_commit_history()")

            if pr_info:
                if pr_info.get("comment_count", 0) > 0:
                    lines.append(
                        f"   • {pr_info['comment_count']} PR review comments exist → get_file_pr_history(\"{file_path}\")"
                    )
                else:
                    lines.append(
                        f"   • Added in PR #{pr_info['number']} → get_file_pr_history(\"{file_path}\")"
                    )

            lines.append("")

        return lines

    @staticmethod
    def format_function_results_markdown(
        function_name: str,
        results: list[dict[str, Any]],
        staleness_info: dict | None = None,
        show_relationships: bool = True,
    ) -> str:
        """
        Format function search results as Markdown.

        Args:
            function_name: The searched function name
            results: List of function matches with module context
            staleness_info: Optional staleness info (is_stale, age_str)
            show_relationships: Whether to show relationship information (what this calls / what calls this)

        Returns:
            Formatted Markdown string
        """
        if not results:
            # Extract just the function name without module/arity for suggestions
            func_only = function_name.split(".")[-1].split("/")[0]

            # Build error message
            error_parts = []

            # Add staleness warning if applicable
            if staleness_info and staleness_info.get("is_stale"):
                error_parts.append(
                    f"WARNING: Index may be stale (index is {staleness_info['age_str']} old, files have been modified)\n"
                    f"   Please ask the user to run: cicada index\n"
                )

            error_parts.append(
                f"""Function Not Found

**Query:** `{function_name}`

## Try:

  • Search without arity: `{func_only}` (if you used /{'{arity}'})
  • Search without module: `{func_only}` (searches all modules)
  • Wildcard search: `*{func_only}*` or `{func_only}*`
  • Semantic search: search_by_features(['{func_only.lower()}'])
  • Check spelling (function names are case-sensitive)

Tip: If you're exploring code, try search_by_features first to discover functions by what they do.

## Was this function recently removed?

If this function was deleted:
  • Check recent PRs: get_file_pr_history("<file_path>")
  • Search git history for the function name
  • Find what replaced it: search_by_features(['<concept>'])
"""
            )

            return "\n".join(error_parts)

        # Group results by (module, name, arity) to consolidate function clauses
        grouped_results = {}
        for result in results:
            key = (
                result["module"],
                result["function"]["name"],
                result["function"]["arity"],
            )
            if key not in grouped_results:
                grouped_results[key] = result
            # If there are multiple clauses, we just keep the first one for display
            # (they all have the same module/name/arity/doc/examples)

        # Convert back to list
        consolidated_results = list(grouped_results.values())

        # Add staleness warning at the top if applicable
        if staleness_info and staleness_info.get("is_stale"):
            lines = [
                f"WARNING: Index may be stale (index is {staleness_info['age_str']} old, files have been modified)",
                "   Please ask the user to run: cicada index",
                "",
                "   Recent changes might be in merged PRs - use get_file_pr_history() for specific files",
                "",
            ]
        else:
            lines = []

        single_result = len(consolidated_results) == 1

        # For single results (e.g., MFA search), use simpler header
        if single_result:
            lines.append("---")
        else:
            lines.extend(
                [
                    f"Functions matching {function_name}",
                    "",
                    f"Found {len(consolidated_results)} match(es):",
                ]
            )

        for result in consolidated_results:
            lines.extend(
                ModuleFormatter._format_function_entry(result, single_result, show_relationships)
            )

        # Add closing separator for single results
        if single_result:
            lines.append("---")

        return "\n".join(lines)

    @staticmethod
    def format_function_results_json(function_name: str, results: list[dict[str, Any]]) -> str:
        """
        Format function search results as JSON.

        Args:
            function_name: The searched function name
            results: List of function matches with module context

        Returns:
            Formatted JSON string
        """
        if not results:
            error_result = {
                "error": "Function not found",
                "query": function_name,
                "hint": "Verify the function name spelling or try without arity",
            }
            return json.dumps(error_result, indent=2)

        formatted_results = []
        for result in results:
            func_entry = {
                "module": result["module"],
                "moduledoc": result.get("moduledoc"),
                "function": result["function"]["name"],
                "arity": result["function"]["arity"],
                "full_name": f"{result['module']}.{result['function']['name']}/{result['function']['arity']}",
                "signature": SignatureBuilder.build(result["function"]),
                "location": f"{result['file']}:{result['function']['line']}",
                "type": result["function"]["type"],
                "doc": result["function"].get("doc"),
                "call_sites": result.get("call_sites", []),
            }

            # Add examples if present
            if result["function"].get("examples"):
                func_entry["examples"] = result["function"]["examples"]

            # Add return_type if present
            if result["function"].get("return_type"):
                func_entry["return_type"] = result["function"]["return_type"]

            # Add guards if present
            if result["function"].get("guards"):
                func_entry["guards"] = result["function"]["guards"]

            formatted_results.append(func_entry)

        output = {
            "query": function_name,
            "total_matches": len(results),
            "results": formatted_results,
        }
        return json.dumps(output, indent=2)

    @staticmethod
    def format_module_usage_markdown(module_name: str, usage_results: dict[str, Any]) -> str:
        """
        Format module usage results as Markdown.

        Args:
            module_name: The module being searched for
            usage_results: Dictionary with usage category keys

        Returns:
            Formatted Markdown string
        """
        aliases = usage_results.get("aliases", [])
        imports = usage_results.get("imports", [])
        requires = usage_results.get("requires", [])
        uses = usage_results.get("uses", [])
        value_mentions = usage_results.get("value_mentions", [])
        function_calls = usage_results.get("function_calls", [])

        lines = [f"# Usage of `{module_name}`", ""]

        # Show aliases section
        if aliases:
            lines.extend([f"## Aliases ({len(aliases)} module(s)):", ""])
            for imp in aliases:
                alias_info = (
                    f" as `{imp['alias_name']}`"
                    if imp["alias_name"] != module_name.split(".")[-1]
                    else ""
                )
                lines.append(f"- `{imp['importing_module']}` {alias_info} — `{imp['file']}`")
            lines.append("")

        # Show imports section
        if imports:
            lines.extend([f"## Imports ({len(imports)} module(s)):", ""])
            for imp in imports:
                lines.append(f"- `{imp['importing_module']}` — `{imp['file']}`")
            lines.append("")

        # Show requires section
        if requires:
            lines.extend([f"## Requires ({len(requires)} module(s)):", ""])
            for req in requires:
                lines.append(f"- `{req['importing_module']}` — `{req['file']}`")
            lines.append("")

        # Show uses section
        if uses:
            lines.extend([f"## Uses ({len(uses)} module(s)):", ""])
            for use in uses:
                lines.append(f"- `{use['importing_module']}` — `{use['file']}`")
            lines.append("")

        # Show value mentions section
        if value_mentions:
            lines.extend([f"## As Value ({len(value_mentions)} module(s)):", ""])
            for vm in value_mentions:
                lines.append(f"- `{vm['importing_module']}` — `{vm['file']}`")
            lines.append("")

        # Show function calls section
        if function_calls:
            # Group by called function
            called_functions = {}
            for fc in function_calls:
                calling_module = fc["calling_module"]
                file_path = fc["file"]

                for call in fc["calls"]:
                    called_func_key = f"{call['called_function']}/{call['called_arity']}"

                    if called_func_key not in called_functions:
                        called_functions[called_func_key] = {
                            "name": call["called_function"],
                            "arity": call["called_arity"],
                            "calling_functions": [],
                            "total_calls": 0,
                        }

                    # Add calling function info
                    calling_func = call.get("calling_function")
                    if calling_func:
                        called_functions[called_func_key]["calling_functions"].append(
                            {
                                "module": calling_module,
                                "function": calling_func["name"],
                                "arity": calling_func["arity"],
                                "start_line": calling_func["start_line"],
                                "end_line": calling_func["end_line"],
                                "call_count": len(call["lines"]),
                                "call_lines": call["lines"],
                                "file": file_path,
                            }
                        )
                    else:
                        # Module-level call
                        called_functions[called_func_key]["calling_functions"].append(
                            {
                                "module": calling_module,
                                "function": None,
                                "call_count": len(call["lines"]),
                                "call_lines": call["lines"],
                                "file": file_path,
                            }
                        )

                    called_functions[called_func_key]["total_calls"] += len(call["lines"])

            lines.extend(
                [
                    "## Function Calls:",
                    "",
                ]
            )

            # Display each called function
            for func_key, func_data in sorted(called_functions.items()):
                num_functions = len(func_data["calling_functions"])
                lines.append(
                    f"- {func_key} — {func_data['total_calls']} calls in {num_functions} function(s)"
                )

                # Display calling functions
                for caller in func_data["calling_functions"]:
                    if caller["function"]:
                        # Regular function call
                        func_sig = f"{caller['function']}/{caller['arity']}"
                        line_range = f":{caller['start_line']}-{caller['end_line']}"
                        call_info = f"{caller['call_count']} calls"

                        # Show specific line numbers only if ≤3 calls
                        if caller["call_count"] <= 3:
                            line_nums = ", ".join(
                                f":{line}" for line in sorted(caller["call_lines"])
                            )
                            call_info = f"{caller['call_count']} calls ({line_nums})"

                        lines.append(f"    • {func_sig} {line_range} — {call_info}")
                    else:
                        # Module-level call
                        call_info = f"{caller['call_count']} calls"
                        if caller["call_count"] <= 3:
                            line_nums = ", ".join(
                                f":{line}" for line in sorted(caller["call_lines"])
                            )
                            call_info = f"{caller['call_count']} calls ({line_nums})"
                        lines.append(f"    • {caller['module']} (module-level) — {call_info}")

            lines.append("")

        # Show message if no usage found at all
        if not any([aliases, imports, requires, uses, value_mentions, function_calls]):
            lines.extend(["*No usage found for this module*"])

        return "\n".join(lines)

    @staticmethod
    def format_module_usage_json(module_name: str, usage_results: dict[str, Any]) -> str:
        """
        Format module usage results as JSON.

        Args:
            module_name: The module being searched for
            usage_results: Dictionary with usage category keys

        Returns:
            Formatted JSON string
        """
        output = {
            "module": module_name,
            "aliases": usage_results.get("aliases", []),
            "imports": usage_results.get("imports", []),
            "requires": usage_results.get("requires", []),
            "uses": usage_results.get("uses", []),
            "value_mentions": usage_results.get("value_mentions", []),
            "function_calls": usage_results.get("function_calls", []),
            "summary": {
                "aliased_by": len(usage_results.get("aliases", [])),
                "imported_by": len(usage_results.get("imports", [])),
                "required_by": len(usage_results.get("requires", [])),
                "used_by": len(usage_results.get("uses", [])),
                "mentioned_as_value_by": len(usage_results.get("value_mentions", [])),
                "called_by": len(usage_results.get("function_calls", [])),
            },
        }
        return json.dumps(output, indent=2)

    @staticmethod
    def format_keyword_search_results_markdown(
        results: list[dict[str, Any]], show_scores: bool = True
    ) -> str:
        """
        Format keyword search results as Markdown.

        Args:
            results: List of search result dictionaries
            show_scores: Whether to show relevance scores. Defaults to True.

        Returns:
            Formatted Markdown string
        """
        lines: list[str] = []

        for result in results:
            result_type = result["type"]
            name = result["name"]
            file_path = result["file"]
            line = result["line"]
            score = result["score"]
            matched_keywords = result["matched_keywords"]
            keyword_sources = result.get("keyword_sources", {})

            # Determine match source indicator
            match_indicator = ""
            if keyword_sources:
                sources = set(keyword_sources.values())
                if sources == {"docs"}:
                    match_indicator = " 📄"
                elif sources == {"strings"}:
                    match_indicator = " 💬"
                elif "both" in sources or ({"docs", "strings"}.issubset(sources)):
                    match_indicator = " 📄💬"

            # Compact format with type indication and match source
            type_label = "Module" if result_type == "module" else "Function"
            lines.append(f"{type_label}: {name}{match_indicator}")
            if show_scores:
                lines.append(f"Score: {score:.2f}")
            lines.append(f"Path: {file_path}:{line}")

            # Show matched keywords with their sources
            if matched_keywords:
                kw_with_sources = []
                for kw in matched_keywords:
                    source = keyword_sources.get(kw)
                    if source == "docs":
                        kw_with_sources.append(kw + " (📄)")
                    elif source == "strings":
                        kw_with_sources.append(kw + " (💬)")
                    elif source == "both":
                        kw_with_sources.append(kw + " (📄💬)")
                    else:
                        kw_with_sources.append(kw)
                lines.append("Matched: " + ", ".join(kw_with_sources))
            else:
                lines.append("Matched: None")

            # Show string sources if available
            string_sources = result.get("string_sources", [])
            if string_sources:
                lines.append("String literals:")
                for src in string_sources[:3]:  # Show up to 3 strings
                    # Truncate long strings
                    string_content = src["string"]
                    if len(string_content) > 60:
                        string_content = string_content[:60] + "..."
                    lines.append(f'  • "{string_content}" (line {src["line"]})')
                if len(string_sources) > 3:
                    lines.append(f"  ... and {len(string_sources) - 3} more")

            # First line of documentation only
            doc = result.get("doc")
            if doc:
                doc_lines = doc.strip().split("\n")
                first_line = doc_lines[0] if doc_lines else ""
                lines.append(f'Doc: "{first_line}"')

            lines.append("---")  # Separator between results

        return "\n".join(lines)


class JSONFormatter:
    """Formats JSON data with customizable options."""

    def __init__(self, indent: int | None = 2, sort_keys: bool = False):
        """
        Initialize the formatter.

        Args:
            indent: Number of spaces for indentation (default: 2)
            sort_keys: Whether to sort dictionary keys alphabetically (default: False)
        """
        self.indent = indent
        self.sort_keys = sort_keys

    def format_string(self, json_string: str) -> str:
        """
        Format a JSON string.

        Args:
            json_string: Raw JSON string to format

        Returns:
            Formatted JSON string

        Raises:
            ValueError: If the input is not valid JSON
        """
        try:
            data = json.loads(json_string)
            return json.dumps(data, indent=self.indent, sort_keys=self.sort_keys)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e

    def format_file(self, input_path: Path, output_path: Path | None = None) -> str:
        """
        Format a JSON file.

        Args:
            input_path: Path to the input JSON file
            output_path: Optional path to write formatted output (default: stdout)

        Returns:
            Formatted JSON string

        Raises:
            FileNotFoundError: If the input file doesn't exist
            ValueError: If the input file contains invalid JSON
        """
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Read the input file
        with open(input_path) as f:
            json_string = f.read()

        # Format the JSON
        formatted = self.format_string(json_string)

        # Write to output file if specified, otherwise return for stdout
        if output_path:
            with open(output_path, "w") as f:
                _ = f.write(formatted)
                _ = f.write("\n")  # Add trailing newline
            print(f"Formatted JSON written to: {output_path}", file=sys.stderr)

        return formatted

    def format_dict(self, data: dict) -> str:
        """
        Format a Python dictionary as JSON.

        Args:
            data: Dictionary to format

        Returns:
            Formatted JSON string
        """
        return json.dumps(data, indent=self.indent, sort_keys=self.sort_keys)


def main():
    """Main entry point for the formatter CLI."""
    parser = argparse.ArgumentParser(
        description="Pretty print JSON files with customizable formatting"
    )
    _ = parser.add_argument("input", type=Path, help="Input JSON file to format")
    _ = parser.add_argument(
        "-o", "--output", type=Path, help="Output file (default: print to stdout)"
    )
    _ = parser.add_argument(
        "-i",
        "--indent",
        type=int,
        default=2,
        help="Number of spaces for indentation (default: 2)",
    )
    _ = parser.add_argument(
        "-s",
        "--sort-keys",
        action="store_true",
        help="Sort dictionary keys alphabetically",
    )
    _ = parser.add_argument(
        "--compact", action="store_true", help="Use compact formatting (no indentation)"
    )

    args = parser.parse_args()

    # Create formatter with specified options
    indent = None if args.compact else args.indent
    formatter = JSONFormatter(indent=indent, sort_keys=args.sort_keys)

    try:
        # Format the file
        formatted = formatter.format_file(args.input, args.output)

        # Print to stdout if no output file specified
        if not args.output:
            print(formatted)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
