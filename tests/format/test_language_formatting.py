"""Integration tests for language-specific formatting."""

import pytest

from cicada.format.formatter import ModuleFormatter
from cicada.utils.signature_builder import SignatureBuilder


class TestSignatureBuilderLanguages:
    """Test SignatureBuilder with different languages."""

    def test_elixir_signature_with_return_type(self):
        """Test Elixir signature with return type uses :: notation."""
        func = {
            "name": "create_user",
            "arity": 2,
            "args_with_types": [
                {"name": "attrs", "type": "map"},
                {"name": "opts", "type": "keyword"},
            ],
            "return_type": "{:ok, User.t()} | {:error, term()}",
        }

        sig = SignatureBuilder.build(func, language="elixir")
        assert sig == "create_user(attrs: map, opts: keyword) :: {:ok, User.t()} | {:error, term()}"

    def test_python_signature_with_return_type(self):
        """Test Python signature with return type uses -> notation."""
        func = {
            "name": "create_user",
            "arity": 2,
            "args_with_types": [
                {"name": "attrs", "type": "dict"},
                {"name": "opts", "type": "dict"},
            ],
            "return_type": "User",
        }

        sig = SignatureBuilder.build(func, language="python")
        assert sig == "def create_user(attrs: dict, opts: dict) -> User:"

    def test_python_signature_without_return_type(self):
        """Test Python signature without return type still has colon."""
        func = {
            "name": "helper",
            "arity": 2,
            "args_with_types": [{"name": "x", "type": "int"}, {"name": "y", "type": "str"}],
        }

        sig = SignatureBuilder.build(func, language="python")
        assert sig == "def helper(x: int, y: str):"

    def test_elixir_signature_without_return_type(self):
        """Test Elixir signature without return type has no colon."""
        func = {
            "name": "helper",
            "arity": 2,
            "args_with_types": [{"name": "x", "type": "integer"}, {"name": "y", "type": "binary"}],
        }

        sig = SignatureBuilder.build(func, language="elixir")
        assert sig == "helper(x: integer, y: binary)"

    def test_signature_with_no_args(self):
        """Test signature with zero arguments."""
        func = {"name": "now", "arity": 0, "args": []}

        elixir_sig = SignatureBuilder.build(func, language="elixir")
        python_sig = SignatureBuilder.build(func, language="python")

        assert elixir_sig == "now()"
        assert python_sig == "def now():"

    def test_signature_fallback_to_arity_notation(self):
        """Test fallback to name/arity notation when no arg details available."""
        func = {"name": "process", "arity": 3}

        sig = SignatureBuilder.build(func, language="elixir")
        assert sig == "process/3"

    def test_signature_with_args_list_only(self):
        """Test signature with args list but no types."""
        func = {"name": "calculate", "arity": 2, "args": ["x", "y"]}

        elixir_sig = SignatureBuilder.build(func, language="elixir")
        python_sig = SignatureBuilder.build(func, language="python")

        assert elixir_sig == "calculate(x, y)"
        assert python_sig == "def calculate(x, y):"

    def test_signature_default_language_is_elixir(self):
        """Test that default language is Elixir when not specified."""
        func = {"name": "test", "arity": 0, "args": []}

        sig = SignatureBuilder.build(func)  # No language specified
        assert sig == "test()"  # Elixir format (no 'def', no colon)


