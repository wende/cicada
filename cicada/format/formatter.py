#!/usr/bin/env python
"""
Formatter Module - Formats module search results in various formats.

This module provides formatting utilities for Cicada MCP server responses,
supporting both Markdown and JSON output formats.
"""

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from cicada.languages.formatter_registry import get_language_formatter
from cicada.utils import (
    CallSiteFormatter,
    FunctionGrouper,
    SignatureBuilder,
    find_similar_names,
)
from cicada.utils.truncation import TruncationHelper

# Display limits for compact output
MAX_COCHANGE_FILES = 3  # Maximum co-change files to show before truncating
COMMENT_PREVIEW_LIMIT = 100
COMMENT_ELLIPSIS = "..."


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
        # Support both Elixir (def/defp) and SCIP/Python (public/private) type conventions
        public_funcs = [f for f in functions if f["type"] in ("def", "public")]
        private_funcs = [f for f in functions if f["type"] in ("defp", "private")]

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
    def _format_func_ref(module: str, func: str, arity: int, language: str = "elixir") -> str:
        """Format function reference using language-appropriate notation.

        Args:
            module: Module name
            func: Function name
            arity: Function arity
            language: Programming language for notation style

        Returns:
            Formatted string (e.g., "Module.func/2" for Elixir, "Module.func()" for TypeScript)
        """
        from cicada.languages.formatter_registry import get_language_formatter

        formatter = get_language_formatter(language)
        return formatter.format_function_identifier(module, func, arity)

    @staticmethod
    def _format_caller_name(site: dict[str, Any], language: str = "elixir") -> str:
        """Format caller name from a call site.

        Args:
            site: Call site dictionary with 'calling_module' and optionally 'calling_function'
            language: Programming language for formatting

        Returns:
            Formatted caller string (e.g., "Module.func/2" or "Module.func()")
        """
        calling_func = site.get("calling_function")
        if calling_func:
            return ModuleFormatter._format_func_ref(
                site["calling_module"],
                calling_func["name"],
                calling_func["arity"],
                language,
            )
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
    def _get_language_from_func(func: dict[str, Any]) -> str:
        """Detect language from function type field."""
        # Elixir uses 'def'/'defp', Python uses 'public'/'private'
        func_type = func.get("type", "")
        return "elixir" if func_type in ("def", "defp") else "python"

    @staticmethod
    def _format_function_name(func: dict[str, Any], name: str, arity: int) -> str:
        """Format function name using language-specific formatter."""
        language = ModuleFormatter._get_language_from_func(func)
        formatter = get_language_formatter(language)
        args = func.get("args")
        return formatter.format_function_name(name, arity, args)

    @staticmethod
    def _append_function_section(
        lines: list[str],
        grouped_funcs: dict[tuple[str, int], list[dict[str, Any]]],
        title: str,
        include_specs: bool = False,
    ) -> bool:
        """Append a formatted function section. Returns True if anything was added."""
        if not grouped_funcs:
            return False

        lines.extend(["", f"{title}:", ""])
        for (name, arity), clauses in sorted(grouped_funcs.items(), key=lambda x: x[1][0]["line"]):
            func = clauses[0]
            if include_specs:
                # Full signature in verbose mode
                func_sig = SignatureBuilder.build(func)
                lines.append(f"{func['line']:>5}: {func_sig}")
            else:
                # Compact: language-appropriate identifier with return type if available
                func_id = ModuleFormatter._format_function_name(func, name, arity)
                return_type = SignatureBuilder.get_return_type(func)
                if return_type:
                    lines.append(f"{func['line']:>5}: {func_id} → {return_type}")
                else:
                    lines.append(f"{func['line']:>5}: {func_id}")
            lines.append("")
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
        detailed_dependencies: dict | None = None,
        format_opts: dict | None = None,
    ) -> str:
        """
        Format module data as Markdown.

        Args:
            module_name: The name of the module
            data: The module data dictionary from the index
            visibility: Which functions to show: 'public' (default), 'private', or 'all'
            pr_info: Optional PR context (number, title, comment_count)
            staleness_info: Optional staleness info (is_stale, age_str)
            detailed_dependencies: Optional detailed dependency information
            format_opts: Optional formatting options:
                - include_docs: Include function documentation (default: False)
                - include_specs: Include full type signatures (default: False)
                - include_moduledoc: Include module documentation (default: False)

        Returns:
            Formatted Markdown string
        """
        opts = format_opts or {}
        public_grouped, private_grouped = ModuleFormatter._group_functions_by_visibility(data)

        # Count unique functions, not function clauses
        public_count = len(public_grouped)
        private_count = len(private_grouped)

        # Check module_kind for type-aware formatting
        module_kind = data.get("module_kind", "module")

        # Build the markdown output - compact format
        lines = [f"{data['file']}:{data['line']}"]

        # Type-aware header based on module_kind
        if module_kind == "type_alias":
            # Type aliases don't have functions - show as type
            lines.append(f"{module_name} (type alias)")
        elif module_kind == "interface":
            # Interfaces have methods, not functions
            method_count = public_count + private_count
            if method_count > 0:
                lines.append(f"{module_name} (interface) • {method_count} method(s)")
            else:
                lines.append(f"{module_name} (interface)")
        elif module_kind == "struct":
            # Structs may have fields/methods
            lines.append(
                f"{module_name} (struct) • {public_count} public • {private_count} private"
            )
        elif module_kind == "enum":
            # Enums have variants
            lines.append(f"{module_name} (enum) • {public_count} public • {private_count} private")
        elif module_kind == "trait":
            # Traits have methods
            method_count = public_count + private_count
            if method_count > 0:
                lines.append(f"{module_name} (trait) • {method_count} method(s)")
            else:
                lines.append(f"{module_name} (trait)")
        else:
            # Default: class or module - standard format
            lines.append(f"{module_name} • {public_count} public • {private_count} private")

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

        # Add moduledoc if present and requested
        if opts.get("include_moduledoc") and data.get("moduledoc"):
            doc = data["moduledoc"].strip()
            # Get first paragraph (up to double newline or first 200 chars)
            first_para = doc.split("\n\n")[0].strip()
            if len(first_para) > 200:
                first_para = first_para[:200] + "..."
            lines.extend(["", first_para])

        # Add Classes section if present (Python modules with classes)
        if data.get("classes"):
            classes = data["classes"]
            if classes:
                lines.extend(["", "**Classes:**"])
                for cls in classes:
                    cls_name = cls["name"]
                    cls_line = cls["line"]
                    cls_public = cls.get("public_methods", 0)
                    cls_private = cls.get("private_methods", 0)
                    lines.append(
                        f"  • {cls_name} (line {cls_line}) • {cls_public} public • {cls_private} private"
                    )
                    # Optionally show class doc as sub-bullet
                    if cls.get("doc"):
                        # Skip code fence and class signature to get actual docstring
                        doc_lines = cls["doc"].strip().split("\n")
                        # Find first non-fence, non-signature line
                        doc_text = None
                        for line in doc_lines:
                            stripped = line.strip()
                            # Skip code fences and class/def/async def signatures
                            if (
                                stripped
                                and not stripped.startswith("```")
                                and not stripped.startswith("class ")
                                and not stripped.startswith("def ")
                                and not stripped.startswith("async def ")
                            ):
                                doc_text = stripped
                                break

                        if doc_text:
                            doc_preview = doc_text[:80]
                            if len(doc_text) > 80:
                                doc_preview += "..."
                            lines.append(f"    {doc_preview}")

        private_shown = False
        include_specs = opts.get("include_specs", False)

        if visibility != "private":
            ModuleFormatter._append_function_section(lines, public_grouped, "Public", include_specs)

        if visibility in ["all", "private"]:
            private_shown = ModuleFormatter._append_function_section(
                lines, private_grouped, "Private", include_specs
            )

        if visibility == "private" and not private_shown:
            lines.extend(["", "*No private functions found*"])

        # Add detailed dependencies if provided
        if detailed_dependencies:
            lines.extend(["", "---", ""])

            # Direct dependencies
            if detailed_dependencies.get("direct"):
                lines.append(f"## Dependencies ({len(detailed_dependencies['direct'])})")
                lines.append("")
                for dep in detailed_dependencies["direct"]:
                    lines.append(f"  • {dep}")
                lines.append("")

            # Transitive dependencies
            if detailed_dependencies.get("transitive"):
                trans = detailed_dependencies["transitive"]
                total_transitive = len(trans)
                lines.append(f"## Transitive Dependencies ({total_transitive})")
                lines.append("")
                for dep, required_by in sorted(trans.items()):
                    via = ", ".join(required_by)
                    lines.append(f"  • {dep} (via {via})")
                lines.append("")

            # Granular function usage
            if detailed_dependencies.get("granular"):
                gran = detailed_dependencies["granular"]
                lines.append("## Function Usage")
                lines.append("")
                for dep_module, func_sigs in sorted(gran.items()):
                    lines.append(f"### {dep_module}")
                    lines.append(f"Used by {len(func_sigs)} function(s):")
                    for sig in func_sigs:
                        lines.append(f"  • {sig}")
                    lines.append("")

        # Add co-change files if present (show top 3 for compactness)
        cochange_files = data.get("cochange_files", [])
        if cochange_files:
            lines.extend(["", "---", "", "## Often Changed With"])
            lines.append("")
            for cf in cochange_files[:MAX_COCHANGE_FILES]:
                module_name_display = cf.get("module") or cf["file"].split("/")[-1]
                lines.append(f"  • {module_name_display} ({cf['count']} commits)")
            if len(cochange_files) > MAX_COCHANGE_FILES:
                lines.append(f"  ... and {len(cochange_files) - MAX_COCHANGE_FILES} more")

        return "\n".join(lines)

    @staticmethod
    def format_module_json(
        module_name: str,
        data: dict[str, Any],
        visibility: str = "public",
        detailed_dependencies: dict | None = None,
    ) -> str:
        """
        Format module data as JSON.

        Args:
            module_name: The name of the module
            data: The module data dictionary from the index
            visibility: Which functions to show: 'public' (default), 'private', or 'all'
            detailed_dependencies: Optional detailed dependency information

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

        # Calculate function counts if not provided
        if "public_functions" in data and "private_functions" in data:
            public_count = data["public_functions"]
            private_count = data["private_functions"]
        else:
            public_count, private_count = ModuleFormatter._count_functions(data)

        result = {
            "module": module_name,
            "location": f"{data['file']}:{data['line']}",
            "moduledoc": data.get("moduledoc"),
            "counts": {
                "public": public_count,
                "private": private_count,
            },
            "functions": functions,
        }

        # Add classes if present (Python modules with classes)
        if data.get("classes"):
            result["classes"] = data["classes"]

        # Include detailed dependencies if provided
        if detailed_dependencies:
            result["dependencies"] = detailed_dependencies

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
                lines.append(f"  • Semantic search: query(['{last_component.lower()}'])")

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
        language: str = "elixir",
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
            ModuleFormatter._format_grouped_sites(
                truncated_sites, indent, include_examples, language
            )
        )

        if truncation_msg:
            lines.append(f"{indent}{truncation_msg}")

        return lines

    @staticmethod
    def _format_remaining_sites(
        label: str,
        sites: list[dict[str, Any]],
        indent: str,
        prepend_blank: bool = False,
        language: str = "elixir",
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
            caller = ModuleFormatter._format_caller_name(site, language)
            line_list = ", ".join(f":{line}" for line in site["lines"])
            lines.append(f"{indent}- {caller} at {site['file']}{line_list}")
        return lines

    @staticmethod
    def _format_grouped_sites(
        grouped_sites, indent, include_examples: bool, language: str = "elixir"
    ) -> list[str]:
        lines: list[str] = []
        for site in grouped_sites:
            caller = ModuleFormatter._format_caller_name(site, language)

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
                    lines.append(f"{indent}  ```")
                    code_lines = code_entry["code"].split("\n")
                    for code_line in code_lines:
                        lines.append(f"{indent}  {code_line}")
                    lines.append(f"{indent}  ```")
                    lines.append("")
        return lines

    @staticmethod
    def _format_remaining_call_sites(
        call_sites, call_sites_with_examples, indent, language: str = "elixir"
    ):
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
                    ModuleFormatter._format_remaining_sites(
                        "Code", remaining_code, indent, language=language
                    )
                )

            if remaining_test:
                lines.extend(
                    ModuleFormatter._format_remaining_sites(
                        "Test",
                        remaining_test,
                        indent,
                        prepend_blank=bool(remaining_code),
                        language=language,
                    )
                )
        return lines

    @staticmethod
    def _format_call_sites_without_examples(call_sites, indent, language: str = "elixir"):
        lines = []
        code_sites, test_sites = ModuleFormatter._split_call_sites(call_sites)

        call_count = len(call_sites)
        lines.append("")
        lines.append(f"{indent}Called {call_count} times:")
        lines.append("")

        if code_sites:
            lines.extend(
                ModuleFormatter._format_call_site_section(
                    "Code", code_sites, indent, include_examples=False, language=language
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
                    language=language,
                )
            )
        lines.append("")
        return lines

    @staticmethod
    def _format_call_sites_with_examples(
        call_sites, call_sites_with_examples, indent, language: str = "elixir"
    ):
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
                    language=language,
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
                    language=language,
                )
            )

        lines.extend(
            ModuleFormatter._format_remaining_call_sites(
                call_sites, call_sites_with_examples, indent, language
            )
        )
        return lines

    @staticmethod
    def _format_call_sites(call_sites, call_sites_with_examples, indent, language: str = "elixir"):
        lines = []
        # Check if we have usage examples (code lines)
        has_examples = len(call_sites_with_examples) > 0

        if has_examples:
            lines.extend(
                ModuleFormatter._format_call_sites_with_examples(
                    call_sites, call_sites_with_examples, indent, language
                )
            )
        else:
            lines.extend(
                ModuleFormatter._format_call_sites_without_examples(call_sites, indent, language)
            )
        return lines

    @staticmethod
    def _format_function_entry(
        result: dict[str, Any],
        single_result: bool,
        show_relationships: bool,
        language: str = "elixir",
        format_opts: dict | None = None,
    ) -> list[str]:
        """Format a single function search result (either single or multi layout)."""
        opts = format_opts or {}
        include_docs = opts.get("include_docs", False)
        include_specs = opts.get("include_specs", False)

        module_name = result["module"]
        func = result["function"]
        file_path = result["file"]
        pr_info = result.get("pr_info")
        sig = SignatureBuilder.build(func)
        call_sites = result.get("call_sites", [])
        call_sites_with_examples = result.get("call_sites_with_examples", [])

        # Format function identifier using language-specific formatter
        language_formatter = get_language_formatter(language)
        func_identifier = language_formatter.format_function_identifier(
            module_name, func["name"], func["arity"]
        )

        lines: list[str] = []

        if single_result:
            lines.append(f"{file_path}:{func['line']}")
            lines.append(func_identifier)
            if include_specs:
                lines.append(f"Type: {sig}")
            lines.extend(ModuleFormatter._format_pr_context(pr_info, file_path))
        else:
            lines.extend(["", "---", "", func_identifier])
            if include_specs:
                lines.extend(
                    [
                        f"{file_path}:{func['line']} • {func['type']}",
                        "",
                        "Signature:",
                        f"{sig}",
                    ]
                )
            else:
                lines.append(f"{file_path}:{func['line']}")
            pr_lines = ModuleFormatter._format_pr_context(pr_info, file_path)
            if pr_info and pr_info.get("comment_count", 0) > 0 and len(pr_lines) > 2:
                pr_lines[-1] = f"{pr_info['comment_count']} review comment(s) available"
            lines.extend(pr_lines)

        if include_docs and func.get("doc"):
            doc_lines = ['Documentation: """', func["doc"], '"""']
            if single_result:
                lines.extend(doc_lines)
            else:
                lines.extend(["", *doc_lines])

        if include_docs and func.get("examples"):
            lines.extend(["", "Examples:", "", func["examples"]])

        # Display comment sources if available
        comment_sources = result.get("comment_sources", [])
        if comment_sources:
            lines.extend(["", "Inline comments:"])
            for comment_info in comment_sources[:5]:  # Limit to 5
                comment_text = comment_info["comment"]
                comment_line = comment_info["line"]
                is_multiline = "\n" in comment_text
                display_text = comment_text.split("\n")[0] if is_multiline else comment_text

                was_truncated = len(display_text) > COMMENT_PREVIEW_LIMIT
                if was_truncated:
                    display_text = (
                        display_text[: COMMENT_PREVIEW_LIMIT - len(COMMENT_ELLIPSIS)]
                        + COMMENT_ELLIPSIS
                    )
                elif is_multiline:
                    # Indicate multi-line without implying truncation
                    display_text = display_text + " [+lines]"

                lines.append(f'   • "# {display_text}" (:{comment_line})')
            if len(comment_sources) > 5:
                lines.append(f"   ... and {len(comment_sources) - 5} more comments")

        if func.get("guards"):
            guards_str = ", ".join(func["guards"])
            if single_result:
                lines.append(f"  Guards: when {guards_str}")
            else:
                lines.extend(["", f"**Guards:** `when {guards_str}`"])

        if show_relationships:
            # Check for detailed dependencies first (from what_it_calls=true)
            detailed_deps = result.get("detailed_dependencies")
            if detailed_deps is not None:
                internal = detailed_deps.get("internal", [])
                external = detailed_deps.get("external", [])
                # Derive total from actual data to avoid inconsistencies
                total = len(internal) + len(external)

                # Only show section if there are actual dependencies
                if total > 0:
                    lines.append("")
                    lines.append("Calls these functions:")

                    # Show internal dependencies first
                    for dep in internal[:5]:
                        dep_module = dep.get("module", "?")
                        dep_func = dep.get("function", "?")
                        dep_arity = dep.get("arity", 0)
                        dep_line = dep.get("line", "?")
                        func_ref = ModuleFormatter._format_func_ref(
                            dep_module, dep_func, dep_arity, language
                        )
                        lines.append(f"   • {func_ref} :{dep_line}")

                    # Show external dependencies
                    remaining = 5 - len(internal[:5])
                    for dep in external[:remaining]:
                        dep_module = dep.get("module", "?")
                        dep_func = dep.get("function", "?")
                        dep_arity = dep.get("arity", 0)
                        dep_line = dep.get("line", "?")
                        func_ref = ModuleFormatter._format_func_ref(
                            dep_module, dep_func, dep_arity, language
                        )
                        lines.append(f"   • {func_ref} :{dep_line}")

                    shown = min(5, len(internal) + len(external))
                    if total > shown:
                        lines.append(f"   ... and {total - shown} more")
            else:
                # Fallback to simple dependencies list (legacy format)
                dependencies = result.get("dependencies", [])
                if dependencies:
                    lines.append("")
                    lines.append("Calls these functions:")
                    for dep in dependencies[:5]:
                        dep_module = dep.get("module", "?")
                        dep_func = dep.get("function", "?")
                        dep_arity = dep.get("arity", 0)
                        dep_line = dep.get("line", "?")
                        func_ref = ModuleFormatter._format_func_ref(
                            dep_module, dep_func, dep_arity, language
                        )
                        lines.append(f"   • {func_ref} :{dep_line}")
                    if len(dependencies) > 5:
                        lines.append(f"   ... and {len(dependencies) - 5} more")

        if call_sites:
            lines.extend(
                ModuleFormatter._format_call_sites(
                    call_sites, call_sites_with_examples, "", language
                )
            )
        else:
            lines.append("*No call sites found*")
            lines.append("")

        return lines

    @staticmethod
    def _split_function_name_to_keywords(func_name: str) -> list[str]:
        """
        Split a function name into keywords for semantic search.

        Examples:
            _extract_cochange -> ['extract', 'cochange']
            getUserData -> ['get', 'user', 'data']
            create_user -> ['create', 'user']
        """
        import re

        # Remove leading underscores
        name = func_name.lstrip("_")
        # Split on underscores and camelCase boundaries
        parts = re.split(r"_|(?<=[a-z])(?=[A-Z])", name)
        # Filter empty strings and lowercase all parts
        return [p.lower() for p in parts if p]

    @staticmethod
    def format_function_results_markdown(
        function_name: str,
        results: list[dict[str, Any]],
        staleness_info: dict | None = None,
        show_relationships: bool = True,
        language: str = "elixir",
        private_suggestion: str | None = None,
        format_opts: dict | None = None,
        fallback_note: str | None = None,
    ) -> str:
        """
        Format function search results as Markdown.

        Args:
            function_name: The searched function name
            results: List of function matches with module context
            staleness_info: Optional staleness info (is_stale, age_str)
            show_relationships: Whether to show relationship information (what this calls / what calls this)
            language: Programming language for formatting function identifiers
            private_suggestion: Optional suggestion for private function pattern
            format_opts: Optional dict with include_docs, include_specs for compact output
            fallback_note: Optional note about fallback search (e.g., "No matches in X, showing all")

        Returns:
            Formatted Markdown string
        """
        if not results:
            # Extract just the function name without module/arity for suggestions
            func_only = function_name.split(".")[-1].split("/")[0]

            # Split function name into keywords for semantic search
            keywords = ModuleFormatter._split_function_name_to_keywords(func_only)
            if len(keywords) > 1:
                keywords_str = ", ".join(f"'{k}'" for k in keywords)
                query_suggestion = f"query([{keywords_str}])"
            else:
                # Single keyword: use processed keyword for consistency with splitting logic
                query_suggestion = f"query(['{keywords[0] if keywords else func_only.lower()}'])"

            # Build error message
            error_parts = []

            # Add staleness warning if applicable
            if staleness_info and staleness_info.get("is_stale"):
                error_parts.append(
                    f"WARNING: Index may be stale (index is {staleness_info['age_str']} old, files have been modified)\n"
                    f"   Please ask the user to run: cicada index\n"
                )

            # Compact one-liner error with actionable suggestions
            if private_suggestion:
                error_parts.append(
                    f"Not found: `{function_name}`. Try: `{private_suggestion}` (private) | `*{func_only}*` | {query_suggestion}"
                )
            else:
                error_parts.append(
                    f"Not found: `{function_name}`. Try: `*{func_only}*` | {query_suggestion}"
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
            # Add fallback note if present (even for single result)
            if fallback_note:
                lines.append(f"({fallback_note})")
                lines.append("")
        else:
            # Add fallback note to the found count line if present
            found_line = f"Found {len(consolidated_results)} match(es):"
            if fallback_note:
                found_line = f"Found {len(consolidated_results)} match(es) ({fallback_note}):"
            lines.extend(
                [
                    f"Functions matching {function_name}",
                    "",
                    found_line,
                ]
            )

        for result in consolidated_results:
            lines.extend(
                ModuleFormatter._format_function_entry(
                    result, single_result, show_relationships, language, format_opts
                )
            )

        # Add closing separator for single results
        if single_result:
            lines.append("---")

        return "\n".join(lines)

    @staticmethod
    def format_function_results_json(
        function_name: str,
        results: list[dict[str, Any]],
        language: str = "elixir",
    ) -> str:
        """
        Format function search results as JSON.

        Args:
            function_name: The searched function name
            results: List of function matches with module context
            language: Programming language for formatting

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
            full_name = ModuleFormatter._format_func_ref(
                result["module"],
                result["function"]["name"],
                result["function"]["arity"],
                language,
            )
            func_entry = {
                "module": result["module"],
                "moduledoc": result.get("moduledoc"),
                "function": result["function"]["name"],
                "arity": result["function"]["arity"],
                "full_name": full_name,
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
    def format_module_usage_markdown(
        module_name: str, usage_results: dict[str, Any], language: str = "elixir"
    ) -> str:
        """
        Format module usage results as Markdown.

        Args:
            module_name: The module being searched for
            usage_results: Dictionary with usage category keys
            language: Programming language for formatting (default: elixir)

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
            for _func_key, func_data in sorted(called_functions.items()):
                num_functions = len(func_data["calling_functions"])
                # Format using language-appropriate notation (not hardcoded /arity)
                display_name = ModuleFormatter._format_func_ref(
                    module_name,
                    func_data["name"],
                    func_data["arity"],
                    language,
                )
                lines.append(
                    f"- {display_name} — {func_data['total_calls']} calls in {num_functions} function(s)"
                )

                # Display calling functions
                for caller in func_data["calling_functions"]:
                    if caller["function"]:
                        # Regular function call - use language-appropriate notation
                        func_sig = ModuleFormatter._format_func_ref(
                            caller["module"],
                            caller["function"],
                            caller["arity"],
                            language,
                        )
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
    def _format_related_items(
        items: list[dict[str, Any]],
        title: str,
        formatter: Callable[[dict[str, Any]], tuple[str, int]],
        top_n: int = 5,
    ) -> list[str]:
        """
        Format a list of related items with counts.

        Args:
            items: List of item dictionaries
            title: Header text for the section
            formatter: Function that converts item dict to (display_name, count) tuple
            top_n: Maximum number of items to display

        Returns:
            List of formatted lines
        """
        sorted_items = sorted(items, key=lambda x: x.get("count", 0), reverse=True)
        lines = [title]

        for item in sorted_items[:top_n]:
            display_name, count = formatter(item)
            lines.append(f"  • {display_name} ({count} commits)")

        if len(sorted_items) > top_n:
            lines.append(f"  ... and {len(sorted_items) - top_n} more")

        return lines

    @staticmethod
    def _format_cochange_info(cochange_info: dict[str, Any], language: str = "elixir") -> list[str]:
        """
        Format co-change information for display.

        Args:
            cochange_info: Dictionary with 'related_files' and/or 'related_functions' keys
            language: Programming language for formatting (default: elixir)

        Returns:
            List of formatted lines
        """
        lines: list[str] = []

        # Display related files
        related_files = cochange_info.get("related_files", [])
        if related_files:

            def format_file(f: dict[str, Any]) -> tuple[str, int]:
                module_name = f.get("module")
                file_path = f.get("file", "")
                display_name = (
                    module_name if module_name else file_path.split("/")[-1].replace(".ex", "")
                )
                return display_name, f.get("count", 0)

            lines.extend(
                ModuleFormatter._format_related_items(
                    related_files, "Often changed with:", format_file, top_n=5
                )
            )

        # Display related functions
        related_functions = cochange_info.get("related_functions", [])
        if related_functions:

            def format_function(f: dict[str, Any]) -> tuple[str, int]:
                module = f.get("module", "?")
                function = f.get("function", "?")
                arity = f.get("arity", 0)
                # Use language-appropriate notation (not hardcoded /arity)
                display_name = ModuleFormatter._format_func_ref(module, function, arity, language)
                return display_name, f.get("count", 0)

            lines.extend(
                ModuleFormatter._format_related_items(
                    related_functions, "Related functions:", format_function, top_n=5
                )
            )

        return lines

    @staticmethod
    def format_keyword_search_results_markdown(
        results: list[dict[str, Any]],
        show_scores: bool = True,
        language: str = "elixir",
    ) -> str:
        """
        Format keyword search results as Markdown.

        Args:
            results: List of search result dictionaries
            show_scores: Whether to show relevance scores. Defaults to True.
            language: Programming language for formatting (default: elixir)

        Returns:
            Formatted Markdown string
        """
        lines: list[str] = []

        for idx, result in enumerate(results, 1):
            name = result["name"]
            file_path = result["file"]
            line = result["line"]
            score = result["score"]
            matched_keywords = result["matched_keywords"]

            # Compact header: number, name, and score on first line
            if show_scores:
                lines.append(f"{idx}. {name} | {score:.2f}")
            else:
                lines.append(f"{idx}. {name}")

            # Path on second line
            lines.append(f"{file_path}:{line}")

            # Show co-change information if available
            cochange_info = result.get("cochange_info")
            if cochange_info:
                cochange_lines = ModuleFormatter._format_cochange_info(cochange_info, language)
                if cochange_lines:  # Only add if there's actual content
                    lines.extend(cochange_lines)

            # First line of documentation only
            doc = result.get("doc")
            if doc:
                doc_lines = doc.strip().split("\n")
                first_line = doc_lines[0] if doc_lines else ""
                # Wrap at ~100 characters
                if len(first_line) > 100:
                    first_line = first_line[:100] + "..."
                lines.append(first_line)

            # Matched keywords with source indicators
            if matched_keywords:
                keyword_sources = result.get("keyword_sources", {})
                kw_with_sources: list[str] = []
                for kw in matched_keywords:
                    source = keyword_sources.get(kw)
                    if source == "docs":
                        kw_with_sources.append(kw + " (in docs)")
                    elif source == "strings":
                        kw_with_sources.append(kw + " (in strings)")
                    elif source == "comments":
                        kw_with_sources.append(kw + " (in comments)")
                    elif source == "both":
                        # Backward compatibility for old "both" format
                        kw_with_sources.append(kw + " (in docs+strings)")
                    elif source and "+" in source:
                        # New combined format: docs+strings+comments
                        kw_with_sources.append(kw + f" (in {source})")
                    else:
                        kw_with_sources.append(kw)
                lines.append("Matched keywords: " + ", ".join(kw_with_sources))

            lines.append("")  # Blank line between results

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
