"""
Comprehensive tests for cicada/parsing/schema.py

Tests cover serialization, deserialization, validation, and edge cases.
Target: 90%+ coverage
"""

import pytest
from cicada.parsing.schema import (
    FunctionData,
    ModuleData,
    IndexMetadata,
    UniversalIndexSchema,
)


# ============================================================================
# SECTION 1: Serialization/Deserialization Tests
# ============================================================================


class TestFunctionDataSerialization:
    """Test FunctionData to_dict/from_dict round-trip."""

    def test_function_data_round_trip_minimal(self):
        """Test round-trip with only required fields."""
        func = FunctionData(
            name="my_function",
            arity=2,
            args=["arg1", "arg2"],
            type="public",
            visibility="public",
            line=10,
            signature="def my_function(arg1, arg2)",
        )

        # Serialize to dict
        func_dict = func.to_dict()

        # Deserialize back
        func_restored = FunctionData.from_dict(func_dict)

        # Verify equality
        assert func_restored.name == func.name
        assert func_restored.arity == func.arity
        assert func_restored.args == func.args
        assert func_restored.type == func.type
        assert func_restored.visibility == func.visibility
        assert func_restored.line == func.line
        assert func_restored.signature == func.signature
        assert func_restored.doc is None
        assert func_restored.spec is None
        assert func_restored.keywords is None

    def test_function_data_round_trip_full(self):
        """Test round-trip with all optional fields."""
        func = FunctionData(
            name="my_function",
            arity=2,
            args=["arg1", "arg2"],
            type="public",
            visibility="public",
            line=10,
            signature="def my_function(arg1, arg2)",
            doc="My documentation",
            spec={"return": "string", "params": ["int", "int"]},
            keywords={"keyword1": 0.9, "keyword2": 0.5},
        )

        func_dict = func.to_dict()
        func_restored = FunctionData.from_dict(func_dict)

        assert func_restored.name == func.name
        assert func_restored.arity == func.arity
        assert func_restored.args == func.args
        assert func_restored.type == func.type
        assert func_restored.line == func.line
        assert func_restored.signature == func.signature
        assert func_restored.doc == func.doc
        assert func_restored.spec == func.spec
        assert func_restored.keywords == func.keywords

    def test_function_data_language_specific_fields(self):
        """Test that language-specific fields are properly merged/extracted."""
        func = FunctionData(
            name="my_function",
            arity=0,
            args=[],
            type="public",
            visibility="public",
            line=10,
            signature="def my_function()",
            language_specific={"custom_field": "custom_value", "another": 123},
        )

        # to_dict should merge language_specific at top level
        func_dict = func.to_dict()
        assert func_dict["custom_field"] == "custom_value"
        assert func_dict["another"] == 123

        # from_dict should extract them back
        func_restored = FunctionData.from_dict(func_dict)
        assert func_restored.language_specific["custom_field"] == "custom_value"
        assert func_restored.language_specific["another"] == 123


