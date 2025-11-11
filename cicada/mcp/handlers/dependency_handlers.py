"""
Dependency Tool Handlers.

Handles tools for analyzing module and function dependencies.
"""

import json
from pathlib import Path
from typing import Any

from mcp.types import TextContent


class DependencyHandler:
    """Handler for dependency analysis tools."""

    def __init__(self, index: dict[str, Any], config: dict[str, Any]):
        """
        Initialize the dependency handler.

        Args:
            index: The code index containing modules and functions
            config: Configuration dictionary
        """
        self.index = index
        self.config = config

    def _format_dependency_with_context(
        self,
        dep: dict,
        context_lines: dict,
        include_context: bool,
        include_module: bool = False,
    ) -> list[str]:
        """
        Format a single dependency with optional code context.

        Args:
            dep: Dependency dict with module, function, arity, line
            context_lines: Dict mapping line numbers to code context
            include_context: Whether to include code context
            include_module: Whether to include module name in output

        Returns:
            List of formatted lines
        """
        lines = []
        line_info = f":{dep['line']}"

        if include_module:
            lines.append(f"- {dep['module']}.{dep['function']}/{dep['arity']} {line_info}")
        else:
            lines.append(f"- {dep['function']}/{dep['arity']} {line_info}")

        if include_context and dep["line"] in context_lines:
            lines.append("  ```elixir")
            lines.append(f"  {context_lines[dep['line']]}")
            lines.append("  ```")

        return lines

    async def get_module_dependencies(
        self, module_name: str, output_format: str, depth: int, granular: bool = False
    ) -> list[TextContent]:
        """
        Get all modules that a given module depends on.

        Args:
            module_name: Module name to analyze
            output_format: Output format ('markdown' or 'json')
            depth: Depth for transitive dependencies (1 = direct only, 2 = include dependencies of dependencies)
            granular: Show which specific functions use which dependencies

        Returns:
            TextContent with formatted dependency information
        """
        from cicada.utils import find_similar_names

        # Look up the module in the index
        module_data = self.index["modules"].get(module_name)
        if not module_data:
            # Module not found - create error message
            error_msg = f"Module not found: {module_name}"
            similar = find_similar_names(module_name, list(self.index["modules"].keys()))
            if similar:
                error_msg += "\n\nDid you mean one of these?\n" + "\n".join(
                    f"  - {name}" for name in similar[:5]
                )
            return [TextContent(type="text", text=error_msg)]

        # Get dependencies from the index
        dependencies = module_data.get("dependencies", {})
        direct_modules = dependencies.get("modules", [])

        # Collect granular dependency information if requested
        granular_info: dict[str, list[dict[str, Any]]] = {}
        if granular:
            # Build a mapping of dependency_module -> [functions that use it]
            for func in module_data.get("functions", []):
                func_deps = func.get("dependencies", [])
                for dep in func_deps:
                    dep_module = dep.get("module", "")
                    if dep_module in direct_modules:
                        if dep_module not in granular_info:
                            granular_info[dep_module] = []
                        granular_info[dep_module].append(
                            {
                                "function": func.get("name"),
                                "arity": func.get("arity"),
                                "line": func.get("line"),
                                "calls": f"{dep.get('function')}/{dep.get('arity')}",
                                "call_line": dep.get("line"),
                            }
                        )

        # If depth > 1, collect transitive dependencies
        all_modules = set(direct_modules)
        if depth > 1:
            visited = {module_name}  # Avoid circular dependencies
            to_visit = list(direct_modules)

            for _ in range(depth - 1):
                next_level = []
                for dep_module in to_visit:
                    if dep_module in visited:
                        continue
                    visited.add(dep_module)

                    dep_data = self.index["modules"].get(dep_module)
                    if dep_data:
                        dep_dependencies = dep_data.get("dependencies", {})
                        dep_modules = dep_dependencies.get("modules", [])
                        all_modules.update(dep_modules)
                        next_level.extend(dep_modules)

                to_visit = next_level

        # Format output
        if output_format == "json":
            result = {
                "module": module_name,
                "dependencies": {
                    "direct": sorted(direct_modules),
                    "all": sorted(all_modules) if depth > 1 else sorted(direct_modules),
                    "depth": depth,
                },
            }
            if granular:
                result["granular"] = granular_info  # type: ignore
            output = json.dumps(result, indent=2)
        else:
            # Markdown format
            lines = [f"# Dependencies for {module_name}\n"]

            if direct_modules:
                lines.append(f"## Direct Dependencies ({len(direct_modules)})\n")
                for dep in sorted(direct_modules):
                    lines.append(f"- {dep}")
                    # Add granular information if available
                    if granular and dep in granular_info:
                        uses = granular_info[dep]
                        lines.append(f"  Used by {len(uses)} function(s):")
                        for use in uses[:3]:  # Limit to 3 examples
                            lines.append(
                                f"    • {use['function']}/{use['arity']} :{use['line']} → calls {use['calls']} :{use['call_line']}"
                            )
                        if len(uses) > 3:
                            lines.append(f"    ... and {len(uses) - 3} more")
                lines.append("")

            if depth > 1 and len(all_modules) > len(direct_modules):
                transitive = sorted(all_modules - set(direct_modules))
                lines.append(f"## Transitive Dependencies ({len(transitive)})\n")
                for dep in transitive:
                    lines.append(f"- {dep}")
                lines.append("")

            if not direct_modules:
                lines.append("*No dependencies found*")

            output = "\n".join(lines)

        return [TextContent(type="text", text=output)]

    async def get_function_dependencies(
        self,
        module_name: str,
        function_name: str,
        arity: int,
        output_format: str,
        include_context: bool,
    ) -> list[TextContent]:
        """
        Get all functions that a given function calls.

        Args:
            module_name: Module name containing the function
            function_name: Function name to analyze
            arity: Function arity
            output_format: Output format ('markdown' or 'json')
            include_context: Whether to include code context

        Returns:
            TextContent with formatted dependency information
        """
        # Look up the module in the index (no suggestions for function lookup)
        module_data = self.index["modules"].get(module_name)
        if not module_data:
            error_msg = f"Module not found: {module_name}"
            return [TextContent(type="text", text=error_msg)]

        # Find the function
        functions = module_data.get("functions", [])
        target_func = None
        for func in functions:
            if func["name"] == function_name and func["arity"] == arity:
                target_func = func
                break

        if not target_func:
            error_msg = (
                f"Function not found: {module_name}.{function_name}/{arity}\n\n"
                f"Available functions in {module_name}:\n"
            )
            available = [f"  - {f['name']}/{f['arity']}" for f in functions[:10]]
            error_msg += "\n".join(available)
            return [TextContent(type="text", text=error_msg)]

        # Get function dependencies
        dependencies = target_func.get("dependencies", [])

        # If include_context is True, fetch the source code
        context_lines = {}
        if include_context and dependencies:
            # Read the source file
            repo_path = self.config.get("repository", {}).get("path", ".")
            file_path = Path(repo_path) / module_data["file"]
            try:
                with open(file_path) as f:
                    source_lines = f.readlines()
                    # Get context for each dependency call
                    for dep in dependencies:
                        line_num = dep["line"]
                        if 1 <= line_num <= len(source_lines):
                            # Get 3 lines of context (before, current, after)
                            start = max(0, line_num - 2)
                            end = min(len(source_lines), line_num + 1)
                            context = "".join(source_lines[start:end])
                            context_lines[line_num] = context.rstrip()
            except OSError:
                pass  # If we can't read the file, just skip context

        # Format output
        if output_format == "json":
            result = {
                "module": module_name,
                "function": f"{function_name}/{arity}",
                "dependencies": dependencies,
            }
            output = json.dumps(result, indent=2)
        else:
            # Markdown format
            lines = [f"# Dependencies for {module_name}.{function_name}/{arity}\n"]

            if dependencies:
                # Group by internal vs external
                internal = [d for d in dependencies if d["module"] == module_name]
                external = [d for d in dependencies if d["module"] != module_name]

                if internal:
                    lines.append(f"## Internal Calls ({len(internal)})\n")
                    for dep in internal:
                        lines.extend(
                            self._format_dependency_with_context(
                                dep, context_lines, include_context, include_module=False
                            )
                        )
                    lines.append("")

                if external:
                    lines.append(f"## External Calls ({len(external)})\n")
                    for dep in external:
                        lines.extend(
                            self._format_dependency_with_context(
                                dep, context_lines, include_context, include_module=True
                            )
                        )
                    lines.append("")
            else:
                lines.append("*No dependencies found*")

            output = "\n".join(lines)

        return [TextContent(type="text", text=output)]
