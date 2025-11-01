"""
Universal index schema for multi-language support.

Defines the standard data structures that all language implementations must produce.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FunctionData:
    """
    Universal function/method data structure.

    All languages must map their function definitions to this structure.
    """

    name: str  # Function name
    arity: int  # Number of parameters
    args: list[str]  # Parameter names
    type: str  # Function type: 'public', 'private', 'def', 'defp', 'method', etc.
    line: int  # Line number where function is defined
    signature: str  # Full function signature
    doc: str | None = None  # Documentation string
    spec: dict | None = None  # Type specification (language-specific format)
    keywords: list[str] | None = None  # Extracted keywords for search
    language_specific: dict[str, Any] = field(default_factory=dict)  # Extra language data

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "arity": self.arity,
            "args": self.args,
            "type": self.type,
            "line": self.line,
            "signature": self.signature,
            "doc": self.doc,
            "spec": self.spec,
            "keywords": self.keywords,
            **self.language_specific,  # Merge language-specific fields at top level
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FunctionData":
        """Create from dictionary."""
        # Extract known fields
        known_fields = {
            "name",
            "arity",
            "args",
            "type",
            "line",
            "signature",
            "doc",
            "spec",
            "keywords",
        }
        language_specific = {k: v for k, v in data.items() if k not in known_fields}

        return cls(
            name=data["name"],
            arity=data["arity"],
            args=data["args"],
            type=data["type"],
            line=data["line"],
            signature=data["signature"],
            doc=data.get("doc"),
            spec=data.get("spec"),
            keywords=data.get("keywords"),
            language_specific=language_specific,
        )


@dataclass
class ModuleData:
    """
    Universal module/class data structure.

    All languages must map their modules/classes to this structure.
    """

    name: str  # Module/class name
    file: str  # Relative file path
    line: int  # Line number where module/class is defined
    doc: str | None = None  # Module/class documentation
    functions: list[dict] = field(default_factory=list)  # List of FunctionData dicts
    dependencies: list[dict] = field(default_factory=list)  # Imports/requires
    calls: list[dict] = field(default_factory=list)  # Function calls
    keywords: list[str] | None = None  # Extracted keywords for search
    language_specific: dict[str, Any] = field(default_factory=dict)  # Language-specific data

    # Computed fields (optional, can be calculated from functions)
    total_functions: int | None = None
    public_functions: int | None = None
    private_functions: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {
            "file": self.file,
            "line": self.line,
            "functions": self.functions,
            "calls": self.calls,
        }

        # Add optional fields if present
        if self.doc:
            result["moduledoc"] = self.doc  # Keep 'moduledoc' for backward compat
        if self.keywords:
            result["keywords"] = self.keywords
        if self.dependencies:
            result["dependencies"] = self.dependencies

        # Add computed function counts if available
        if self.total_functions is not None:
            result["total_functions"] = self.total_functions
        if self.public_functions is not None:
            result["public_functions"] = self.public_functions
        if self.private_functions is not None:
            result["private_functions"] = self.private_functions

        # Merge language-specific fields
        result.update(self.language_specific)

        return result

    @classmethod
    def from_dict(cls, name: str, data: dict) -> "ModuleData":
        """Create from dictionary."""
        # Extract known fields
        known_fields = {
            "file",
            "line",
            "functions",
            "dependencies",
            "calls",
            "keywords",
            "moduledoc",
            "doc",
            "total_functions",
            "public_functions",
            "private_functions",
        }
        language_specific = {k: v for k, v in data.items() if k not in known_fields}

        return cls(
            name=name,
            file=data["file"],
            line=data["line"],
            doc=data.get("moduledoc") or data.get("doc"),
            functions=data.get("functions", []),
            dependencies=data.get("dependencies", []),
            calls=data.get("calls", []),
            keywords=data.get("keywords"),
            language_specific=language_specific,
            total_functions=data.get("total_functions"),
            public_functions=data.get("public_functions"),
            private_functions=data.get("private_functions"),
        )


@dataclass
class IndexMetadata:
    """Metadata about the index."""

    indexed_at: str  # ISO format timestamp
    total_modules: int
    total_functions: int
    repo_path: str
    language: str = "elixir"  # Language identifier
    version: str = "2.0"  # Schema version

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "indexed_at": self.indexed_at,
            "total_modules": self.total_modules,
            "total_functions": self.total_functions,
            "repo_path": self.repo_path,
            "language": self.language,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IndexMetadata":
        """Create from dictionary."""
        return cls(
            indexed_at=data["indexed_at"],
            total_modules=data["total_modules"],
            total_functions=data["total_functions"],
            repo_path=data["repo_path"],
            language=data.get("language", "elixir"),  # Default for backward compat
            version=data.get("version", "1.0"),  # Default for old indexes
        )


@dataclass
class UniversalIndexSchema:
    """
    Universal index structure for all programming languages.

    This is the top-level schema that all indexers must produce.
    """

    modules: dict[str, dict]  # module_name -> ModuleData dict
    metadata: dict  # IndexMetadata dict
    language: str = "elixir"  # Language identifier (also in metadata for redundancy)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "modules": self.modules,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UniversalIndexSchema":
        """Create from dictionary."""
        metadata = data.get("metadata", {})
        language = metadata.get("language", "elixir")

        return cls(
            modules=data.get("modules", {}),
            metadata=metadata,
            language=language,
        )

    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate the index structure.

        Returns:
            tuple[bool, list[str]]: (is_valid, list of error messages)
        """
        errors = []

        # Check required top-level fields
        if not isinstance(self.modules, dict):
            errors.append("'modules' must be a dictionary")
        if not isinstance(self.metadata, dict):
            errors.append("'metadata' must be a dictionary")

        # Validate metadata
        required_metadata = [
            "indexed_at",
            "total_modules",
            "total_functions",
            "repo_path",
        ]
        for field_name in required_metadata:
            if field_name not in self.metadata:
                errors.append(f"metadata missing required field: '{field_name}'")

        # Validate each module
        for module_name, module_data in self.modules.items():
            if not isinstance(module_data, dict):
                errors.append(f"Module '{module_name}' data must be a dictionary")
                continue

            # Check required module fields
            required_module_fields = ["file", "line", "functions"]
            for field_name in required_module_fields:
                if field_name not in module_data:
                    errors.append(f"Module '{module_name}' missing required field: '{field_name}'")

            # Validate functions list
            if "functions" in module_data and not isinstance(module_data["functions"], list):
                errors.append(f"Module '{module_name}' functions must be a list")

        return (len(errors) == 0, errors)
