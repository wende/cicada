"""Tests for Python symbol type detection."""

import pytest

from cicada.languages.python.symbol_types import get_symbol_type, is_callable


class TestPythonSymbolTypes:
    """Test Python symbol type detection."""

    def test_function_detection(self):
        """Python functions end with ()."""
        assert get_symbol_type("calculator/helper_function().") == "function"
        assert get_symbol_type("module/process_data().") == "function"

    def test_method_detection(self):
        """Python methods contain # and end with ()."""
        assert get_symbol_type("calculator/Calculator#add().") == "method"
        assert get_symbol_type("models/User#save().") == "method"

    def test_class_detection(self):
        """Python classes end with #."""
        assert get_symbol_type("calculator/Calculator#") == "class"
        assert get_symbol_type("models/User#") == "class"

    def test_module_detection(self):
        """Python modules end with :."""
        assert get_symbol_type("calculator/__init__:") == "module"
        assert get_symbol_type("package/module:") == "module"

    def test_parameter_detection(self):
        """Python parameters end with .(paramName)."""
        assert get_symbol_type("calculator/Calculator#add().(x)") == "parameter"
        assert get_symbol_type("utils/helper().(data)") == "parameter"

    def test_attribute_detection(self):
        """Python attributes end with . but not ()."""
        assert get_symbol_type("calculator/Calculator#value.") == "attribute"
        assert get_symbol_type("models/User#name.") == "attribute"

    def test_is_callable_function(self):
        """Functions are callable."""
        assert is_callable("calculator/helper_function().") is True

    def test_is_callable_method(self):
        """Methods are callable."""
        assert is_callable("calculator/Calculator#add().") is True

    def test_is_callable_attribute_not_callable(self):
        """Attributes are not callable."""
        assert is_callable("calculator/Calculator#value.") is False

    def test_is_callable_class_not_callable(self):
        """Classes are not callable (in this context)."""
        assert is_callable("calculator/Calculator#") is False
