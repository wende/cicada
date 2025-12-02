"""Parse Rust `use` statements to map visible aliases to fully-qualified paths."""

from __future__ import annotations

import re
from pathlib import Path

_USE_RE = re.compile(r"^(?P<prefix>(?:pub\s+)?use)\s+(?P<body>.+)$")


class RustAliasExtractor:
    """Extract import aliases from Rust source files.

    The extractor keeps the interface similar to the Python equivalent so we can reuse
    the same converter hooks. It intentionally handles only the subset required for
    indexing (top-level `use` statements with optional aliases and grouped braces).
    """

    def extract_aliases(self, file_path: Path | str) -> dict[str, str]:
        path = Path(file_path)
        if not path.exists():
            return {}

        statements = self._collect_use_statements(path.read_text())
        aliases: dict[str, str] = {}
        for stmt in statements:
            aliases.update(self._parse_use_statement(stmt))
        return aliases

    def _collect_use_statements(self, contents: str) -> list[str]:
        statements: list[str] = []
        buffer = ""
        for raw_line in contents.splitlines():
            line = raw_line.split("//", 1)[0].strip()
            if not line:
                continue
            buffer += line + " "
            if ";" in line:
                parts = buffer.split(";")
                for part in parts[:-1]:
                    part = part.strip()
                    if part:
                        statements.append(part)
                buffer = parts[-1].strip()
        return statements

    def _parse_use_statement(self, statement: str) -> dict[str, str]:
        match = _USE_RE.match(statement)
        if not match:
            return {}

        body = match.group("body").strip()

        # Remove trailing braces/semicolons if any remain
        body = body.rstrip(";")

        if "{" in body:
            prefix, rest = body.split("{", 1)
            prefix = prefix.strip()
            if prefix.endswith("::"):
                prefix = prefix[:-2]
            rest = rest.rsplit("}", 1)[0]
            items = [item.strip() for item in rest.split(",") if item.strip()]
            aliases: dict[str, str] = {}
            for item in items:
                aliases.update(self._parse_item(prefix, item))
            return aliases

        return self._parse_item(None, body)

    def _parse_item(self, prefix: str | None, item: str) -> dict[str, str]:
        if not item:
            return {}
        target = item
        alias = None

        if " as " in item:
            target, alias = [part.strip() for part in item.split(" as ", 1)]

        full_target = target
        if prefix:
            if target in {"self"}:
                full_target = prefix
            elif target.startswith("::"):
                full_target = target.lstrip(":")
            else:
                full_target = f"{prefix}::{target}"

        if alias is None:
            alias = self._default_alias_from_target(target)

        return {alias: full_target}

    def _default_alias_from_target(self, target: str) -> str:
        # Strip trailing generics or lifetimes, which aren't expected in use statements
        cleaned = target.split("::")[-1]
        cleaned = cleaned.replace(" ", "")
        return cleaned
