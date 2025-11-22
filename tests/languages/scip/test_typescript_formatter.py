"""Tests for TypeScript-specific formatting.

These tests verify that TypeScript code is formatted with proper TypeScript
conventions (parentheses notation, not Elixir's /arity notation).
"""

import pytest

from cicada.languages.formatter_interface import BaseLanguageFormatter
from cicada.languages.formatter_registry import get_language_formatter
from cicada.languages.scip.reader import SCIPReader
from cicada.languages.scip.converter import SCIPConverter
from cicada.format.formatter import ModuleFormatter


class TestTypeScriptFormatter:
    """Test the TypeScriptFormatter class."""

    def test_typescript_formatter_exists(self):
        """Test that TypeScriptFormatter class can be imported."""
        # This will fail until we create TypeScriptFormatter
        from cicada.languages.scip.formatter import TypeScriptFormatter

        assert TypeScriptFormatter is not None
        assert issubclass(TypeScriptFormatter, BaseLanguageFormatter)

    def test_format_typescript_function(self):
        """Test formatting for TypeScript uses () notation, not /arity."""
        from cicada.languages.scip.formatter import TypeScriptFormatter

        formatter = TypeScriptFormatter()
        result = formatter.format_function_identifier("Container", "add", 1)

        # TypeScript should use parentheses, not /arity
        assert result == "Container.add()"
        assert "/1" not in result  # Should NOT use Elixir notation

    def test_format_zero_arity_typescript(self):
        """Test zero-arity function in TypeScript."""
        from cicada.languages.scip.formatter import TypeScriptFormatter

        formatter = TypeScriptFormatter()
        result = formatter.format_function_identifier("Calculator", "reset", 0)

        assert result == "Calculator.reset()"
        assert "/0" not in result

    def test_format_multiple_arity_typescript(self):
        """Test that TypeScript doesn't use arity in notation."""
        from cicada.languages.scip.formatter import TypeScriptFormatter

        formatter = TypeScriptFormatter()

        # TypeScript doesn't distinguish by arity in notation
        result_arity_0 = formatter.format_function_identifier("MyClass", "method", 0)
        result_arity_2 = formatter.format_function_identifier("MyClass", "method", 2)
        result_arity_5 = formatter.format_function_identifier("MyClass", "method", 5)

        # All should use the same () notation
        assert result_arity_0 == "MyClass.method()"
        assert result_arity_2 == "MyClass.method()"
        assert result_arity_5 == "MyClass.method()"

    def test_format_static_method(self):
        """Test formatting static methods."""
        from cicada.languages.scip.formatter import TypeScriptFormatter

        formatter = TypeScriptFormatter()
        result = formatter.format_function_identifier("Container", "getInstanceCount", 0)

        assert result == "Container.getInstanceCount()"

    def test_format_async_function(self):
        """Test formatting async functions (same as regular functions)."""
        from cicada.languages.scip.formatter import TypeScriptFormatter

        formatter = TypeScriptFormatter()
        result = formatter.format_function_identifier("AsyncHandler", "save", 2)

        # Async notation is not part of the identifier
        assert result == "AsyncHandler.save()"

    def test_format_arrow_function(self):
        """Test formatting arrow functions."""
        from cicada.languages.scip.formatter import TypeScriptFormatter

        formatter = TypeScriptFormatter()
        result = formatter.format_function_identifier("typescript_features", "arrowAdd", 2)

        assert result == "typescript_features.arrowAdd()"

    def test_format_constructor(self):
        """Test formatting class constructors."""
        from cicada.languages.scip.formatter import TypeScriptFormatter

        formatter = TypeScriptFormatter()
        result = formatter.format_function_identifier("Container", "constructor", 1)

        assert result == "Container.constructor()"

    def test_format_generic_function(self):
        """Test formatting generic functions (generics not in identifier)."""
        from cicada.languages.scip.formatter import TypeScriptFormatter

        formatter = TypeScriptFormatter()
        result = formatter.format_function_identifier("typescript_features", "mapItems", 2)

        # Type parameters are not part of the identifier
        assert result == "typescript_features.mapItems()"
        assert "<T>" not in result


