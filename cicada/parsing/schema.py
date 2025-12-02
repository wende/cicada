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
    type: str  # Function type (language-specific: 'def', 'defp', 'method', etc.)
    visibility: str  # Normalized visibility: 'public' or 'private'
    line: int  # Line number where function is defined
    signature: str  # Full function signature
    doc: str | None = None  # Documentation string
    spec: dict | None = None  # Type specification (language-specific format)
    keywords: dict[str, float] | None = None  # Keyword -> relevance score mapping for search
    language_specific: dict[str, Any] = field(default_factory=dict)  # Extra language data

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "arity": self.arity,
            "args": self.args,
            "type": self.type,
            "visibility": self.visibility,
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
            "visibility",
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
            visibility=data.get("visibility", "public"),  # Default for backward compat
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
    dependencies: list[dict] | dict = field(
        default_factory=list
    )  # Imports/requires (list for old format, dict with 'modules' and 'has_dynamic_calls' for new format)
    calls: list[dict] = field(default_factory=list)  # Function calls
    keywords: dict[str, float] | None = None  # Keyword -> relevance score mapping for search
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
    reverse_calls: dict[str, list[dict]] | None = None  # callee -> list of callers

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "modules": self.modules,
            "metadata": self.metadata,
        }
        if self.reverse_calls:
            result["reverse_calls"] = self.reverse_calls
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "UniversalIndexSchema":
        """Create from dictionary."""
        metadata = data.get("metadata", {})
        language = metadata.get("language", "elixir")

        return cls(
            modules=data.get("modules", {}),
            metadata=metadata,
            language=language,
            reverse_calls=data.get("reverse_calls"),
        )

    def validate(self, strict: bool = True) -> tuple[bool, list[str]]:
        """
        Validate the index structure comprehensively.

        Args:
            strict: If True, validate all field types and constraints.
                   If False, only validate required fields exist.

        Returns:
            tuple[bool, list[str]]: (is_valid, list of error messages)
        """
        errors = []

        # Check required top-level fields
        if not isinstance(self.modules, dict):
            errors.append("'modules' must be a dictionary")
            return (False, errors)  # Fatal error, can't continue

        if not isinstance(self.metadata, dict):
            errors.append("'metadata' must be a dictionary")
            return (False, errors)  # Fatal error, can't continue

        # Validate metadata
        errors.extend(self._validate_metadata(self.metadata, strict))

        # Validate each module
        for module_name, module_data in self.modules.items():
            if not isinstance(module_data, dict):
                errors.append(f"Module '{module_name}' data must be a dictionary")
                continue

            module_errors = self._validate_module(module_name, module_data, strict)
            errors.extend(module_errors)

        return (len(errors) == 0, errors)

    def _validate_metadata(self, metadata: dict, strict: bool) -> list[str]:
        """Validate metadata section."""
        errors = []

        # Required fields
        required_fields = {
            "indexed_at": str,
            "total_modules": int,
            "total_functions": int,
            "repo_path": str,
        }

        for field_name, expected_type in required_fields.items():
            if field_name not in metadata:
                errors.append(f"metadata missing required field: '{field_name}'")
            elif strict and not isinstance(metadata[field_name], expected_type):
                actual_type = type(metadata[field_name]).__name__
                errors.append(
                    f"metadata.{field_name} must be {expected_type.__name__}, got {actual_type}"
                )

        # Optional but typed fields
        if "language" in metadata and strict and not isinstance(metadata["language"], str):
            errors.append("metadata.language must be a string")

        if "version" in metadata and strict and not isinstance(metadata["version"], str):
            errors.append("metadata.version must be a string")

        # Validate counts are non-negative
        if strict:
            for count_field in ["total_modules", "total_functions"]:
                if (
                    count_field in metadata
                    and isinstance(metadata[count_field], int)
                    and metadata[count_field] < 0
                ):
                    errors.append(f"metadata.{count_field} must be non-negative")

        return errors

    def _validate_module(self, module_name: str, module_data: dict, strict: bool) -> list[str]:
        """Validate a single module entry."""
        errors = []

        # Required module fields
        required_fields = {
            "file": str,
            "line": int,
            "functions": list,
        }

        for field_name, expected_type in required_fields.items():
            if field_name not in module_data:
                errors.append(f"Module '{module_name}' missing required field: '{field_name}'")
            elif strict and not isinstance(module_data[field_name], expected_type):
                actual_type = type(module_data[field_name]).__name__
                errors.append(
                    f"Module '{module_name}'.{field_name} must be {expected_type.__name__}, "
                    f"got {actual_type}"
                )

        # Validate line number
        if (
            strict
            and "line" in module_data
            and isinstance(module_data["line"], int)
            and module_data["line"] <= 0
        ):
            errors.append(f"Module '{module_name}'.line must be positive")

        # Validate optional list fields
        # Note: 'dependencies' can be either list (old format) or dict (new format with 'modules' and 'has_dynamic_calls')
        if "calls" in module_data and strict and not isinstance(module_data["calls"], list):
            errors.append(f"Module '{module_name}'.calls must be a list")

        # Validate dependencies structure (support both old list and new dict format)
        if "dependencies" in module_data and strict:
            deps = module_data["dependencies"]
            if isinstance(deps, dict):
                # New format: dict with 'modules' and 'has_dynamic_calls'
                if "modules" not in deps:
                    errors.append(
                        f"Module '{module_name}'.dependencies dict must have 'modules' key"
                    )
                elif not isinstance(deps["modules"], list):
                    errors.append(f"Module '{module_name}'.dependencies['modules'] must be a list")
                if "has_dynamic_calls" in deps and not isinstance(deps["has_dynamic_calls"], bool):
                    errors.append(
                        f"Module '{module_name}'.dependencies['has_dynamic_calls'] must be a boolean"
                    )
            elif not isinstance(deps, list):
                # Must be either list or dict
                errors.append(f"Module '{module_name}'.dependencies must be a list or dict")

        # Validate each function
        if "functions" in module_data and isinstance(module_data["functions"], list):
            for idx, func in enumerate(module_data["functions"]):
                func_errors = self._validate_function(module_name, idx, func, strict)
                errors.extend(func_errors)

        # Validate calls structure if present
        if "calls" in module_data and isinstance(module_data["calls"], list) and strict:
            for idx, call in enumerate(module_data["calls"]):
                call_errors = self._validate_call(module_name, idx, call)
                errors.extend(call_errors)

        return errors

    def _validate_function(
        self, module_name: str, func_idx: int, func_data: dict, strict: bool
    ) -> list[str]:
        """Validate a single function entry."""
        errors = []

        if not isinstance(func_data, dict):
            errors.append(
                f"Module '{module_name}' function at index {func_idx} must be a dictionary"
            )
            return errors

        # Required function fields
        required_fields = {
            "name": str,
            "arity": int,
            "args": list,
            "type": str,
            "visibility": str,
            "line": int,
            "signature": str,
        }

        for field_name, expected_type in required_fields.items():
            if field_name not in func_data:
                errors.append(
                    f"Module '{module_name}' function at index {func_idx} "
                    f"missing required field: '{field_name}'"
                )
            elif strict and not isinstance(func_data[field_name], expected_type):
                actual_type = type(func_data[field_name]).__name__
                errors.append(
                    f"Module '{module_name}' function at index {func_idx}: "
                    f"{field_name} must be {expected_type.__name__}, got {actual_type}"
                )

        if not strict:
            return errors

        # Strict validation: constraints and value checks
        func_name = func_data.get("name", f"<unnamed at index {func_idx}>")

        # Validate arity matches args length
        if (
            "arity" in func_data
            and "args" in func_data
            and isinstance(func_data["arity"], int)
            and isinstance(func_data["args"], list)
            and func_data["arity"] != len(func_data["args"])
        ):
            errors.append(
                f"Module '{module_name}' function '{func_name}': "
                f"arity ({func_data['arity']}) does not match args length "
                f"({len(func_data['args'])})"
            )

        # Validate arity is non-negative
        if "arity" in func_data and isinstance(func_data["arity"], int) and func_data["arity"] < 0:
            errors.append(
                f"Module '{module_name}' function '{func_name}': arity must be non-negative"
            )

        # Validate line number is positive
        if "line" in func_data and isinstance(func_data["line"], int) and func_data["line"] <= 0:
            errors.append(f"Module '{module_name}' function '{func_name}': line must be positive")

        # Validate args are all strings
        if "args" in func_data and isinstance(func_data["args"], list):
            for arg_idx, arg in enumerate(func_data["args"]):
                if not isinstance(arg, str):
                    errors.append(
                        f"Module '{module_name}' function '{func_name}': "
                        f"arg at index {arg_idx} must be a string, got {type(arg).__name__}"
                    )

        # Validate type is known value (for common types)
        if (
            "type" in func_data
            and isinstance(func_data["type"], str)
            and not func_data["type"].strip()
        ):
            # Don't enforce this strictly, just warn if it's completely empty
            errors.append(f"Module '{module_name}' function '{func_name}': type cannot be empty")

        # Validate optional fields if present
        if (
            "doc" in func_data
            and func_data["doc"] is not None
            and not isinstance(func_data["doc"], str)
        ):
            errors.append(
                f"Module '{module_name}' function '{func_name}': doc must be a string or null"
            )

        if (
            "keywords" in func_data
            and func_data["keywords"] is not None
            and not isinstance(func_data["keywords"], dict)
        ):
            errors.append(
                f"Module '{module_name}' function '{func_name}': "
                f"keywords must be a dict[str, float] or null"
            )

        return errors

    def _validate_call(self, module_name: str, call_idx: int, call_data: dict) -> list[str]:
        """Validate a single call entry."""
        errors = []

        if not isinstance(call_data, dict):
            errors.append(f"Module '{module_name}' call at index {call_idx} must be a dictionary")
            return errors

        # Required call fields
        required_fields = {"function": str, "arity": int, "line": int}

        for field_name, expected_type in required_fields.items():
            if field_name not in call_data:
                errors.append(
                    f"Module '{module_name}' call at index {call_idx} "
                    f"missing required field: '{field_name}'"
                )
            elif not isinstance(call_data[field_name], expected_type):
                actual_type = type(call_data[field_name]).__name__
                errors.append(
                    f"Module '{module_name}' call at index {call_idx}: "
                    f"{field_name} must be {expected_type.__name__}, got {actual_type}"
                )

        # module is optional but should be string or None
        if (
            "module" in call_data
            and call_data["module"] is not None
            and not isinstance(call_data["module"], str)
        ):
            errors.append(
                f"Module '{module_name}' call at index {call_idx}: "
                f"module must be a string or null"
            )

        # Validate constraints
        if "arity" in call_data and isinstance(call_data["arity"], int) and call_data["arity"] < 0:
            errors.append(
                f"Module '{module_name}' call at index {call_idx}: arity must be non-negative"
            )

        if "line" in call_data and isinstance(call_data["line"], int) and call_data["line"] <= 0:
            errors.append(f"Module '{module_name}' call at index {call_idx}: line must be positive")

        return errors