class TestModuleFormatterLanguages:
    """Test ModuleFormatter with different languages."""

    def setup_method(self):
        """Set up test data."""
        self.module_data = {
            "file": "lib/my_app/user.ex",
            "line": 1,
            "moduledoc": "User management module.",
            "public_functions": 1,
            "private_functions": 1,
            "functions": [
                {
                    "name": "create",
                    "arity": 2,
                    "type": "public",
                    "line": 10,
                    "args_with_types": [
                        {"name": "attrs", "type": "map"},
                        {"name": "opts", "type": "keyword"},
                    ],
                    "return_type": "{:ok, User.t()}",
                },
                {"name": "helper", "arity": 1, "type": "private", "line": 20, "args": ["data"]},
            ],
        }

    def test_module_markdown_elixir(self):
        """Test module formatting for Elixir."""
        result = ModuleFormatter.format_module_markdown(
            "MyApp.User", self.module_data, private_functions="include", language="elixir"
        )

        # Check header format
        assert "MyApp.User" in result
        assert "lib/my_app/user.ex:1" in result
        assert "1 public" in result
        assert "1 private" in result

        # Check function signatures are in Elixir format
        assert "create(attrs: map, opts: keyword) :: {:ok, User.t()}" in result
        assert "helper(data)" in result

        # Should NOT have 'def' prefix (Elixir format)
        assert "def create" not in result

    def test_module_markdown_python(self):
        """Test module formatting for Python."""
        # Adjust data for Python
        python_data = {
            "file": "my_app/user.py",
            "line": 1,
            "moduledoc": "User management module.",
            "functions": [
                {
                    "name": "create",
                    "arity": 2,
                    "type": "public",
                    "line": 10,
                    "args_with_types": [
                        {"name": "attrs", "type": "dict"},
                        {"name": "opts", "type": "dict"},
                    ],
                    "return_type": "User",
                },
                {"name": "_helper", "arity": 1, "type": "private", "line": 20, "args": ["data"]},
            ],
        }

        result = ModuleFormatter.format_module_markdown(
            "my_app.user", python_data, private_functions="include", language="python"
        )

        # Check header format
        assert "my_app.user" in result
        assert "my_app/user.py:1" in result

        # Check function signatures are in Python format
        assert "def create(attrs: dict, opts: dict) -> User:" in result
        assert "def _helper(data):" in result

    def test_module_json_elixir(self):
        """Test module JSON formatting for Elixir."""
        result = ModuleFormatter.format_module_json(
            "MyApp.User", self.module_data, private_functions="exclude", language="elixir"
        )

        # Check that it's valid JSON
        import json

        data = json.loads(result)

        # Check structure
        assert data["module"] == "MyApp.User"
        assert len(data["functions"]) == 1  # Only public

        # Check signature format
        sig = data["functions"][0]["signature"]
        assert "create(attrs: map, opts: keyword) :: {:ok, User.t()}" == sig

    def test_module_json_python(self):
        """Test module JSON formatting for Python."""
        python_data = {
            "file": "my_app/user.py",
            "line": 1,
            "moduledoc": "User management module.",
            "public_functions": 1,
            "private_functions": 0,
            "functions": [
                {
                    "name": "create",
                    "arity": 2,
                    "type": "public",
                    "line": 10,
                    "args_with_types": [
                        {"name": "attrs", "type": "dict"},
                        {"name": "opts", "type": "dict"},
                    ],
                    "return_type": "User",
                }
            ],
        }

        result = ModuleFormatter.format_module_json(
            "my_app.user", python_data, private_functions="exclude", language="python"
        )

        # Check that it's valid JSON
        import json

        data = json.loads(result)

        # Check signature format
        sig = data["functions"][0]["signature"]
        assert "def create(attrs: dict, opts: dict) -> User:" == sig

    def test_function_results_markdown_elixir(self):
        """Test function search results formatting for Elixir."""
        results = [
            {
                "module": "MyApp.User",
                "file": "lib/my_app/user.ex",
                "function": {
                    "name": "create",
                    "arity": 2,
                    "line": 10,
                    "type": "def",
                    "args_with_types": [
                        {"name": "attrs", "type": "map"},
                        {"name": "opts", "type": "keyword"},
                    ],
                    "return_type": "{:ok, User.t()}",
                    "doc": "Creates a new user.",
                },
                "call_sites": [],
            }
        ]

        result = ModuleFormatter.format_function_results_markdown(
            "create", results, language="elixir"
        )

        # Check signature format
        assert "create(attrs: map, opts: keyword) :: {:ok, User.t()}" in result
        assert "MyApp.User.create/2" in result

    def test_function_results_markdown_python(self):
        """Test function search results formatting for Python."""
        results = [
            {
                "module": "my_app.user",
                "file": "my_app/user.py",
                "function": {
                    "name": "create",
                    "arity": 2,
                    "line": 10,
                    "type": "public",
                    "args_with_types": [
                        {"name": "attrs", "type": "dict"},
                        {"name": "opts", "type": "dict"},
                    ],
                    "return_type": "User",
                    "doc": "Creates a new user.",
                },
                "call_sites": [],
            }
        ]

        result = ModuleFormatter.format_function_results_markdown(
            "create", results, language="python"
        )

        # Check signature format
        assert "def create(attrs: dict, opts: dict) -> User:" in result
        # Python doesn't use /arity notation in the same way
        assert "my_app.user.create" in result

    def test_formatter_default_language_is_elixir(self):
        """Test that formatters default to Elixir when language not specified."""
        result = ModuleFormatter.format_module_markdown("MyApp.User", self.module_data)

        # Should use Elixir format by default
        assert "create(attrs: map, opts: keyword) :: {:ok, User.t()}" in result
        assert "def create" not in result  # No 'def' prefix
