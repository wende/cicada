"""
Language-specific configuration model.

Defines configuration settings that are specific to each programming language.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LanguageConfig:
    """
    Configuration for a specific programming language.

    Each language defines its own configuration with file extensions,
    excluded directories, and other language-specific settings.
    """

    # Required fields
    language: str  # Language identifier (e.g., 'elixir', 'python')
    file_extensions: list[str]  # Extensions to index (e.g., ['.ex', '.exs'])
    excluded_dirs: list[str]  # Directories to exclude from indexing

    # Optional fields
    tree_sitter_grammar: str | None = None  # tree-sitter grammar package name
    comment_syntax: dict[str, str] = field(
        default_factory=dict
    )  # Comment delimiters {'line': '#', 'block_start': '"""', 'block_end': '"""'}

    # Language-specific parsing options
    parse_options: dict = field(default_factory=dict)  # Extra parsing configuration

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        result: dict[str, Any] = {
            "language": self.language,
            "file_extensions": self.file_extensions,
            "excluded_dirs": self.excluded_dirs,
        }

        if self.tree_sitter_grammar:
            result["tree_sitter_grammar"] = self.tree_sitter_grammar
        if self.comment_syntax:
            result["comment_syntax"] = self.comment_syntax
        if self.parse_options:
            result["parse_options"] = self.parse_options

        return result

    @classmethod
    def from_dict(cls, data: dict) -> "LanguageConfig":
        """Create from dictionary (loaded from YAML)."""
        return cls(
            language=data["language"],
            file_extensions=data["file_extensions"],
            excluded_dirs=data["excluded_dirs"],
            tree_sitter_grammar=data.get("tree_sitter_grammar"),
            comment_syntax=data.get("comment_syntax", {}),
            parse_options=data.get("parse_options", {}),
        )

    @staticmethod
    def default_elixir() -> "LanguageConfig":
        """Create default Elixir configuration."""
        return LanguageConfig(
            language="elixir",
            file_extensions=[".ex", ".exs"],
            excluded_dirs=["deps", "_build", "node_modules", ".git", "assets", "priv"],
            tree_sitter_grammar="tree-sitter-elixir",
            comment_syntax={"line": "#"},
        )

    @staticmethod
    def default_python() -> "LanguageConfig":
        """Create default Python configuration."""
        return LanguageConfig(
            language="python",
            file_extensions=[".py"],
            excluded_dirs=[
                "__pycache__",
                ".venv",
                "venv",
                ".git",
                "node_modules",
                ".pytest_cache",
                ".mypy_cache",
                "dist",
                "build",
                "*.egg-info",
            ],
            tree_sitter_grammar="tree-sitter-python",
            comment_syntax={"line": "#", "block_start": '"""', "block_end": '"""'},
        )

    @staticmethod
    def default_typescript() -> "LanguageConfig":
        """Create default TypeScript configuration."""
        return LanguageConfig(
            language="typescript",
            file_extensions=[".ts", ".tsx"],
            excluded_dirs=[
                "node_modules",
                ".git",
                "dist",
                "build",
                "coverage",
                ".next",
                ".nuxt",
                "out",
                ".cache",
            ],
            tree_sitter_grammar="tree-sitter-typescript",
            comment_syntax={
                "line": "//",
                "block_start": "/*",
                "block_end": "*/",
            },
        )

    @staticmethod
    def default_javascript() -> "LanguageConfig":
        """Create default JavaScript configuration."""
        return LanguageConfig(
            language="javascript",
            file_extensions=[".js", ".jsx", ".mjs", ".cjs"],
            excluded_dirs=[
                "node_modules",
                ".git",
                "dist",
                "build",
                "coverage",
                ".next",
                ".nuxt",
                "out",
                ".cache",
            ],
            tree_sitter_grammar="tree-sitter-javascript",
            comment_syntax={
                "line": "//",
                "block_start": "/*",
                "block_end": "*/",
            },
        )

    @staticmethod
    def default_rust() -> "LanguageConfig":
        """Create default Rust configuration."""
        return LanguageConfig(
            language="rust",
            file_extensions=[".rs"],
            excluded_dirs=[
                "target",
                ".git",
                "vendor",
                "node_modules",
            ],
            tree_sitter_grammar="tree-sitter-rust",
            comment_syntax={
                "line": "//",
                "block_start": "/*",
                "block_end": "*/",
            },
        )

    @staticmethod
    def default_erlang() -> "LanguageConfig":
        """Create default Erlang configuration."""
        return LanguageConfig(
            language="erlang",
            file_extensions=[".erl", ".hrl"],
            excluded_dirs=["_build", "deps", ".git", "node_modules", "ebin"],
            tree_sitter_grammar="tree-sitter-erlang",
            comment_syntax={"line": "%"},
        )
