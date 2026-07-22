"""
Language-specific configuration model.

Defines configuration settings that are specific to each programming language.
"""

from dataclasses import dataclass, field
from typing import Any

# Shared excluded directories for Node.js/JS/TS projects
_NODE_EXCLUDED_DIRS = [
    "node_modules",
    ".git",
    "dist",
    "build",
    "coverage",
    ".next",
    ".nuxt",
    "out",
    ".cache",
]


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
            excluded_dirs=list(_NODE_EXCLUDED_DIRS),
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
            excluded_dirs=list(_NODE_EXCLUDED_DIRS),
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

    @staticmethod
    def default_gleam() -> "LanguageConfig":
        """Create default Gleam configuration."""
        return LanguageConfig(
            language="gleam",
            file_extensions=[".gleam"],
            excluded_dirs=["_build", "build", "deps", ".git", "node_modules"],
            tree_sitter_grammar="tree-sitter-gleam",
            comment_syntax={"line": "//"},
        )

    @staticmethod
    def default_go() -> "LanguageConfig":
        """Create default Go configuration."""
        return LanguageConfig(
            language="go",
            file_extensions=[".go"],
            excluded_dirs=[
                "vendor",
                ".git",
                "node_modules",
                "testdata",
            ],
            comment_syntax={
                "line": "//",
                "block_start": "/*",
                "block_end": "*/",
            },
        )

    @staticmethod
    def default_java() -> "LanguageConfig":
        """Create default Java configuration."""
        return LanguageConfig(
            language="java",
            file_extensions=[".java"],
            excluded_dirs=[
                "build",
                "target",
                ".gradle",
                ".git",
                "node_modules",
                "out",
                "bin",
            ],
            comment_syntax={
                "line": "//",
                "block_start": "/*",
                "block_end": "*/",
            },
        )

    @staticmethod
    def default_scala() -> "LanguageConfig":
        """Create default Scala configuration."""
        return LanguageConfig(
            language="scala",
            file_extensions=[".scala", ".sc"],
            excluded_dirs=[
                "target",
                ".bloop",
                ".metals",
                ".git",
                "node_modules",
                "project/target",
            ],
            comment_syntax={
                "line": "//",
                "block_start": "/*",
                "block_end": "*/",
            },
        )

    @staticmethod
    def default_c() -> "LanguageConfig":
        """Create default C configuration."""
        return LanguageConfig(
            language="c",
            file_extensions=[".c", ".h"],
            excluded_dirs=[
                "build",
                ".git",
                "node_modules",
                "vendor",
                "third_party",
            ],
            comment_syntax={
                "line": "//",
                "block_start": "/*",
                "block_end": "*/",
            },
        )

    @staticmethod
    def default_cpp() -> "LanguageConfig":
        """Create default C++ configuration."""
        return LanguageConfig(
            language="cpp",
            file_extensions=[".cpp", ".cc", ".cxx", ".hpp", ".hxx", ".h"],
            excluded_dirs=[
                "build",
                ".git",
                "node_modules",
                "vendor",
                "third_party",
                "cmake-build-debug",
                "cmake-build-release",
            ],
            comment_syntax={
                "line": "//",
                "block_start": "/*",
                "block_end": "*/",
            },
        )

    @staticmethod
    def default_ruby() -> "LanguageConfig":
        """Create default Ruby configuration."""
        return LanguageConfig(
            language="ruby",
            file_extensions=[".rb", ".rake"],
            excluded_dirs=[
                "vendor",
                ".git",
                "node_modules",
                "tmp",
                "log",
                ".bundle",
            ],
            comment_syntax={"line": "#"},
        )

    @staticmethod
    def default_csharp() -> "LanguageConfig":
        """Create default C# configuration."""
        return LanguageConfig(
            language="csharp",
            file_extensions=[".cs"],
            excluded_dirs=[
                "bin",
                "obj",
                ".git",
                "node_modules",
                "packages",
                ".vs",
            ],
            comment_syntax={
                "line": "//",
                "block_start": "/*",
                "block_end": "*/",
            },
        )

    @staticmethod
    def default_vb() -> "LanguageConfig":
        """Create default Visual Basic configuration."""
        return LanguageConfig(
            language="vb",
            file_extensions=[".vb"],
            excluded_dirs=[
                "bin",
                "obj",
                ".git",
                "node_modules",
                "packages",
                ".vs",
            ],
            comment_syntax={"line": "'"},
        )

    @staticmethod
    def default_dart() -> "LanguageConfig":
        """Create default Dart configuration."""
        return LanguageConfig(
            language="dart",
            file_extensions=[".dart"],
            excluded_dirs=[
                "build",
                ".dart_tool",
                ".git",
                "node_modules",
                ".pub-cache",
            ],
            comment_syntax={
                "line": "//",
                "block_start": "/*",
                "block_end": "*/",
            },
        )