class TestFormatterRegistryTypeScript:
    """Test the formatter registry for TypeScript language."""

    def test_get_typescript_formatter(self):
        """Test getting TypeScript formatter from registry."""
        formatter = get_language_formatter("typescript")

        # Should return TypeScriptFormatter, not ElixirFormatter
        from cicada.languages.scip.formatter import TypeScriptFormatter

        assert isinstance(formatter, TypeScriptFormatter)

        result = formatter.format_function_identifier("Container", "add", 1)
        assert result == "Container.add()"

    def test_typescript_formatter_not_elixir(self):
        """Test that TypeScript doesn't fall back to Elixir formatter."""
        formatter = get_language_formatter("typescript")

        # Should use () notation, not /arity
        from cicada.languages.elixir.formatter import ElixirFormatter

        assert not isinstance(formatter, ElixirFormatter)

        result = formatter.format_function_identifier("MyClass", "method", 2)
        assert result == "MyClass.method()"
        assert result != "MyClass.method/2"

    def test_typescript_vs_python_formatter_same_notation(self):
        """Test that TypeScript and Python use same notation style."""
        ts_formatter = get_language_formatter("typescript")
        py_formatter = get_language_formatter("python")

        ts_result = ts_formatter.format_function_identifier("MyClass", "method", 2)
        py_result = py_formatter.format_function_identifier("MyClass", "method", 2)

        # Both should use () notation
        assert ts_result == py_result
        assert ts_result == "MyClass.method()"

    def test_typescript_vs_elixir_formatter_different(self):
        """Test that TypeScript and Elixir use different notations."""
        ts_formatter = get_language_formatter("typescript")
        ex_formatter = get_language_formatter("elixir")

        ts_result = ts_formatter.format_function_identifier("MyModule", "func", 2)
        ex_result = ex_formatter.format_function_identifier("MyModule", "func", 2)

        # TypeScript uses (), Elixir uses /arity
        assert ts_result == "MyModule.func()"
        assert ex_result == "MyModule.func/2"
        assert ts_result != ex_result


class TestTypeScriptIndexFormatting:
    """Test formatting TypeScript SCIP indexes with proper notation."""

    @pytest.fixture
    def typescript_index(self, fixtures_dir):
        """Load TypeScript SCIP index for testing."""
        scip_file = fixtures_dir / "sample_typescript" / "index.scip"
        if not scip_file.exists():
            pytest.skip("TypeScript SCIP index not found. Run tests/setup_fixtures.sh")

        reader = SCIPReader()
        scip_index = reader.read_index(scip_file)

        converter = SCIPConverter()
        return converter.convert(scip_index, scip_file.parent)

    def test_module_formatter_uses_typescript_notation(self, typescript_index):
        """Test that ModuleFormatter uses TypeScript notation for TypeScript code."""
        # Get a TypeScript module
        container_module = None
        for module_name, module_data in typescript_index["modules"].items():
            if "Container" in module_name:
                container_module = (module_name, module_data)
                break

        if not container_module:
            pytest.skip("Container class not found in TypeScript index")

        module_name, module_data = container_module

        # Format the module
        formatter = ModuleFormatter()
        output = formatter.format_module_json(module_name, module_data)

        # Verify that known TypeScript members use () notation in signatures,
        # which confirms that the TypeScript formatter is being used.
        assert "(method) add(" in output or "(method) save(" in output

        # Ensure Elixir-style /arity notation is never present in TypeScript output.
        # We explicitly check for common arities as well as "/" in general to
        # catch any fallback to Elixir formatting.
        assert "/1" not in output
        assert "/2" not in output
        assert "/3" not in output
        assert "/" not in output

    def test_language_detection_triggers_typescript_formatter(self, typescript_index):
        """Test that language metadata triggers correct formatter."""
        metadata = typescript_index.get("metadata", {})
        language = metadata.get("language")

        # Should detect as TypeScript
        assert language == "typescript"

        # Should get TypeScript formatter
        formatter = get_language_formatter(language)
        from cicada.languages.scip.formatter import TypeScriptFormatter

        assert isinstance(formatter, TypeScriptFormatter)

    def test_format_all_function_types(self, typescript_index):
        """Test formatting various TypeScript function types."""
        # Find different function types
        function_types = {
            "static": [],
            "async": [],
            "arrow": [],
            "constructor": [],
            "regular": [],
        }

        for module_name, module_data in typescript_index["modules"].items():
            for func in module_data.get("functions", []):
                func_name = func["name"]

                # Categorize by name patterns
                if "constructor" in func_name.lower():
                    function_types["constructor"].append(func)
                elif func_name.startswith("arrow"):
                    function_types["arrow"].append(func)
                elif "async" in func_name.lower() or func_name in ["save", "load", "asyncProcess"]:
                    function_types["async"].append(func)
                elif func_name.startswith("get") or func_name.startswith("reset"):
                    function_types["static"].append(func)
                else:
                    function_types["regular"].append(func)

        # Format each type
        from cicada.languages.scip.formatter import TypeScriptFormatter

        formatter = TypeScriptFormatter()

        for func_type, functions in function_types.items():
            for func in functions[:1]:  # Test at least one of each type
                module_name = "TestModule"
                result = formatter.format_function_identifier(
                    module_name, func["name"], func["arity"]
                )

                # All should use () notation
                assert result.endswith("()")
                assert f"/{func['arity']}" not in result


