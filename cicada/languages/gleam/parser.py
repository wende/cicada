"""Gleam parser using tree-sitter."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

from tree_sitter_language_pack import get_language, get_parser

from cicada.parsing.base_parser import BaseParser
from cicada.parsing.language_config import LanguageConfig


class GleamParser(BaseParser):
    """Parse Gleam source files into Cicada's module/function index shape."""

    def __init__(self):
        self.parser = get_parser("gleam")
        self.config = LanguageConfig.default_gleam()

    def get_language_name(self) -> str:
        return "gleam"

    def get_tree_sitter_language(self) -> Any:
        return get_language("gleam")

    def get_file_extensions(self) -> list[str]:
        return self.config.file_extensions

    def parse_file(
        self, file_path: str | Path, repo_path: str | Path | None = None
    ) -> list[dict] | None:
        path = Path(file_path)
        source = path.read_bytes()
        tree = self.parser.parse(source)
        root = self._value(tree, "root_node")

        module_name = self._module_name(path, Path(repo_path) if repo_path else None)
        module_data: dict[str, Any] = {
            "module": module_name,
            "file": self._file_path(path, Path(repo_path) if repo_path else None),
            "line": 1,
            "functions": self._extract_functions(root, source),
        }

        module_doc = self._extract_module_doc(root, source)
        if module_doc:
            module_data["doc"] = module_doc

        return [module_data]

    def _module_name(self, file_path: Path, repo_path: Path | None) -> str:
        if repo_path:
            try:
                relative = file_path.relative_to(repo_path)
                parts = relative.with_suffix("").parts
                if parts and parts[0] in {"src", "test"}:
                    parts = parts[1:]
                return "/".join(parts)
            except ValueError:
                pass

        return file_path.with_suffix("").name

    def _file_path(self, file_path: Path, repo_path: Path | None) -> str:
        if repo_path:
            try:
                return file_path.relative_to(repo_path).as_posix()
            except ValueError:
                pass

        return str(file_path)

    def _extract_functions(self, root, source: bytes) -> list[dict[str, Any]]:
        functions: list[dict[str, Any]] = []
        pending_doc: str | None = None

        for child in self._children(root):
            node_type = self._node_type(child)
            if node_type == "statement_comment":
                pending_doc = self._append_doc(pending_doc, self._comment_content(child, source))
                continue

            if node_type == "function":
                function = self._extract_function(child, source)
                if function:
                    if pending_doc:
                        function["doc"] = pending_doc
                    functions.append(function)
                pending_doc = None
                continue

            if node_type not in {"module_comment"}:
                pending_doc = None

        return functions

    def _extract_function(self, node, source: bytes) -> dict[str, Any] | None:
        name: str | None = None
        args: list[str] = []
        is_public = False

        for child in self._children(node):
            node_type = self._node_type(child)
            if node_type == "visibility_modifier" and self._text(child, source) == "pub":
                is_public = True
            elif node_type == "identifier" and name is None:
                name = self._text(child, source)
            elif node_type == "function_parameters":
                args = self._extract_parameters(child, source)

        if not name:
            return None

        return {
            "name": name,
            "arity": len(args),
            "line": self._start_line(node),
            "type": "def" if is_public else "defp",
            "args": args,
        }

    def _extract_parameters(self, node, source: bytes) -> list[str]:
        args = []
        for child in self._children(node):
            if self._node_type(child) != "function_parameter":
                continue
            identifier = self._first_child_of_type(child, "identifier")
            args.append(self._text(identifier, source) if identifier else self._text(child, source))
        return args

    def _extract_module_doc(self, root, source: bytes) -> str | None:
        doc_lines = []
        for child in self._children(root):
            if self._node_type(child) != "module_comment":
                break
            doc_lines.append(self._comment_content(child, source))
        return self._join_doc(doc_lines)

    def _comment_content(self, node, source: bytes) -> str:
        content_parts = []
        for child in self._children(node):
            if self._node_type(child) == "doc_comment_content":
                content_parts.append(self._text(child, source).strip())
        return "\n".join(part for part in content_parts if part)

    def _append_doc(self, current: str | None, line: str) -> str | None:
        if not line:
            return current
        if not current:
            return line
        return f"{current}\n{line}"

    def _join_doc(self, lines: list[str]) -> str | None:
        doc = "\n".join(line for line in lines if line).strip()
        return doc or None

    def _first_child_of_type(self, node, wanted_type: str):
        for child in self._children(node):
            if self._node_type(child) == wanted_type:
                return child
        return None

    def _children(self, node) -> list[Any]:
        children = getattr(node, "children", None)
        if children is not None:
            return list(cast(Sequence[Any], children))

        child_count = int(self._value(node, "child_count"))
        return [node.child(i) for i in range(child_count)]

    def _node_type(self, node) -> str:
        node_type = getattr(node, "type", None)
        if isinstance(node_type, str):
            return node_type
        return str(self._value(node, "kind"))

    def _text(self, node, source: bytes) -> str:
        start = int(self._value(node, "start_byte"))
        end = int(self._value(node, "end_byte"))
        return source[start:end].decode("utf-8")

    def _start_line(self, node) -> int:
        point = self._value(node, "start_point", fallback_name="start_position")
        if hasattr(point, "row"):
            return int(point.row) + 1
        return int(cast(Sequence[Any], point)[0]) + 1

    def _value(self, obj, name: str, fallback_name: str | None = None) -> Any:
        if hasattr(obj, name):
            value = getattr(obj, name)
        elif fallback_name and hasattr(obj, fallback_name):
            value = getattr(obj, fallback_name)
        else:
            raise AttributeError(name)
        return value() if callable(value) else value