class TestModuleDataSerialization:
    """Test ModuleData to_dict/from_dict round-trip."""

    def test_module_data_round_trip_minimal(self):
        """Test round-trip with only required fields."""
        module = ModuleData(
            name="MyModule",
            file="lib/my_module.ex",
            line=1,
        )

        module_dict = module.to_dict()
        module_restored = ModuleData.from_dict("MyModule", module_dict)

        assert module_restored.name == module.name
        assert module_restored.file == module.file
        assert module_restored.line == module.line
        assert module_restored.doc is None
        assert module_restored.functions == []
        assert module_restored.dependencies == []
        assert module_restored.calls == []

    def test_module_data_round_trip_full(self):
        """Test round-trip with all optional fields."""
        module = ModuleData(
            name="MyModule",
            file="lib/my_module.ex",
            line=1,
            doc="Module documentation",
            functions=[{"name": "func1", "arity": 0}],
            dependencies=[{"module": "OtherModule"}],
            calls=[{"function": "other_func", "arity": 1, "line": 10}],
            keywords={"key1": 0.8, "key2": 0.6},
            total_functions=5,
            public_functions=3,
            private_functions=2,
        )

        module_dict = module.to_dict()
        module_restored = ModuleData.from_dict("MyModule", module_dict)

        assert module_restored.name == module.name
        assert module_restored.file == module.file
        assert module_restored.line == module.line
        assert module_restored.doc == module.doc
        assert module_restored.functions == module.functions
        assert module_restored.dependencies == module.dependencies
        assert module_restored.calls == module.calls
        assert module_restored.keywords == module.keywords
        assert module_restored.total_functions == module.total_functions
        assert module_restored.public_functions == module.public_functions
        assert module_restored.private_functions == module.private_functions

    def test_module_data_backward_compatibility_moduledoc(self):
        """Test that 'moduledoc' field is backward compatible with 'doc'."""
        # Serialize with doc
        module = ModuleData(
            name="MyModule",
            file="lib/my_module.ex",
            line=1,
            doc="Module documentation",
        )

        module_dict = module.to_dict()

        # to_dict should use 'moduledoc' for backward compatibility
        assert "moduledoc" in module_dict
        assert module_dict["moduledoc"] == "Module documentation"

        # from_dict should handle both 'moduledoc' and 'doc'
        module_restored = ModuleData.from_dict("MyModule", module_dict)
        assert module_restored.doc == "Module documentation"

        # Test with 'doc' field directly
        module_dict_new = {"file": "lib/test.ex", "line": 1, "doc": "New doc"}
        module_new = ModuleData.from_dict("TestModule", module_dict_new)
        assert module_new.doc == "New doc"

    def test_module_data_language_specific_fields(self):
        """Test that language-specific fields are properly merged/extracted."""
        module = ModuleData(
            name="MyModule",
            file="lib/my_module.ex",
            line=1,
            language_specific={"elixir_specific": "value", "custom_count": 42},
        )

        module_dict = module.to_dict()
        assert module_dict["elixir_specific"] == "value"
        assert module_dict["custom_count"] == 42

        module_restored = ModuleData.from_dict("MyModule", module_dict)
        assert module_restored.language_specific["elixir_specific"] == "value"
        assert module_restored.language_specific["custom_count"] == 42


class TestIndexMetadataSerialization:
    """Test IndexMetadata to_dict/from_dict round-trip."""

    def test_index_metadata_round_trip(self):
        """Test round-trip serialization."""
        metadata = IndexMetadata(
            indexed_at="2024-01-01T00:00:00Z",
            total_modules=10,
            total_functions=50,
            repo_path="/path/to/repo",
            language="elixir",
            version="2.0",
        )

        metadata_dict = metadata.to_dict()
        metadata_restored = IndexMetadata.from_dict(metadata_dict)

        assert metadata_restored.indexed_at == metadata.indexed_at
        assert metadata_restored.total_modules == metadata.total_modules
        assert metadata_restored.total_functions == metadata.total_functions
        assert metadata_restored.repo_path == metadata.repo_path
        assert metadata_restored.language == metadata.language
        assert metadata_restored.version == metadata.version

    def test_index_metadata_defaults(self):
        """Test that defaults are applied for backward compatibility."""
        metadata_dict = {
            "indexed_at": "2024-01-01T00:00:00Z",
            "total_modules": 5,
            "total_functions": 20,
            "repo_path": "/path/to/repo",
        }

        metadata = IndexMetadata.from_dict(metadata_dict)

        # Should default to 'elixir' and '1.0'
        assert metadata.language == "elixir"
        assert metadata.version == "1.0"