class TestTypeScriptFormatterEdgeCases:
    """Test edge cases and special scenarios."""

    def test_format_with_special_characters(self):
        """Test formatting function names with special characters."""
        from cicada.languages.scip.formatter import TypeScriptFormatter

        formatter = TypeScriptFormatter()

        # Underscores
        result = formatter.format_function_identifier("MyClass", "_privateMethod", 1)
        assert result == "MyClass._privateMethod()"

        # Double underscores
        result = formatter.format_function_identifier("MyClass", "__internal", 0)
        assert result == "MyClass.__internal()"

    def test_format_with_long_names(self):
        """Test formatting very long function names."""
        from cicada.languages.scip.formatter import TypeScriptFormatter

        formatter = TypeScriptFormatter()
        long_name = "thisIsAVeryLongFunctionNameThatShouldStillWork"

        result = formatter.format_function_identifier("MyClass", long_name, 3)
        assert result == f"MyClass.{long_name}()"

    def test_format_with_numbers(self):
        """Test formatting function names with numbers."""
        from cicada.languages.scip.formatter import TypeScriptFormatter

        formatter = TypeScriptFormatter()
        result = formatter.format_function_identifier("MyClass", "function2", 1)

        assert result == "MyClass.function2()"

    def test_format_interface_method(self):
        """Test formatting interface methods (should work the same)."""
        from cicada.languages.scip.formatter import TypeScriptFormatter

        formatter = TypeScriptFormatter()
        result = formatter.format_function_identifier("DataProcessor", "process", 1)

        assert result == "DataProcessor.process()"

    def test_format_type_alias(self):
        """Test formatting type aliases (treated as modules/classes)."""
        from cicada.languages.scip.formatter import TypeScriptFormatter

        formatter = TypeScriptFormatter()
        # Type aliases don't have methods, but if they did...
        result = formatter.format_function_identifier("ProcessResult", "someMethod", 0)

        assert result == "ProcessResult.someMethod()"


class TestTypeScriptFormatterImplementationDetails:
    """Test implementation details and interface compliance."""

    def test_implements_base_formatter_interface(self):
        """Test that TypeScriptFormatter implements BaseLanguageFormatter."""
        from cicada.languages.scip.formatter import TypeScriptFormatter

        formatter = TypeScriptFormatter()

        # Should have the required method
        assert hasattr(formatter, "format_function_identifier")
        assert callable(formatter.format_function_identifier)

    def test_method_signature_matches_interface(self):
        """Test that method signature matches the interface."""
        from cicada.languages.scip.formatter import TypeScriptFormatter
        import inspect

        formatter = TypeScriptFormatter()
        method = formatter.format_function_identifier

        # Should accept: module_name, func_name, arity
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())

        assert len(params) == 3
        assert "module_name" in params or params[0] in ["module_name", "module"]
        assert "func_name" in params or params[1] in ["func_name", "function_name", "name"]
        assert "arity" in params or params[2] == "arity"

    def test_returns_string(self):
        """Test that format_function_identifier returns a string."""
        from cicada.languages.scip.formatter import TypeScriptFormatter

        formatter = TypeScriptFormatter()
        result = formatter.format_function_identifier("MyClass", "method", 2)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_consistent_output_format(self):
        """Test that output format is consistent."""
        from cicada.languages.scip.formatter import TypeScriptFormatter

        formatter = TypeScriptFormatter()

        # All outputs should follow Module.function() pattern
        results = [
            formatter.format_function_identifier("A", "b", 0),
            formatter.format_function_identifier("ClassX", "methodY", 1),
            formatter.format_function_identifier("VeryLongClassName", "shortMethod", 5),
        ]

        for result in results:
            # Should have exactly one dot
            assert result.count(".") == 1
            # Should end with ()
            assert result.endswith("()")
            # Should have module and function parts
            parts = result.replace("()", "").split(".")
            assert len(parts) == 2
