"""Tests for SignatureBuilder utility."""

import pytest

from cicada.utils.signature_builder import SignatureBuilder


class TestSignatureBuilder:
    """Test the SignatureBuilder class."""

    def test_build_with_args_and_types(self):
        """Test building signature with typed arguments."""
        func = {
            "name": "create_user",
            "arity": 2,
            "args_with_types": [
                {"name": "attrs", "type": "map"},
                {"name": "opts", "type": "keyword"},
            ],
            "return_type": "{:ok, User.t()} | {:error, Ecto.Changeset.t()}",
        }
        result = SignatureBuilder.build(func)
        assert (
            result
            == "create_user(attrs: map, opts: keyword) :: {:ok, User.t()} | {:error, Ecto.Changeset.t()}"
        )

    def test_build_with_args_without_types(self):
        """Test building signature with untyped arguments."""
        func = {
            "name": "calculate",
            "arity": 2,
            "args": ["x", "y"],
        }
        result = SignatureBuilder.build(func)
        assert result == "calculate(x, y)"

    def test_build_with_args_without_types_and_return_type(self):
        """Test building signature with untyped arguments and return type."""
        func = {
            "name": "add",
            "arity": 2,
            "args": ["a", "b"],
            "return_type": "integer",
        }
        result = SignatureBuilder.build(func)
        assert result == "add(a, b) :: integer"

    def test_build_zero_arity(self):
        """Test building signature for zero-arity function."""
        func = {
            "name": "get_config",
            "arity": 0,
        }
        result = SignatureBuilder.build(func)
        assert result == "get_config()"

    def test_build_zero_arity_with_return_type(self):
        """Test building signature for zero-arity function with return type."""
        func = {
            "name": "version",
            "arity": 0,
            "return_type": "String.t()",
        }
        result = SignatureBuilder.build(func)
        assert result == "version() :: String.t()"

    def test_build_fallback_to_name_arity(self):
        """Test fallback to name/arity notation when no args available."""
        func = {
            "name": "process",
            "arity": 3,
        }
        result = SignatureBuilder.build(func)
        assert result == "process/3"

    def test_build_fallback_to_name_arity_with_return_type(self):
        """Test fallback to name/arity notation with return type."""
        func = {
            "name": "transform",
            "arity": 2,
            "return_type": "list",
        }
        result = SignatureBuilder.build(func)
        assert result == "transform/2 :: list"

    def test_build_with_empty_args_list(self):
        """Test building signature with empty args list (should use zero arity format)."""
        func = {
            "name": "init",
            "arity": 0,
            "args": [],
        }
        result = SignatureBuilder.build(func)
        assert result == "init()"

    def test_build_with_args_with_types_missing_type(self):
        """Test args_with_types where some args are missing type annotations."""
        func = {
            "name": "mixed_args",
            "arity": 3,
            "args_with_types": [
                {"name": "typed_arg", "type": "map"},
                {"name": "untyped_arg"},  # No type
                {"name": "another_typed", "type": "list"},
            ],
        }
        result = SignatureBuilder.build(func)
        assert result == "mixed_args(typed_arg: map, untyped_arg, another_typed: list)"

    def test_build_with_args_with_types_all_missing_types(self):
        """Test args_with_types where all args are missing type annotations."""
        func = {
            "name": "all_untyped",
            "arity": 2,
            "args_with_types": [
                {"name": "arg1"},
                {"name": "arg2"},
            ],
        }
        result = SignatureBuilder.build(func)
        assert result == "all_untyped(arg1, arg2)"

    def test_build_with_complex_return_types(self):
        """Test building signature with complex return types."""
        func = {
            "name": "fetch_data",
            "arity": 1,
            "args_with_types": [{"name": "id", "type": "integer"}],
            "return_type": "{:ok, %{name: String.t(), age: integer}} | {:error, atom}",
        }
        result = SignatureBuilder.build(func)
        assert (
            result
            == "fetch_data(id: integer) :: {:ok, %{name: String.t(), age: integer}} | {:error, atom}"
        )

    def test_format_args_with_types_empty(self):
        """Test formatting empty args list."""
        result = SignatureBuilder._format_args_with_types([])
        assert result == ""

    def test_format_args_with_types_single_arg(self):
        """Test formatting single argument with type."""
        args = [{"name": "value", "type": "map"}]
        result = SignatureBuilder._format_args_with_types(args)
        assert result == "value: map"

    def test_format_args_with_types_multiple_args(self):
        """Test formatting multiple arguments with types."""
        args = [
            {"name": "x", "type": "integer"},
            {"name": "y", "type": "float"},
            {"name": "opts", "type": "keyword"},
        ]
        result = SignatureBuilder._format_args_with_types(args)
        assert result == "x: integer, y: float, opts: keyword"

    def test_format_args_with_types_no_type(self):
        """Test formatting argument without type annotation."""
        args = [{"name": "arg"}]
        result = SignatureBuilder._format_args_with_types(args)
        assert result == "arg"

    def test_format_args_with_types_mixed(self):
        """Test formatting mix of typed and untyped arguments."""
        args = [
            {"name": "typed", "type": "map"},
            {"name": "untyped"},
            {"name": "also_typed", "type": "list"},
        ]
        result = SignatureBuilder._format_args_with_types(args)
        assert result == "typed: map, untyped, also_typed: list"

    def test_build_with_single_arg(self):
        """Test building signature with single argument."""
        func = {
            "name": "validate",
            "arity": 1,
            "args_with_types": [{"name": "data", "type": "map"}],
        }
        result = SignatureBuilder.build(func)
        assert result == "validate(data: map)"

    def test_build_with_special_characters_in_types(self):
        """Test building signature with special characters in type annotations."""
        func = {
            "name": "process",
            "arity": 1,
            "args_with_types": [{"name": "input", "type": "String.t() | nil"}],
            "return_type": "{:ok, result()} | {:error, reason()}",
        }
        result = SignatureBuilder.build(func)
        assert result == "process(input: String.t() | nil) :: {:ok, result()} | {:error, reason()}"

    def test_build_preserves_args_with_types_priority(self):
        """Test that args_with_types takes priority over args when both present."""
        func = {
            "name": "both_present",
            "arity": 2,
            "args": ["should", "ignore"],
            "args_with_types": [
                {"name": "use", "type": "this"},
                {"name": "instead", "type": "please"},
            ],
        }
        result = SignatureBuilder.build(func)
        assert result == "both_present(use: this, instead: please)"

    def test_build_with_empty_return_type(self):
        """Test that empty return type string is not appended."""
        func = {
            "name": "no_return_shown",
            "arity": 1,
            "args": ["arg"],
            "return_type": "",  # Empty string should be treated as no return type
        }
        result = SignatureBuilder.build(func)
        # Empty string is falsy, so no :: should be appended
        assert result == "no_return_shown(arg)"
