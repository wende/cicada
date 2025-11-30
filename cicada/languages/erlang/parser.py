"""Minimal Erlang parser using tree-sitter."""

from pathlib import Path
from typing import Any

from tree_sitter_language_pack import get_language, get_parser

from cicada.languages.erlang.extractors.doc import (
    extract_docs_from_comments,
    match_docs_to_declarations,
)
from cicada.parsing.base_parser import BaseParser


class ErlangParser(BaseParser):
    def __init__(self):
        self.parser = get_parser("erlang")

    def get_language_name(self) -> str:
        return "erlang"

    def get_tree_sitter_language(self) -> Any:
        return get_language("erlang")

    def get_file_extensions(self) -> list[str]:
        return [".erl", ".hrl"]

    def parse_file(self, file_path: str | Path) -> list[dict] | None:
        with open(file_path, "rb") as f:
            source = f.read()

        tree = self.parser.parse(source)
        return self._extract_modules(tree.root_node, source, str(file_path))

    def _extract_modules(self, root, source: bytes, file_path: str) -> list[dict]:
        modules = []
        module_name = None
        module_line = 1
        exports = set()
        functions = []

        for child in root.children:
            if child.type == "module_attribute":
                # -module(name).
                module_name = self._extract_module_name(child, source)
                module_line = child.start_point[0] + 1
            elif child.type == "export_attribute":
                # -export([...]).
                exports.update(self._extract_exports(child, source))
            elif child.type == "fun_decl":
                # Function declaration contains function_clause(s)
                func = self._extract_function_from_decl(child, source, exports)
                if func:
                    functions.append(func)

        if module_name:
            module_data = {
                "module": module_name,
                "file": file_path,
                "line": module_line,
                "functions": functions,
            }

            # Extract and match EDoc comments
            docs = extract_docs_from_comments(root, source)
            match_docs_to_declarations(docs, [module_data], functions)

            modules.append(module_data)

        return modules

    def _extract_module_name(self, node, source: bytes) -> str | None:
        # Find atom child which is the module name
        for child in node.children:
            if child.type == "atom":
                return child.text.decode("utf-8")
        return None

    def _extract_exports(self, node, source: bytes) -> set:
        # Extract function/arity from export list
        exports = set()
        # Walk to find fa (function/arity) nodes
        self._find_exports_recursive(node, source, exports)
        return exports

    def _find_exports_recursive(self, node, source: bytes, exports: set):
        if node.type == "fa":
            # fa contains atom (name) and arity node (which contains integer)
            name = None
            arity = None
            for child in node.children:
                if child.type == "atom":
                    name = child.text.decode("utf-8")
                elif child.type == "arity":
                    # arity node contains the integer
                    for subchild in child.children:
                        if subchild.type == "integer":
                            arity = int(subchild.text.decode("utf-8"))
            if name and arity is not None:
                exports.add(f"{name}/{arity}")
        for child in node.children:
            self._find_exports_recursive(child, source, exports)

    def _extract_function_from_decl(self, node, source: bytes, exports: set) -> dict | None:
        # fun_decl contains function_clause children.
        # We only extract the first clause - this is safe because:
        # 1. All clauses of a function share the same name and arity by definition
        # 2. For indexing purposes (finding functions, line numbers, visibility), the
        #    first clause provides all needed metadata
        # 3. The line number of the first clause is the canonical location for navigation
        # Full multi-clause handling (e.g., clause count metadata) is documented as
        # future work in docs/prd-erlang.md.
        for child in node.children:
            if child.type == "function_clause":
                return self._extract_function(child, source, exports)
        return None

    def _extract_function(self, node, source: bytes, exports: set) -> dict | None:
        # Find function name and arity from function_clause
        name = None
        arity = 0
        line = node.start_point[0] + 1

        for child in node.children:
            if child.type == "atom" and name is None:
                name = child.text.decode("utf-8")
            elif child.type == "expr_args":
                # Count named children to correctly calculate arity,
                # handles pattern matching in arguments (tuples, records, literals)
                arity = sum(1 for c in child.children if c.is_named)

        if name:
            func_key = f"{name}/{arity}"
            return {
                "name": name,
                "arity": arity,
                "line": line,
                "type": "def" if func_key in exports else "defp",  # Elixir-style for now
            }
        return None