class TestUniversalIndexSchemaSerialization:
    """Test UniversalIndexSchema to_dict/from_dict round-trip."""

    def test_universal_index_schema_round_trip(self):
        """Test full schema round-trip."""
        schema = UniversalIndexSchema(
            modules={
                "MyModule": {
                    "file": "lib/my_module.ex",
                    "line": 1,
                    "functions": [],
                    "calls": [],
                }
            },
            metadata={
                "indexed_at": "2024-01-01T00:00:00Z",
                "total_modules": 1,
                "total_functions": 0,
                "repo_path": "/path/to/repo",
                "language": "elixir",
                "version": "2.0",
            },
        )

        schema_dict = schema.to_dict()
        schema_restored = UniversalIndexSchema.from_dict(schema_dict)

        assert schema_restored.modules == schema.modules
        assert schema_restored.metadata == schema.metadata
        assert schema_restored.language == schema.language


# ============================================================================
# SECTION 2: Validation Happy Path Tests
# ============================================================================


class TestValidationHappyPaths:
    """Test validation with valid schemas."""

    def test_validate_valid_schema_minimal(self):
        """Test validation passes for minimal valid schema."""
        schema = UniversalIndexSchema(
            modules={
                "MyModule": {
                    "file": "lib/my_module.ex",
                    "line": 1,
                    "functions": [],
                    "calls": [],
                }
            },
            metadata={
                "indexed_at": "2024-01-01T00:00:00Z",
                "total_modules": 1,
                "total_functions": 0,
                "repo_path": "/path/to/repo",
            },
        )

        is_valid, errors = schema.validate(strict=True)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_valid_schema_full(self):
        """Test validation passes for complete valid schema."""
        schema = UniversalIndexSchema(
            modules={
                "MyModule": {
                    "file": "lib/my_module.ex",
                    "line": 1,
                    "moduledoc": "Module doc",
                    "functions": [
                        {
                            "name": "my_func",
                            "arity": 2,
                            "args": ["x", "y"],
                            "type": "public",
                            "visibility": "public",
                            "line": 5,
                            "signature": "def my_func(x, y)",
                            "doc": "Function doc",
                            "keywords": {"key": 0.9},
                        }
                    ],
                    "calls": [
                        {"function": "other_func", "arity": 1, "line": 10, "module": "OtherModule"}
                    ],
                    "dependencies": [{"module": "OtherModule"}],
                    "keywords": {"module_key": 0.8},
                    "total_functions": 1,
                    "public_functions": 1,
                    "private_functions": 0,
                }
            },
            metadata={
                "indexed_at": "2024-01-01T00:00:00Z",
                "total_modules": 1,
                "total_functions": 1,
                "repo_path": "/path/to/repo",
                "language": "elixir",
                "version": "2.0",
            },
        )

        is_valid, errors = schema.validate(strict=True)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_non_strict_mode(self):
        """Test non-strict validation allows type mismatches."""
        schema = UniversalIndexSchema(
            modules={
                "MyModule": {
                    "file": "lib/my_module.ex",
                    "line": 1,
                    "functions": [],
                    "calls": [],
                }
            },
            metadata={
                "indexed_at": "2024-01-01T00:00:00Z",
                "total_modules": 1,
                "total_functions": 0,
                "repo_path": "/path/to/repo",
            },
        )

        # Non-strict mode should be more lenient
        is_valid, errors = schema.validate(strict=False)

        assert is_valid is True
        assert len(errors) == 0


# ============================================================================
# SECTION 3: Validation Error Path Tests (Priority)
# ============================================================================


