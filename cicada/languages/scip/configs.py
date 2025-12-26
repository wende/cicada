"""SCIP language configurations.

Each language is defined by a simple config dict instead of a separate class.
"""

from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Callable

# Type for pre-indexing hooks (e.g., dart pub get)
PreIndexHook = Callable[[Path, bool], None]


@dataclass
class SCIPLanguageConfig:
    """Configuration for a SCIP-based language indexer."""

    name: str
    extensions: list[str]
    excluded_dirs: set[str] = field(default_factory=set)
    # Command template: use {output} for output path placeholder
    command: list[str] = field(default_factory=list)
    # Alternative commands to try (e.g., coursier fallback for Java)
    fallback_commands: list[list[str]] = field(default_factory=list)
    # Required executables (first found is used)
    required_executables: list[str] = field(default_factory=list)
    # Error message if executable not found
    install_hint: str = ""
    # Hook to run before indexing (e.g., dart pub get)
    pre_index_hook: PreIndexHook | None = None


def _dart_pre_index_hook(repo_path: Path, verbose: bool) -> None:
    """Run dart pub get if package_config.json doesn't exist."""
    import shutil
    import subprocess

    package_config = repo_path / ".dart_tool" / "package_config.json"
    if package_config.exists():
        return

    dart_cmd = shutil.which("dart")
    if not dart_cmd:
        return

    if verbose:
        print("  Running dart pub get to generate package_config.json...")
    try:
        result = subprocess.run(
            [dart_cmd, "pub", "get"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0 and verbose:
            print(f"  Warning: dart pub get returned {result.returncode}")
    except subprocess.TimeoutExpired:
        if verbose:
            print("  Warning: dart pub get timed out")


# Common excluded directories
_COMMON_EXCLUDED = {".git", "node_modules"}


LANGUAGE_CONFIGS: dict[str, SCIPLanguageConfig] = {
    # Go
    "go": SCIPLanguageConfig(
        name="go",
        extensions=[".go"],
        excluded_dirs=_COMMON_EXCLUDED | {"vendor", "testdata"},
        command=["scip-go", "index", "--output", "index.scip", "./..."],
        required_executables=["scip-go"],
        install_hint="Install via: go install github.com/sourcegraph/scip-go@latest",
    ),
    # Ruby
    "ruby": SCIPLanguageConfig(
        name="ruby",
        extensions=[".rb", ".rake"],
        excluded_dirs=_COMMON_EXCLUDED | {"vendor", "tmp", "log", ".bundle"},
        command=["scip-ruby", "--index-file", "index.scip", "."],
        required_executables=["scip-ruby"],
        install_hint="Install via: gem install scip-ruby",
    ),
    # Dart
    "dart": SCIPLanguageConfig(
        name="dart",
        extensions=[".dart"],
        excluded_dirs=_COMMON_EXCLUDED | {"build", ".dart_tool", ".pub-cache"},
        command=["scip_dart", "./"],
        required_executables=["scip_dart", "dart"],
        install_hint="Install via: dart pub global activate scip",
        pre_index_hook=_dart_pre_index_hook,
    ),
    # Java (via scip-java or coursier)
    "java": SCIPLanguageConfig(
        name="java",
        extensions=[".java"],
        excluded_dirs=_COMMON_EXCLUDED | {"build", "target", ".gradle", "out", "bin", ".idea"},
        command=["scip-java", "index", "--output", "index.scip"],
        fallback_commands=[
            [
                "coursier",
                "launch",
                "com.sourcegraph:scip-java_2.13:0.11.2",
                "--",
                "index",
                "--output",
                "index.scip",
            ],
            [
                "cs",
                "launch",
                "com.sourcegraph:scip-java_2.13:0.11.2",
                "--",
                "index",
                "--output",
                "index.scip",
            ],
        ],
        required_executables=["scip-java", "coursier", "cs"],
        install_hint="Install via: brew install coursier/formulas/coursier",
    ),
    # Scala (same tool as Java)
    "scala": SCIPLanguageConfig(
        name="scala",
        extensions=[".scala", ".sc"],
        excluded_dirs=_COMMON_EXCLUDED
        | {
            "build",
            "target",
            ".gradle",
            "out",
            "bin",
            ".idea",
            ".bloop",
            ".metals",
            "project/target",
        },
        command=["scip-java", "index", "--output", "index.scip"],
        fallback_commands=[
            [
                "coursier",
                "launch",
                "com.sourcegraph:scip-java_2.13:0.11.2",
                "--",
                "index",
                "--output",
                "index.scip",
            ],
            [
                "cs",
                "launch",
                "com.sourcegraph:scip-java_2.13:0.11.2",
                "--",
                "index",
                "--output",
                "index.scip",
            ],
        ],
        required_executables=["scip-java", "coursier", "cs"],
        install_hint="Install via: brew install coursier/formulas/coursier",
    ),
    # C (via scip-clang)
    "c": SCIPLanguageConfig(
        name="c",
        extensions=[".c", ".h"],
        excluded_dirs=_COMMON_EXCLUDED
        | {"build", "vendor", "third_party", "cmake-build-debug", "cmake-build-release"},
        command=["scip-clang", "--index-output-path", "index.scip"],
        required_executables=["scip-clang"],
        install_hint="Install via: https://github.com/nicklockwood/scip-clang",
    ),
    # C++
    "cpp": SCIPLanguageConfig(
        name="cpp",
        extensions=[".cpp", ".cc", ".cxx", ".hpp", ".hxx", ".h"],
        excluded_dirs=_COMMON_EXCLUDED
        | {"build", "vendor", "third_party", "cmake-build-debug", "cmake-build-release"},
        command=["scip-clang", "--index-output-path", "index.scip"],
        required_executables=["scip-clang"],
        install_hint="Install via: https://github.com/nicklockwood/scip-clang",
    ),
    # C#
    "csharp": SCIPLanguageConfig(
        name="csharp",
        extensions=[".cs"],
        excluded_dirs=_COMMON_EXCLUDED | {"bin", "obj", "packages", ".vs"},
        command=["scip-dotnet", "index", "--output", "index.scip"],
        required_executables=["scip-dotnet"],
        install_hint="Install via: dotnet tool install -g scip-dotnet",
    ),
    # Visual Basic
    "vb": SCIPLanguageConfig(
        name="vb",
        extensions=[".vb"],
        excluded_dirs=_COMMON_EXCLUDED | {"bin", "obj", "packages", ".vs"},
        command=["scip-dotnet", "index", "--output", "index.scip"],
        required_executables=["scip-dotnet"],
        install_hint="Install via: dotnet tool install -g scip-dotnet",
    ),
}


def get_config(language: str) -> SCIPLanguageConfig | None:
    """Get configuration for a language."""
    return LANGUAGE_CONFIGS.get(language)


def get_all_languages() -> list[str]:
    """Get list of all supported languages."""
    return list(LANGUAGE_CONFIGS.keys())
