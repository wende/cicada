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


class ModuleFormatter:
    """Formats Cicada module data in various output formats."""

    @staticmethod
    def _group_call_sites_by_caller(call_sites):
        return CallSiteFormatter.group_by_caller(call_sites)

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
        pr_info: dict | None, file_path: str, function_name: str | None = None
    ) -> list[str]:
        """
        Format PR context information with suggestions when unavailable.

        Args:
            pr_info: Optional PR context (number, title, author, comment_count)
            file_path: Path to the file
            function_name: Optional function name for more specific suggestions

        Returns:
            List of formatted lines to append to output. The first line is always
            an empty string (for spacing), followed by either:
            - PR context lines (if pr_info provided): PR title, author, comment count
            - Suggestion lines (if no pr_info): Instructions on how to get context
        """
        lines = []
        if pr_info:
            lines.append("")
            lines.append(
                f"📝 Last modified: PR #{pr_info['number']} \"{pr_info['title']}\" by @{pr_info['author']}"
            )
            if pr_info["comment_count"] > 0:
                lines.append(
                    f"💬 {pr_info['comment_count']} review comment(s) • Use: get_file_pr_history(\"{file_path}\")"
                )
        else:
            # Suggest how to get context when PR info unavailable
            lines.append("")
            lines.append("💭 Want to know why this code exists?")
            lines.append("   • Build PR index: Ask user to run 'cicada index-pr'")
            if function_name:
                lines.append(
                    f'   • Check git history: get_commit_history("{file_path}", function_name="{function_name}")'
                )
            else:
                lines.append(f'   • Check git history: get_commit_history("{file_path}")')
        return lines

    @staticmethod
    def format_module_markdown(
        module_name: str,
        data: dict[str, Any],
        private_functions: str = "exclude",
        pr_info: dict | None = None,
        staleness_info: dict | None = None,
    ) -> str:
        """
        Format module data as Markdown.

        Args:
            module_name: The name of the module
            data: The module data dictionary from the index
            private_functions: How to handle private functions: 'exclude' (hide), 'include' (show all), or 'only' (show only private)
            pr_info: Optional PR context (number, title, comment_count)
            staleness_info: Optional staleness info (is_stale, age_str)

        Returns:
            Formatted Markdown string
        """
        # Group functions by type (def = public, defp = private)
        public_funcs = [f for f in data["functions"] if f["type"] == "def"]
        private_funcs = [f for f in data["functions"] if f["type"] == "defp"]

        # Group by name/arity to deduplicate function clauses
        public_grouped = FunctionGrouper.group_by_name_arity(public_funcs)
        private_grouped = FunctionGrouper.group_by_name_arity(private_funcs)

        # Count unique functions, not function clauses
        public_count = len(public_grouped)
        private_count = len(private_grouped)

        # Build the markdown output - compact format
        lines = [
            module_name,
            "",
            f"{data['file']}:{data['line']} • {public_count} public • {private_count} private",
        ]

        # Add staleness warning if applicable
        if staleness_info and staleness_info.get("is_stale"):
            lines.append("")
            lines.append(
                f"⚠️  Index may be stale (index is {staleness_info['age_str']} old, files have been modified)"
            )
            lines.append("   Please ask the user to run: cicada index")
            lines.append("")
            lines.append("   💭 Recent changes might be in merged PRs:")
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

        # Show public functions (unless private_functions == "only")
        if public_grouped and private_functions != "only":
            lines.extend(["", "Public:", ""])
            # Sort by line number instead of function name
            for (_, _), clauses in sorted(public_grouped.items(), key=lambda x: x[1][0]["line"]):
                # Use the first clause for display (they all have same name/arity)
                func = clauses[0]
                func_sig = SignatureBuilder.build(func)
                lines.append(f"{func['line']:>5}: {func_sig}")

        # Show private functions (if private_functions == "include" or "only")
        if private_grouped and private_functions in ["include", "only"]:
            lines.extend(["", "Private:", ""])
            # Sort by line number instead of function name
            for (_, _), clauses in sorted(private_grouped.items(), key=lambda x: x[1][0]["line"]):
                # Use the first clause for display (they all have same name/arity)
                func = clauses[0]
                func_sig = SignatureBuilder.build(func)
                lines.append(f"{func['line']:>5}: {func_sig}")

        # Check if there are no functions to display based on the filter
        has_functions_to_show = (private_functions != "only" and public_grouped) or (
            private_functions in ["include", "only"] and private_grouped
        )

        if not has_functions_to_show:
            if private_functions == "only" and not private_grouped:
                lines.extend(["", "*No private functions found*"])
            elif not data["functions"]:
                lines.extend(["", "*No functions found*"])

        return "\n".join(lines)

    @staticmethod
    def format_module_json(
        module_name: str, data: dict[str, Any], private_functions: str = "exclude"
    ) -> str:
        """
        Format module data as JSON.

        Args:
            module_name: The name of the module
            data: The module data dictionary from the index
            private_functions: How to handle private functions: 'exclude' (hide), 'include' (show all), or 'only' (show only private)

        Returns:
            Formatted JSON string
        """
        # Filter functions based on private_functions parameter
        if private_functions == "exclude":
            # Only public functions
            filtered_funcs = [f for f in data["functions"] if f["type"] == "def"]
        elif private_functions == "only":
            # Only private functions
            filtered_funcs = [f for f in data["functions"] if f["type"] == "defp"]
        else:  # "include"
            # All functions
            filtered_funcs = data["functions"]

        # Group functions by name/arity to deduplicate function clauses
        grouped = FunctionGrouper.group_by_name_arity(filtered_funcs)

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
            "❌ Module Not Found",
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
    def _format_remaining_code_sites(remaining_code, indent):
        lines = []
        grouped_remaining_code = CallSiteFormatter.group_by_caller(remaining_code)
        remaining_code_count = sum(len(site["lines"]) for site in grouped_remaining_code)
        lines.append(f"{indent}Code ({remaining_code_count}):")
        for site in grouped_remaining_code:
            calling_func = site.get("calling_function")
            if calling_func:
                caller = f"{site['calling_module']}.{calling_func['name']}/{calling_func['arity']}"
            else:
                caller = site["calling_module"]

            line_list = ", ".join(f":{line}" for line in site["lines"])
            lines.append(f"{indent}- {caller} at {site['file']}{line_list}")
        return lines

    @staticmethod
    def _format_test_sites_without_examples(test_sites, code_sites, indent):
        lines = []
        if code_sites:
            lines.append("")  # Blank line between sections
        # Group test sites by caller
        grouped_test = CallSiteFormatter.group_by_caller(test_sites)
        test_count = sum(len(site["lines"]) for site in grouped_test)
        lines.append(f"{indent}Test ({test_count}):")
        for site in grouped_test:
            # Format calling location with function if available
            calling_func = site.get("calling_function")
            if calling_func:
                caller = f"{site['calling_module']}.{calling_func['name']}/{calling_func['arity']}"
            else:
                caller = site["calling_module"]

            # Show consolidated line numbers
            line_list = ", ".join(f":{line}" for line in site["lines"])
            lines.append(f"{indent}- {caller} at {site['file']}{line_list}")
        return lines

    @staticmethod
    def _format_code_sites_without_examples(code_sites, indent):
        lines = []
        # Group code sites by caller
        grouped_code = CallSiteFormatter.group_by_caller(code_sites)
        code_count = sum(len(site["lines"]) for site in grouped_code)
        lines.append(f"{indent}Code ({code_count}):")
        for site in grouped_code:
            # Format calling location with function if available
            calling_func = site.get("calling_function")
            if calling_func:
                caller = f"{site['calling_module']}.{calling_func['name']}/{calling_func['arity']}"
            else:
                caller = site["calling_module"]

            # Show consolidated line numbers
            line_list = ", ".join(f":{line}" for line in site["lines"])
            lines.append(f"{indent}- {caller} at {site['file']}{line_list}")
        return lines

    @staticmethod
    def _format_remaining_test_sites(remaining_test, remaining_code, indent):
        lines = []
        if remaining_code:
            lines.append("")
        grouped_remaining_test = CallSiteFormatter.group_by_caller(remaining_test)
        remaining_test_count = sum(len(site["lines"]) for site in grouped_remaining_test)
        lines.append(f"{indent}Test ({remaining_test_count}):")
        for site in grouped_remaining_test:
            calling_func = site.get("calling_function")
            if calling_func:
                caller = f"{site['calling_module']}.{calling_func['name']}/{calling_func['arity']}"
            else:
                caller = site["calling_module"]

            line_list = ", ".join(f":{line}" for line in site["lines"])
            lines.append(f"{indent}- {caller} at {site['file']}{line_list}")
        return lines

    @staticmethod
    def _format_grouped_test_sites(grouped_test, indent):
        lines = []
        for site in grouped_test:
            # Format calling location with function if available
            calling_func = site.get("calling_function")
            if calling_func:
                caller = f"{site['calling_module']}.{calling_func['name']}/{calling_func['arity']}"
            else:
                caller = site["calling_module"]

            # Show consolidated line numbers only if multiple lines
            if len(site["lines"]) > 1:
                line_list = ", ".join(f":{line}" for line in site["lines"])
                lines.append(f"{indent}- {caller} at {site['file']}{line_list}")
            else:
                lines.append(f"{indent}- {caller} at {site['file']}")

            # Add the actual code lines if available
            if site.get("code_lines"):
                for code_entry in site["code_lines"]:
                    # Properly indent each line of the code block
                    code_lines = code_entry["code"].split("\n")
                    for code_line in code_lines:
                        lines.append(f"{indent}  {code_line}")
        return lines

    @staticmethod
    def _format_grouped_code_sites(grouped_code, indent):
        lines = []
        for site in grouped_code:
            # Format calling location with function if available
            calling_func = site.get("calling_function")
            if calling_func:
                caller = f"{site['calling_module']}.{calling_func['name']}/{calling_func['arity']}"
            else:
                caller = site["calling_module"]

            # Show consolidated line numbers only if multiple lines
            if len(site["lines"]) > 1:
                line_list = ", ".join(f":{line}" for line in site["lines"])
                lines.append(f"{indent}- {caller} at {site['file']}{line_list}")
            else:
                lines.append(f"{indent}- {caller} at {site['file']}")

            # Add the actual code lines if available
            if site.get("code_lines"):
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
                lines.extend(ModuleFormatter._format_remaining_code_sites(remaining_code, indent))

            if remaining_test:
                lines.extend(
                    ModuleFormatter._format_remaining_test_sites(
                        remaining_test, remaining_code, indent
                    )
                )
        return lines

    @staticmethod
    def _format_test_sites_with_examples(
        test_sites_with_examples, code_sites_with_examples, indent
    ):
        lines = []
        if code_sites_with_examples:
            lines.append("")  # Blank line between sections
        # Group test sites by caller
        grouped_test = CallSiteFormatter.group_by_caller(test_sites_with_examples)
        test_count = sum(len(site["lines"]) for site in grouped_test)
        lines.append(f"{indent}Test ({test_count}):")
        lines.extend(ModuleFormatter._format_grouped_test_sites(grouped_test, indent))
        return lines

    @staticmethod
    def _format_code_sites_with_examples(code_sites_with_examples, indent):
        lines = []
        # Group code sites by caller
        grouped_code = CallSiteFormatter.group_by_caller(code_sites_with_examples)
        code_count = sum(len(site["lines"]) for site in grouped_code)
        lines.append(f"{indent}Code ({code_count}):")
        lines.extend(ModuleFormatter._format_grouped_code_sites(grouped_code, indent))
        return lines

    @staticmethod
    def _format_call_sites_without_examples(call_sites, indent):
        lines = []
        # Separate into code and test call sites
        code_sites = [s for s in call_sites if "test" not in s["file"].lower()]
        test_sites = [s for s in call_sites if "test" in s["file"].lower()]

        call_count = len(call_sites)
        lines.append("")
        lines.append(f"{indent}Called {call_count} times:")
        lines.append("")

        if code_sites:
            lines.extend(ModuleFormatter._format_code_sites_without_examples(code_sites, indent))

        if test_sites:
            lines.extend(
                ModuleFormatter._format_test_sites_without_examples(test_sites, code_sites, indent)
            )
        lines.append("")
        return lines

    @staticmethod
    def _format_call_sites_with_examples(call_sites, call_sites_with_examples, indent):
        lines = []
        # Separate into code and test call sites WITH examples
        code_sites_with_examples = [
            s for s in call_sites_with_examples if "test" not in s["file"].lower()
        ]
        test_sites_with_examples = [
            s for s in call_sites_with_examples if "test" in s["file"].lower()
        ]

        lines.append(f"{indent}Usage Examples:")

        if code_sites_with_examples:
            lines.extend(
                ModuleFormatter._format_code_sites_with_examples(code_sites_with_examples, indent)
            )

        if test_sites_with_examples:
            lines.extend(
                ModuleFormatter._format_test_sites_with_examples(
                    test_sites_with_examples, code_sites_with_examples, indent
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
                    f"⚠️  Index may be stale (index is {staleness_info['age_str']} old, files have been modified)\n"
                    f"   Please ask the user to run: cicada index\n"
                )

            error_parts.append(
                f"""❌ Function Not Found

**Query:** `{function_name}`

## Try:

  • Search without arity: `{func_only}` (if you used /{'{arity}'})
  • Search without module: `{func_only}` (searches all modules)
  • Wildcard search: `*{func_only}*` or `{func_only}*`
  • Semantic search: search_by_features(['{func_only.lower()}'])
  • Check spelling (function names are case-sensitive)

💡 Tip: If you're exploring code, try search_by_features first to discover functions by what they do.

## Was this function recently removed?

💭 If this function was deleted:
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
                f"⚠️  Index may be stale (index is {staleness_info['age_str']} old, files have been modified)",
                "   Please ask the user to run: cicada index",
                "",
                "   💭 Recent changes might be in merged PRs - use get_file_pr_history() for specific files",
                "",
            ]
        else:
            lines = []

        # For single results (e.g., MFA search), use simpler header
        if len(consolidated_results) == 1:
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
            module_name = result["module"]
            func = result["function"]
            file_path = result["file"]
            pr_info = result.get("pr_info")

            # No indentation for single results
            indent = ""

            # Add signature first (right after file path)
            sig = SignatureBuilder.build(func)

            # Skip the section header for single results
            if len(consolidated_results) == 1:
                lines.extend(
                    [
                        f"{file_path}:{func['line']}",
                        f"{module_name}.{func['name']}/{func['arity']}",
                        f"Type: {sig}",
                    ]
                )

                # Add PR context for single results
                lines.extend(ModuleFormatter._format_pr_context(pr_info, file_path, func["name"]))
            else:
                lines.extend(
                    [
                        "",
                        "---",
                        "",
                        f"{module_name}.{func['name']}/{func['arity']}",
                    ]
                )
                lines.append(f"{file_path}:{func['line']} • {func['type']}")
                lines.extend(["", "Signature:", "", f"{sig}"])

                # Add PR context for multi-result format
                pr_lines = ModuleFormatter._format_pr_context(pr_info, file_path)
                # For multi-result, adjust comment count message to be more concise
                if pr_info and pr_info.get("comment_count", 0) > 0 and len(pr_lines) > 2:
                    # Replace the last line with shorter version for multi-result display
                    pr_lines[-1] = f"💬 {pr_info['comment_count']} review comment(s) available"
                lines.extend(pr_lines)

            # Add documentation if present
            if func.get("doc"):
                if len(consolidated_results) == 1:
                    lines.extend(['Documentation: """', func["doc"], '"""'])
                else:
                    lines.extend(["", "Documentation:", "", func["doc"]])

            # Add examples if present
            if func.get("examples"):
                if len(consolidated_results) == 1:
                    lines.extend(["", f"{indent}Examples:", "", f"{indent}{func['examples']}"])
                else:
                    lines.extend(["", "Examples:", "", func["examples"]])

            # Add guards if present (on separate line for idiomatic Elixir style)
            if func.get("guards"):
                guards_str = ", ".join(func["guards"])
                if len(results) == 1:
                    lines.append(f"  Guards: when {guards_str}")
                else:
                    lines.extend(["", f"**Guards:** `when {guards_str}`"])

            # Add relationship information if enabled
            if show_relationships:
                dependencies = result.get("dependencies", [])
                if dependencies:
                    lines.append("")
                    lines.append(f"{indent}📞 Calls these functions:")
                    for dep in dependencies[:5]:  # Limit to 5 for brevity
                        dep_module = dep.get("module", "?")
                        dep_func = dep.get("function", "?")
                        dep_arity = dep.get("arity", "?")
                        dep_line = dep.get("line", "?")
                        lines.append(
                            f"{indent}   • {dep_module}.{dep_func}/{dep_arity} (line {dep_line})"
                        )
                    if len(dependencies) > 5:
                        lines.append(f"{indent}   ... and {len(dependencies) - 5} more")

            # Add call sites
            call_sites = result.get("call_sites", [])
            call_sites_with_examples = result.get("call_sites_with_examples", [])

            if call_sites:
                lines.extend(
                    ModuleFormatter._format_call_sites(call_sites, call_sites_with_examples, indent)
                )
            else:
                lines.append(f"{indent}*No call sites found*")
                lines.append("")
                lines.append(f"{indent}💭 Possible reasons:")
                lines.append(f"{indent}   • Dead code → Use find_dead_code() to verify")
                lines.append(f"{indent}   • Public API → Not called internally but used by clients")
                lines.append(f"{indent}   • New code → Check when added with get_commit_history()")

                # Smart suggestion based on available data
                if pr_info:
                    if pr_info.get("comment_count", 0) > 0:
                        lines.append(
                            f"{indent}   • {pr_info['comment_count']} PR review comments exist → get_file_pr_history(\"{file_path}\")"
                        )
                    else:
                        lines.append(
                            f"{indent}   • Added in PR #{pr_info['number']} → get_file_pr_history(\"{file_path}\")"
                        )

        # Add closing separator for single results
        if len(consolidated_results) == 1:
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
            # Count total calls
            total_calls = sum(len(fc["calls"]) for fc in function_calls)
            lines.extend(
                [
                    f"## Function Calls ({len(function_calls)} module(s), {total_calls} function(s)):",
                    "",
                ]
            )

            for fc in function_calls:
                lines.append(f"### `{fc['calling_module']}`")
                lines.append(f"  `{fc['file']}`")
                lines.append("")

                for call in fc["calls"]:
                    alias_info = f" (via `{call['alias_used']}`)" if call["alias_used"] else ""
                    # Show unique line numbers for this function
                    line_list = ", ".join(f":{line}" for line in sorted(call["lines"]))
                    lines.append(
                        f"  - `{call['function']}/{call['arity']}`{alias_info} — {line_list}"
                    )

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
        _keywords: list[str], results: list[dict[str, Any]], show_scores: bool = True
    ) -> str:
        """
        Format keyword search results as Markdown.

        Args:
            keywords: The search keywords
            results: List of search result dictionaries
            show_scores: Whether to show relevance scores. Defaults to True.

        Returns:
            Formatted Markdown string
        """
        lines: list[str] = []

        for _, result in enumerate(results, 1):
            result_type = result["type"]
            name = result["name"]
            file_path = result["file"]
            line = result["line"]
            score = result["score"]
            _confidence = result["confidence"]
            matched_keywords = result["matched_keywords"]

            # Compact format with type indication
            type_label = "Module" if result_type == "module" else "Function"
            lines.append(f"{type_label}: {name}")
            if show_scores:
                lines.append(f"Score: {score:.4f}")
            lines.append(f"Path: {file_path}:{line}")
            lines.append(f"Matched: {', '.join(matched_keywords) if matched_keywords else 'None'}")

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