class TestValidationErrorsPriority:
    """Test validation catches common errors."""

    def test_validate_missing_modules(self):
        """Test error when modules is not a dict."""
        schema = UniversalIndexSchema(
            modules=None,  # Invalid!
            metadata={
                "indexed_at": "2024-01-01T00:00:00Z",
                "total_modules": 0,
                "total_functions": 0,
                "repo_path": "/path/to/repo",
            },
        )

        is_valid, errors = schema.validate(strict=True)

        assert is_valid is False
        assert len(errors) == 1
        assert "'modules' must be a dictionary" in errors[0]

    def test_validate_missing_metadata(self):
        """Test error when metadata is not a dict."""
        schema = UniversalIndexSchema(
            modules={},
            metadata=None,  # Invalid!
        )

        is_valid, errors = schema.validate(strict=True)

        assert is_valid is False
        assert len(errors) == 1
        assert "'metadata' must be a dictionary" in errors[0]

    def test_validate_missing_metadata_required_fields(self):
        """Test error when required metadata fields are missing."""
        schema = UniversalIndexSchema(
            modules={},
            metadata={
                "indexed_at": "2024-01-01T00:00:00Z",
                # Missing: total_modules, total_functions, repo_path
            },
        )

        is_valid, errors = schema.validate(strict=True)

        assert is_valid is False
        assert any("total_modules" in err for err in errors)
        assert any("total_functions" in err for err in errors)
        assert any("repo_path" in err for err in errors)

    def test_validate_invalid_module_structure(self):
        """Test error when module data is not a dict."""
        schema = UniversalIndexSchema(
            modules={
                "MyModule": "invalid_string",  # Should be dict!
            },
            metadata={
                "indexed_at": "2024-01-01T00:00:00Z",
                "total_modules": 1,
                "total_functions": 0,
                "repo_path": "/path/to/repo",
            },
        )

        is_valid, errors = schema.validate(strict=True)

        assert is_valid is False
        assert any("must be a dictionary" in err for err in errors)

    def test_validate_missing_required_module_fields(self):
        """Test error when required module fields are missing."""
        schema = UniversalIndexSchema(
            modules={
                "MyModule": {
                    # Missing: file, line, functions
                }
            },
            metadata={
                "indexed_at": "2024-01-01T00:00:00Z",
                "total_modules": 1,
                "total_functions": 0,
                "repo_path": "/path/to/repo",
            },
        )

        is_valid, errors = schema.validate(strict=True)

        assert is_valid is False
        assert any("'file'" in err for err in errors)
        assert any("'line'" in err for err in errors)
        assert any("'functions'" in err for err in errors)

    def test_validate_invalid_function_structure(self):
        """Test error when function is not a dict."""
        schema = UniversalIndexSchema(
            modules={
                "MyModule": {
                    "file": "lib/my_module.ex",
                    "line": 1,
                    "functions": ["invalid_string"],  # Should be list of dicts!
                    "calls": [],
                }
            },
            metadata={
                "indexed_at": "2024-01-01T00:00:00Z",
                "total_modules": 1,
                "total_functions": 0,
                "repo_path": "/path/to/repo",
            },
        )

        is_valid, errors = schema.validate(strict=True)

        assert is_valid is False
        assert any("must be a dictionary" in err for err in errors)

    def test_validate_missing_required_function_fields(self):
        """Test error when required function fields are missing."""
        schema = UniversalIndexSchema(
            modules={
                "MyModule": {
                    "file": "lib/my_module.ex",
                    "line": 1,
                    "functions": [
                        {
                            # Missing: name, arity, args, type, line, signature
                        }
                    ],
                    "calls": [],
                }
            },
            metadata={
                "indexed_at": "2024-01-01T00:00:00Z",
                "total_modules": 1,
                "total_functions": 0,
                "repo_path": "/path/to/repo",
            },
        )

        is_valid, errors = schema.validate(strict=True)

        assert is_valid is False
        assert any("'name'" in err for err in errors)
        assert any("'arity'" in err for err in errors)
        assert any("'args'" in err for err in errors)
        assert any("'type'" in err for err in errors)

    def test_validate_arity_args_mismatch(self):
        """Test error when arity doesn't match args length."""
        schema = UniversalIndexSchema(
            modules={
                "MyModule": {
                    "file": "lib/my_module.ex",
                    "line": 1,
                    "functions": [
                        {
                            "name": "my_func",
                            "arity": 3,  # Says 3
                            "args": ["x", "y"],  # But only 2 args!
                            "type": "public",
                            "line": 5,
                            "signature": "def my_func(x, y)",
                        }
                    ],
                    "calls": [],
                }
            },
            metadata={
                "indexed_at": "2024-01-01T00:00:00Z",
                "total_modules": 1,
                "total_functions": 1,
                "repo_path": "/path/to/repo",
            },
        )

        is_valid, errors = schema.validate(strict=True)

        assert is_valid is False
        assert any("does not match args length" in err for err in errors)

    def test_validate_negative_counts(self):
        """Test error when counts are negative."""
        # Test negative metadata counts
        schema1 = UniversalIndexSchema(
            modules={},
            metadata={
                "indexed_at": "2024-01-01T00:00:00Z",
                "total_modules": -1,  # Negative!
                "total_functions": -5,  # Negative!
                "repo_path": "/path/to/repo",
            },
        )

        is_valid, errors = schema1.validate(strict=True)

        assert is_valid is False
        assert any("must be non-negative" in err for err in errors)

        # Test negative arity
        schema2 = UniversalIndexSchema(
            modules={
                "MyModule": {
                    "file": "lib/my_module.ex",
                    "line": 1,
                    "functions": [
                        {
                            "name": "my_func",
                            "arity": -2,  # Negative!
                            "args": [],
                            "type": "public",
                            "line": 5,
                            "signature": "def my_func()",
                        }
                    ],
                    "calls": [],
                }
            },
            metadata={
                "indexed_at": "2024-01-01T00:00:00Z",
                "total_modules": 1,
                "total_functions": 1,
                "repo_path": "/path/to/repo",
            },
        )

        is_valid, errors = schema2.validate(strict=True)

        assert is_valid is False
        assert any("must be non-negative" in err for err in errors)

    def test_validate_invalid_types(self):
        """Test error when field types are wrong."""
        schema = UniversalIndexSchema(
            modules={
                "MyModule": {
                    "file": "lib/my_module.ex",
                    "line": 1,
                    "functions": [
                        {
                            "name": "my_func",
                            "arity": "two",  # Should be int!
                            "args": "x, y",  # Should be list!
                            "type": 123,  # Should be string!
                            "line": "five",  # Should be int!
                            "signature": ["def", "my_func"],  # Should be string!
                        }
                    ],
                    "calls": [],
                }
            },
            metadata={
                "indexed_at": "2024-01-01T00:00:00Z",
                "total_modules": 1,
                "total_functions": 1,
                "repo_path": "/path/to/repo",
            },
        )

        is_valid, errors = schema.validate(strict=True)

        assert is_valid is False
        assert len(errors) >= 5  # Multiple type errors


