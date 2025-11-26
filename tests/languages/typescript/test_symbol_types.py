"""Tests for TypeScript symbol type detection.

Based on actual scip-typescript output, TypeScript uses:
- Functions/methods: (). suffix (e.g., `file.ts`/add().)
- Properties: . suffix (e.g., `file.ts`/Class#property.)
- Classes: # suffix (e.g., `file.ts`/Class#)
- Modules: / suffix (e.g., `file.ts`/)
"""

import pytest

from cicada.languages.typescript.symbol_types import get_symbol_type, is_callable


class TestTypescriptSymbolTypes:
    """Test TypeScript symbol type detection based on actual SCIP patterns."""

    def test_function_detection(self):
        """TypeScript functions end with (). (callables)."""
        # Top-level function
        assert get_symbol_type("`file.ts`/functionName().") == "function"
        assert get_symbol_type("`router.ts`/lazy().") == "function"

    def test_method_detection(self):
        """TypeScript methods contain # and end with ().."""
        # Class method
        assert get_symbol_type("`file.ts`/Calculator#add().") == "method"
        assert get_symbol_type("`class.ts`/MyClass#myMethod().") == "method"

    def test_class_detection(self):
        """TypeScript classes end with #."""
        assert get_symbol_type("`file.ts`/Calculator#") == "class"
        assert get_symbol_type("`models.ts`/User#") == "class"

    def test_module_detection(self):
        """TypeScript modules end with / or :."""
        assert get_symbol_type("`file.ts`/") == "module"
        assert get_symbol_type("src/file.ts:") == "module"

    def test_parameter_detection(self):
        """TypeScript parameters end with ().(paramName)."""
        assert get_symbol_type("`file.ts`/Calculator#add().(x)") == "parameter"
        assert get_symbol_type("`utils.ts`/helper().(data)") == "parameter"

    def test_property_is_not_callable(self):
        """TypeScript properties end with . (not ().) and are not callable."""
        # Property - ends with . but not ().
        assert get_symbol_type("`file.ts`/Calculator#value.") == "unknown"
        assert is_callable("`file.ts`/Calculator#value.") is False

    def test_is_callable_function(self):
        """Functions are callable."""
        assert is_callable("`file.ts`/functionName().") is True

    def test_is_callable_method(self):
        """Methods are callable."""
        assert is_callable("`file.ts`/Calculator#add().") is True

    def test_is_callable_class_not_callable(self):
        """Classes are not callable (in this context)."""
        assert is_callable("`file.ts`/Calculator#") is False

    def test_is_callable_module_not_callable(self):
        """Modules are not callable."""
        assert is_callable("`file.ts`/") is False


class TestTypescriptVsPythonSymbols:
    """Test TypeScript symbol patterns vs Python patterns.

    Note: Both TypeScript and Python use (). for callables in SCIP.
    The main difference is path format (TypeScript uses backticks and /).
    """

    def test_typescript_function_with_parens(self):
        """TypeScript functions use (). like Python."""
        assert get_symbol_type("`functionName`().") == "function"

    def test_typescript_method_with_parens(self):
        """TypeScript methods use (). like Python."""
        assert get_symbol_type("`ClassName`#methodName().") == "method"
