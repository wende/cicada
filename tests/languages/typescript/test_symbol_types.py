"""Tests for TypeScript symbol type detection."""

import pytest

from cicada.languages.typescript.symbol_types import get_symbol_type, is_callable


class TestTypescriptSymbolTypes:
    """Test TypeScript symbol type detection."""

    def test_function_detection(self):
        """TypeScript functions end with . (no parens)."""
        # Top-level function
        assert get_symbol_type("src/file.ts:functionName.") == "function"
        assert get_symbol_type("packages/server/src/router.ts:lazy.") == "function"

    def test_method_detection(self):
        """TypeScript methods contain # and end with ."""
        # Class method
        assert get_symbol_type("src/file.ts:Calculator#add.") == "method"
        assert get_symbol_type("src/class.ts:MyClass#myMethod.") == "method"

    def test_class_detection(self):
        """TypeScript classes end with #."""
        assert get_symbol_type("src/file.ts:Calculator#") == "class"
        assert get_symbol_type("src/models.ts:User#") == "class"

    def test_module_detection(self):
        """TypeScript modules end with :."""
        assert get_symbol_type("src/file.ts:") == "module"
        assert get_symbol_type("packages/server/src/index.ts:") == "module"

    def test_parameter_detection(self):
        """TypeScript parameters end with .(paramName)."""
        assert get_symbol_type("src/file.ts:Calculator#add.(x)") == "parameter"
        assert get_symbol_type("src/utils.ts:helper.(data)") == "parameter"

    def test_is_callable_function(self):
        """Functions are callable."""
        assert is_callable("src/file.ts:functionName.") is True

    def test_is_callable_method(self):
        """Methods are callable."""
        assert is_callable("src/file.ts:Calculator#add.") is True

    def test_is_callable_class_not_callable(self):
        """Classes are not callable (in this context)."""
        assert is_callable("src/file.ts:Calculator#") is False

    def test_is_callable_module_not_callable(self):
        """Modules are not callable."""
        assert is_callable("src/file.ts:") is False


class TestTypescriptVsPythonSymbols:
    """Test that TypeScript symbols differ from Python symbols."""

    def test_typescript_function_no_parens(self):
        """TypeScript functions don't have ()."""
        # This would be classified as 'attribute' by Python rules
        # but should be 'function' by TypeScript rules
        assert get_symbol_type("functionName.") == "function"

    def test_typescript_method_no_parens(self):
        """TypeScript methods don't have ()."""
        # This would be classified as 'attribute' by Python rules
        # but should be 'method' by TypeScript rules
        assert get_symbol_type("ClassName#methodName.") == "method"