# ============================================================================
# SECTION 4: Validation Error Path Tests (Edge Cases)
# ============================================================================


class TestValidationErrorsEdgeCases:
    """Test validation catches edge case errors."""

    def test_validate_invalid_line_numbers(self):
        """Test error when line numbers are <= 0."""
        schema = UniversalIndexSchema(
            modules={
                "MyModule": {
                    "file": "lib/my_module.ex",
                    "line": 0,  # Invalid!
                    "functions": [
                        {
                            "name": "my_func",
                            "arity": 0,
                            "args": [],
                            "type": "public",
                            "line": -5,  # Invalid!
                            "signature": "def my_func()",
                        }
                    ],
                    "calls": [],
                }
            },
            metadata={
                "indexed_at": "2024-01-01T00:00:00Z",
                "total_modules": 1,
                "total_functions": 1,
                "repo_path": "/path/to/repo",
            },
        )

        is_valid, errors = schema.validate(strict=True)

        assert is_valid is False
        assert any("must be positive" in err for err in errors)

    def test_validate_empty_required_strings(self):
        """Test error when required strings are empty."""
        schema = UniversalIndexSchema(
            modules={
                "MyModule": {
                    "file": "lib/my_module.ex",
                    "line": 1,
                    "functions": [
                        {
                            "name": "my_func",
                            "arity": 0,
                            "args": [],
                            "type": "",  # Empty string!
                            "line": 5,
                            "signature": "def my_func()",
                        }
                    ],
                    "calls": [],
                }
            },
            metadata={
                "indexed_at": "2024-01-01T00:00:00Z",
                "total_modules": 1,
                "total_functions": 1,
                "repo_path": "/path/to/repo",
            },
        )

        is_valid, errors = schema.validate(strict=True)

        assert is_valid is False
        assert any("cannot be empty" in err for err in errors)

    def test_validate_invalid_optional_fields(self):
        """Test error when optional fields have wrong types."""
        schema = UniversalIndexSchema(
            modules={
                "MyModule": {
                    "file": "lib/my_module.ex",
                    "line": 1,
                    "functions": [
                        {
                            "name": "my_func",
                            "arity": 0,
                            "args": [],
                            "type": "public",
                            "line": 5,
                            "signature": "def my_func()",
                            "doc": 123,  # Should be string or None!
                            "keywords": ["key1", "key2"],  # Should be dict or None!
                        }
                    ],
                    "calls": "not_a_list",  # Should be list!
                }
            },
            metadata={
                "indexed_at": "2024-01-01T00:00:00Z",
                "total_modules": 1,
                "total_functions": 1,
                "repo_path": "/path/to/repo",
            },
        )

        is_valid, errors = schema.validate(strict=True)

        assert is_valid is False
        assert any("doc" in err for err in errors)
        assert any("keywords" in err for err in errors)
        assert any("calls" in err for err in errors)

    def test_validate_invalid_call_structure(self):
        """Test error when call structure is invalid."""
        # Call is not a dict
        schema1 = UniversalIndexSchema(
            modules={
                "MyModule": {
                    "file": "lib/my_module.ex",
                    "line": 1,
                    "functions": [],
                    "calls": ["invalid"],  # Should be list of dicts!
                }
            },
            metadata={
                "indexed_at": "2024-01-01T00:00:00Z",
                "total_modules": 1,
                "total_functions": 0,
                "repo_path": "/path/to/repo",
            },
        )

        is_valid, errors = schema1.validate(strict=True)
        assert is_valid is False
        assert any("must be a dictionary" in err for err in errors)

        # Missing required call fields
        schema2 = UniversalIndexSchema(
            modules={
                "MyModule": {
                    "file": "lib/my_module.ex",
                    "line": 1,
                    "functions": [],
                    "calls": [
                        {
                            # Missing: function, arity, line
                        }
                    ],
                }
            },
            metadata={
                "indexed_at": "2024-01-01T00:00:00Z",
                "total_modules": 1,
                "total_functions": 0,
                "repo_path": "/path/to/repo",
            },
        )

        is_valid, errors = schema2.validate(strict=True)
        assert is_valid is False
        assert any("'function'" in err for err in errors)
        assert any("'arity'" in err for err in errors)
        assert any("'line'" in err for err in errors)

        # Invalid call field types
        schema3 = UniversalIndexSchema(
            modules={
                "MyModule": {
                    "file": "lib/my_module.ex",
                    "line": 1,
                    "functions": [],
                    "calls": [
                        {
                            "function": 123,  # Should be string!
                            "arity": "two",  # Should be int!
                            "line": "ten",  # Should be int!
                            "module": 456,  # Should be string or None!
                        }
                    ],
                }
            },
            metadata={
                "indexed_at": "2024-01-01T00:00:00Z",
                "total_modules": 1,
                "total_functions": 0,
                "repo_path": "/path/to/repo",
            },
        )

        is_valid, errors = schema3.validate(strict=True)
        assert is_valid is False
        assert len(errors) >= 4  # Multiple type errors

        # Negative arity in call
        schema4 = UniversalIndexSchema(
            modules={
                "MyModule": {
                    "file": "lib/my_module.ex",
                    "line": 1,
                    "functions": [],
                    "calls": [
                        {
                            "function": "my_func",
                            "arity": -1,  # Negative!
                            "line": 10,
                        }
                    ],
                }
            },
            metadata={
                "indexed_at": "2024-01-01T00:00:00Z",
                "total_modules": 1,
                "total_functions": 0,
                "repo_path": "/path/to/repo",
            },
        )

        is_valid, errors = schema4.validate(strict=True)
        assert is_valid is False
        assert any("must be non-negative" in err for err in errors)

        # Invalid line in call
        schema5 = UniversalIndexSchema(
            modules={
                "MyModule": {
                    "file": "lib/my_module.ex",
                    "line": 1,
                    "functions": [],
                    "calls": [
                        {
                            "function": "my_func",
                            "arity": 0,
                            "line": 0,  # Invalid!
                        }
                    ],
                }
            },
            metadata={
                "indexed_at": "2024-01-01T00:00:00Z",
                "total_modules": 1,
                "total_functions": 0,
                "repo_path": "/path/to/repo",
            },
        )

        is_valid, errors = schema5.validate(strict=True)
        assert is_valid is False
        assert any("must be positive" in err for err in errors)

    def test_validate_invalid_args_types(self):
        """Test error when args contain non-strings."""
        schema = UniversalIndexSchema(
            modules={
                "MyModule": {
                    "file": "lib/my_module.ex",
                    "line": 1,
                    "functions": [
                        {
                            "name": "my_func",
                            "arity": 3,
                            "args": ["x", 123, None],  # Should all be strings!
                            "type": "public",
                            "line": 5,
                            "signature": "def my_func(x, y, z)",
                        }
                    ],
                    "calls": [],
                }
            },
            metadata={
                "indexed_at": "2024-01-01T00:00:00Z",
                "total_modules": 1,
                "total_functions": 1,
                "repo_path": "/path/to/repo",
            },
        )

        is_valid, errors = schema.validate(strict=True)

        assert is_valid is False
        assert any("must be a string" in err for err in errors)

    def test_validate_metadata_type_errors(self):
        """Test error when metadata fields have wrong types."""
        schema = UniversalIndexSchema(
            modules={},
            metadata={
                "indexed_at": 123,  # Should be string!
                "total_modules": "ten",  # Should be int!
                "total_functions": 5.5,  # Should be int!
                "repo_path": ["path", "to", "repo"],  # Should be string!
                "language": 123,  # Should be string!
                "version": ["2", "0"],  # Should be string!
            },
        )

        is_valid, errors = schema.validate(strict=True)

        assert is_valid is False
        assert len(errors) >= 4  # Multiple type errors


