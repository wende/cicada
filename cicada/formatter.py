#!/usr/bin/env python
"""
Formatter Module - Formats module search results in various formats.

This module provides formatting utilities for Cicada MCP server responses,
supporting both Markdown and JSON output formats.
"""

import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import argparse

from cicada.utils import FunctionGrouper, CallSiteFormatter, SignatureBuilder


class ModuleFormatter:
    """Formats Cicada module data in various output formats."""

    @staticmethod
    def _format_function_signature(func: Dict[str, Any]) -> str:
        """
        Format function signature with arguments, types, and return type.

        Args:
            func: Function dictionary with name, args, optionally args_with_types and return_type

        Returns:
            Formatted signature like "func_name(arg1: type1, arg2: type2) :: return_type"
        """
        return SignatureBuilder.build(func)

    @staticmethod
    def _group_functions_by_name_arity(
        funcs: list[Dict[str, Any]],
    ) -> Dict[tuple, list[Dict[str, Any]]]:
        """
        Group functions by their name and arity.

        Args:
            funcs: List of function dictionaries

        Returns:
            Dictionary mapping (name, arity) tuples to lists of function clauses
        """
        return FunctionGrouper.group_by_name_arity(funcs)

    @staticmethod
    def format_module_markdown(
        module_name: str, data: Dict[str, Any], private_functions: str = "exclude"
    ) -> str:
        """
        Format module data as Markdown.

        Args:
            module_name: The name of the module
            data: The module data dictionary from the index
            private_functions: How to handle private functions: 'exclude' (hide), 'include' (show all), or 'only' (show only private)

        Returns:
            Formatted Markdown string
        """
        # Group functions by type (def = public, defp = private)
        public_funcs = [f for f in data["functions"] if f["type"] == "def"]
        private_funcs = [f for f in data["functions"] if f["type"] == "defp"]

        # Group by name/arity to deduplicate function clauses
        public_grouped = ModuleFormatter._group_functions_by_name_arity(public_funcs)
        private_grouped = ModuleFormatter._group_functions_by_name_arity(private_funcs)

        # Count unique functions, not function clauses
        public_count = len(public_grouped)
        private_count = len(private_grouped)

        # Build the markdown output - compact format
        lines = [
            module_name,
            "",
            f"{data['file']}:{data['line']} • {public_count} public • {private_count} private",
        ]

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
            for (_, _), clauses in sorted(
                public_grouped.items(), key=lambda x: x[1][0]["line"]
            ):
                # Use the first clause for display (they all have same name/arity)
                func = clauses[0]
                func_sig = ModuleFormatter._format_function_signature(func)
                lines.append(f"{func['line']:>5}: {func_sig}")

        # Show private functions (if private_functions == "include" or "only")
        if private_grouped and private_functions in ["include", "only"]:
            lines.extend(["", "Private:", ""])
            # Sort by line number instead of function name
            for (_, _), clauses in sorted(
                private_grouped.items(), key=lambda x: x[1][0]["line"]
            ):
                # Use the first clause for display (they all have same name/arity)
                func = clauses[0]
                func_sig = ModuleFormatter._format_function_signature(func)
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
        module_name: str, data: Dict[str, Any], private_functions: str = "exclude"
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
        grouped = ModuleFormatter._group_functions_by_name_arity(filtered_funcs)

        # Compact function format - one entry per unique name/arity
        functions = [
            {
                "signature": ModuleFormatter._format_function_signature(clauses[0]),
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
    def format_error_markdown(module_name: str, total_modules: int) -> str:
        """
        Format error message as Markdown.

        Args:
            module_name: The queried module name
            total_modules: Total number of modules in the index

        Returns:
            Formatted Markdown error message
        """
        return f"""# Module Not Found

**Query:** `{module_name}`

The module `{module_name}` was not found in the index.

## Suggestions

- Verify the exact module name as it appears in the code
- Check that the module is part of the indexed codebase
- Total modules available in index: **{total_modules}**

## Note

Module names are case-sensitive and must match exactly (e.g., `MyApp.User`, not `myapp.user`).
"""

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
    def _group_call_sites_by_caller(
        call_sites: list[Dict[str, Any]],
    ) -> list[Dict[str, Any]]:
        """
        Group call sites by their caller (calling_module + calling_function).

        Args:
            call_sites: List of call site dictionaries

        Returns:
            List of grouped call sites with consolidated line numbers
        """
        return CallSiteFormatter.group_by_caller(call_sites)

    @staticmethod
    def format_function_results_markdown(
        function_name: str, results: list[Dict[str, Any]]
    ) -> str:
        """
        Format function search results as Markdown.

        Args:
            function_name: The searched function name
            results: List of function matches with module context

        Returns:
            Formatted Markdown string
        """
        if not results:
            return f"""# Function Not Found

**Query:** `{function_name}`

No functions matching `{function_name}` were found in the index.

## Suggestions

- Verify the function name spelling
- Try searching without arity (e.g., 'create_user' instead of 'create_user/2')
- Check that the function is part of the indexed codebase
"""

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

        # For single results (e.g., MFA search), use simpler header
        if len(consolidated_results) == 1:
            lines = [
                f"{consolidated_results[0]['module']}.{consolidated_results[0]['function']['name']}/{consolidated_results[0]['function']['arity']}"
            ]
        else:
            lines = [
                f"Functions matching {function_name}",
                f"",
                f"Found {len(consolidated_results)} match(es):",
            ]

        for result in consolidated_results:
            module_name = result["module"]
            func = result["function"]
            file_path = result["file"]

            # No indentation for single results
            indent = ""

            # Add signature first (right after file path)
            sig = ModuleFormatter._format_function_signature(func)

            # Skip the section header for single results
            if len(consolidated_results) == 1:
                lines.extend(["", f"{file_path}:{func['line']}", f"{indent}{sig}"])
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

            # Add documentation if present
            if func.get("doc"):
                if len(consolidated_results) == 1:
                    lines.extend(
                        ["", f"{indent}Documentation:", "", f"{indent}{func['doc']}"]
                    )
                else:
                    lines.extend(["", "Documentation:", "", func["doc"]])

            # Add examples if present
            if func.get("examples"):
                if len(consolidated_results) == 1:
                    lines.extend(
                        ["", f"{indent}Examples:", "", f"{indent}{func['examples']}"]
                    )
                else:
                    lines.extend(["", "Examples:", "", func["examples"]])

            # Add guards if present (on separate line for idiomatic Elixir style)
            if func.get("guards"):
                guards_str = ", ".join(func["guards"])
                if len(results) == 1:
                    lines.append(f"  Guards: when {guards_str}")
                else:
                    lines.extend(["", f"**Guards:** `when {guards_str}`"])

            # Add call sites
            call_sites = result.get("call_sites", [])
            call_sites_with_examples = result.get("call_sites_with_examples", [])

            if call_sites:
                # Check if we have usage examples (code lines)
                has_examples = len(call_sites_with_examples) > 0

                if has_examples:
                    # Separate into code and test call sites WITH examples
                    code_sites_with_examples = [
                        s
                        for s in call_sites_with_examples
                        if "test" not in s["file"].lower()
                    ]
                    test_sites_with_examples = [
                        s
                        for s in call_sites_with_examples
                        if "test" in s["file"].lower()
                    ]

                    lines.append(f"{indent}Usage Examples:")

                    if code_sites_with_examples:
                        # Group code sites by caller
                        grouped_code = ModuleFormatter._group_call_sites_by_caller(
                            code_sites_with_examples
                        )
                        code_count = sum(len(site["lines"]) for site in grouped_code)
                        lines.append(f"{indent}Code ({code_count}):")
                        for site in grouped_code:
                            # Format calling location with function if available
                            calling_func = site.get("calling_function")
                            if calling_func:
                                caller = f"{site['calling_module']}.{calling_func['name']}/{calling_func['arity']}"
                            else:
                                caller = site["calling_module"]

                            # Show consolidated line numbers only if multiple lines
                            if len(site["lines"]) > 1:
                                line_list = ", ".join(
                                    f":{line}" for line in site["lines"]
                                )
                                lines.append(
                                    f"{indent}- {caller} at {site['file']}{line_list}"
                                )
                            else:
                                lines.append(f"{indent}- {caller} at {site['file']}")

                            # Add the actual code lines if available
                            if site.get("code_lines"):
                                for code_entry in site["code_lines"]:
                                    # Properly indent each line of the code block
                                    code_lines = code_entry["code"].split("\n")
                                    for code_line in code_lines:
                                        lines.append(f"{indent}  {code_line}")

                    if test_sites_with_examples:
                        if code_sites_with_examples:
                            lines.append("")  # Blank line between sections
                        # Group test sites by caller
                        grouped_test = ModuleFormatter._group_call_sites_by_caller(
                            test_sites_with_examples
                        )
                        test_count = sum(len(site["lines"]) for site in grouped_test)
                        lines.append(f"{indent}Test ({test_count}):")
                        for site in grouped_test:
                            # Format calling location with function if available
                            calling_func = site.get("calling_function")
                            if calling_func:
                                caller = f"{site['calling_module']}.{calling_func['name']}/{calling_func['arity']}"
                            else:
                                caller = site["calling_module"]

                            # Show consolidated line numbers only if multiple lines
                            if len(site["lines"]) > 1:
                                line_list = ", ".join(
                                    f":{line}" for line in site["lines"]
                                )
                                lines.append(
                                    f"{indent}- {caller} at {site['file']}{line_list}"
                                )
                            else:
                                lines.append(f"{indent}- {caller} at {site['file']}")

                            # Add the actual code lines if available
                            if site.get("code_lines"):
                                for code_entry in site["code_lines"]:
                                    # Properly indent each line of the code block
                                    code_lines = code_entry["code"].split("\n")
                                    for code_line in code_lines:
                                        lines.append(f"{indent}  {code_line}")

                    # Now show the remaining call sites (those without code examples)
                    # Create a set of call sites that were shown with examples
                    shown_call_lines = set()
                    for site in call_sites_with_examples:
                        shown_call_lines.add((site["file"], site["line"]))

                    # Filter to get call sites not yet shown
                    remaining_call_sites = [
                        site
                        for site in call_sites
                        if (site["file"], site["line"]) not in shown_call_lines
                    ]

                    if remaining_call_sites:
                        # Separate into code and test
                        remaining_code = [
                            s
                            for s in remaining_call_sites
                            if "test" not in s["file"].lower()
                        ]
                        remaining_test = [
                            s
                            for s in remaining_call_sites
                            if "test" in s["file"].lower()
                        ]

                        lines.append("")
                        lines.append(f"{indent}Other Call Sites:")

                        if remaining_code:
                            grouped_remaining_code = (
                                ModuleFormatter._group_call_sites_by_caller(
                                    remaining_code
                                )
                            )
                            remaining_code_count = sum(
                                len(site["lines"]) for site in grouped_remaining_code
                            )
                            lines.append(f"{indent}Code ({remaining_code_count}):")
                            for site in grouped_remaining_code:
                                calling_func = site.get("calling_function")
                                if calling_func:
                                    caller = f"{site['calling_module']}.{calling_func['name']}/{calling_func['arity']}"
                                else:
                                    caller = site["calling_module"]

                                line_list = ", ".join(
                                    f":{line}" for line in site["lines"]
                                )
                                lines.append(
                                    f"{indent}- {caller} at {site['file']}{line_list}"
                                )

                        if remaining_test:
                            if remaining_code:
                                lines.append("")
                            grouped_remaining_test = (
                                ModuleFormatter._group_call_sites_by_caller(
                                    remaining_test
                                )
                            )
                            remaining_test_count = sum(
                                len(site["lines"]) for site in grouped_remaining_test
                            )
                            lines.append(f"{indent}Test ({remaining_test_count}):")
                            for site in grouped_remaining_test:
                                calling_func = site.get("calling_function")
                                if calling_func:
                                    caller = f"{site['calling_module']}.{calling_func['name']}/{calling_func['arity']}"
                                else:
                                    caller = site["calling_module"]

                                line_list = ", ".join(
                                    f":{line}" for line in site["lines"]
                                )
                                lines.append(
                                    f"{indent}- {caller} at {site['file']}{line_list}"
                                )
                else:
                    # Separate into code and test call sites
                    code_sites = [
                        s for s in call_sites if "test" not in s["file"].lower()
                    ]
                    test_sites = [s for s in call_sites if "test" in s["file"].lower()]

                    call_count = len(call_sites)
                    lines.append("")
                    lines.append(f"{indent}Called {call_count} times:")
                    lines.append("")

                    if code_sites:
                        # Group code sites by caller
                        grouped_code = ModuleFormatter._group_call_sites_by_caller(
                            code_sites
                        )
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
                            lines.append(
                                f"{indent}- {caller} at {site['file']}{line_list}"
                            )

                    if test_sites:
                        if code_sites:
                            lines.append("")  # Blank line between sections
                        # Group test sites by caller
                        grouped_test = ModuleFormatter._group_call_sites_by_caller(
                            test_sites
                        )
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
                            lines.append(
                                f"{indent}- {caller} at {site['file']}{line_list}"
                            )
                lines.append("")
            else:
                lines.extend([f"{indent}*No call sites found*"])

        return "\n".join(lines)

    @staticmethod
    def format_function_results_json(
        function_name: str, results: list[Dict[str, Any]]
    ) -> str:
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
                "signature": ModuleFormatter._format_function_signature(
                    result["function"]
                ),
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
        module_name: str, usage_results: Dict[str, Any]
    ) -> str:
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
                lines.append(
                    f"- `{imp['importing_module']}` {alias_info} — `{imp['file']}`"
                )
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
                    alias_info = (
                        f" (via `{call['alias_used']}`)" if call["alias_used"] else ""
                    )
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
    def format_module_usage_json(
        module_name: str, usage_results: Dict[str, Any]
    ) -> str:
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


class JSONFormatter:
    """Formats JSON data with customizable options."""

    def __init__(self, indent: int = 2, sort_keys: bool = False):
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
            raise ValueError(f"Invalid JSON: {e}")

    def format_file(self, input_path: Path, output_path: Optional[Path] = None) -> str:
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
        with open(input_path, "r") as f:
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