# ============================================================================
# SECTION 5: Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Test edge cases like empty collections, unicode, special chars."""

    def test_empty_modules_dict(self):
        """Test schema with no modules."""
        schema = UniversalIndexSchema(
            modules={},  # Empty!
            metadata={
                "indexed_at": "2024-01-01T00:00:00Z",
                "total_modules": 0,
                "total_functions": 0,
                "repo_path": "/path/to/repo",
            },
        )

        is_valid, errors = schema.validate(strict=True)

        assert is_valid is True
        assert len(errors) == 0

    def test_empty_functions_list(self):
        """Test module with no functions."""
        schema = UniversalIndexSchema(
            modules={
                "MyModule": {
                    "file": "lib/my_module.ex",
                    "line": 1,
                    "functions": [],  # Empty!
                    "calls": [],
                }
            },
            metadata={
                "indexed_at": "2024-01-01T00:00:00Z",
                "total_modules": 1,
                "total_functions": 0,
                "repo_path": "/path/to/repo",
            },
        )

        is_valid, errors = schema.validate(strict=True)

        assert is_valid is True
        assert len(errors) == 0

    def test_unicode_in_names_and_docs(self):
        """Test that unicode is handled properly."""
        func = FunctionData(
            name="функция",  # Cyrillic
            arity=1,
            args=["参数"],  # Chinese
            type="公开",  # Chinese
            visibility="public",
            line=10,
            signature="def функция(参数)",
            doc="Cette fonction résout le problème très facilement",  # French with accents
        )

        func_dict = func.to_dict()
        func_restored = FunctionData.from_dict(func_dict)

        assert func_restored.name == "функция"
        assert func_restored.args == ["参数"]
        assert func_restored.type == "公开"
        assert func_restored.doc == "Cette fonction résout le problème très facilement"

    def test_special_characters_in_signatures(self):
        """Test special characters in signatures and paths."""
        module = ModuleData(
            name="MyModule<T>",
            file="lib/path with spaces/my_module.ex",
            line=1,
        )

        func = FunctionData(
            name="operator++",
            arity=2,
            args=["a", "b"],
            type="public",
            visibility="public",
            line=5,
            signature="def operator++(a, b) -> Result<T, Error>",
        )

        module_dict = module.to_dict()
        func_dict = func.to_dict()

        module_restored = ModuleData.from_dict("MyModule<T>", module_dict)
        func_restored = FunctionData.from_dict(func_dict)

        assert module_restored.name == "MyModule<T>"
        assert module_restored.file == "lib/path with spaces/my_module.ex"
        assert func_restored.name == "operator++"
        assert func_restored.signature == "def operator++(a, b) -> Result<T, Error>"

    def test_zero_arity_function(self):
        """Test function with zero arity."""
        schema = UniversalIndexSchema(
            modules={
                "MyModule": {
                    "file": "lib/my_module.ex",
                    "line": 1,
                    "functions": [
                        {
                            "name": "zero_arity",
                            "arity": 0,
                            "args": [],
                            "type": "public",
                            "visibility": "public",
                            "line": 5,
                            "signature": "def zero_arity()",
                        }
                    ],
                    "calls": [],
                }
            },
            metadata={
                "indexed_at": "2024-01-01T00:00:00Z",
                "total_modules": 1,
                "total_functions": 1,
                "repo_path": "/path/to/repo",
            },
        )

        is_valid, errors = schema.validate(strict=True)

        assert is_valid is True
        assert len(errors) == 0

    def test_large_arity_function(self):
        """Test function with many parameters."""
        large_args = [f"arg{i}" for i in range(100)]

        func = FunctionData(
            name="many_args",
            arity=100,
            args=large_args,
            type="public",
            visibility="public",
            line=10,
            signature=f"def many_args({', '.join(large_args)})",
        )

        func_dict = func.to_dict()
        func_restored = FunctionData.from_dict(func_dict)

        assert func_restored.arity == 100
        assert len(func_restored.args) == 100

    def test_none_values_in_optional_fields(self):
        """Test that None values in optional fields are handled correctly."""
        func = FunctionData(
            name="my_func",
            arity=0,
            args=[],
            type="public",
            visibility="public",
            line=10,
            signature="def my_func()",
            doc=None,
            spec=None,
            keywords=None,
        )

        func_dict = func.to_dict()
        func_restored = FunctionData.from_dict(func_dict)

        assert func_restored.doc is None
        assert func_restored.spec is None
        assert func_restored.keywords is None

    def test_deeply_nested_language_specific_fields(self):
        """Test deeply nested structures in language_specific."""
        func = FunctionData(
            name="my_func",
            arity=0,
            args=[],
            type="public",
            visibility="public",
            line=10,
            signature="def my_func()",
            language_specific={
                "nested": {"deeply": {"very": {"much": "value"}}},
                "list_of_dicts": [
                    {"key1": "value1"},
                    {"key2": "value2"},
                ],
            },
        )

        func_dict = func.to_dict()
        func_restored = FunctionData.from_dict(func_dict)

        assert func_restored.language_specific["nested"]["deeply"]["very"]["much"] == "value"
        assert len(func_restored.language_specific["list_of_dicts"]) == 2
