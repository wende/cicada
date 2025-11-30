"""Tests for Python string extractor."""

import pytest

from cicada.languages.python.string_extractor import PythonStringExtractor


class TestPythonStringExtractor:
    """Test suite for PythonStringExtractor."""

    @pytest.fixture
    def extractor(self):
        """Create a PythonStringExtractor with default settings."""
        return PythonStringExtractor()

    @pytest.fixture
    def extractor_min_5(self):
        """Create a PythonStringExtractor with min_length=5."""
        return PythonStringExtractor(min_length=5)

    # Tests for initialization

    def test_init_default_min_length(self):
        """Test default min_length is 3."""
        extractor = PythonStringExtractor()
        assert extractor.min_length == 3

    def test_init_custom_min_length(self):
        """Test custom min_length is set correctly."""
        extractor = PythonStringExtractor(min_length=10)
        assert extractor.min_length == 10

    # Tests for extract_from_source

    def test_extract_from_source_basic_strings(self, extractor):
        """Test extracting basic string literals."""
        code = """
x = "hello world"
y = 'another string'
"""
        result = extractor.extract_from_source(code)
        assert len(result) == 2
        assert any(s["string"] == "hello world" for s in result)
        assert any(s["string"] == "another string" for s in result)

    def test_extract_from_source_syntax_error(self, extractor):
        """Test that syntax errors return empty list."""
        code = "def broken("
        result = extractor.extract_from_source(code)
        assert result == []

    def test_extract_from_source_empty_code(self, extractor):
        """Test extracting from empty source code."""
        result = extractor.extract_from_source("")
        assert result == []

    def test_extract_from_source_no_strings(self, extractor):
        """Test extracting when code has no strings."""
        code = """
x = 42
y = [1, 2, 3]
z = x + y[0]
"""
        result = extractor.extract_from_source(code)
        assert result == []

    # Tests for docstring filtering

    def test_skips_module_docstring(self, extractor):
        """Test that module docstrings are skipped."""
        code = '''
"""This is a module docstring."""

x = "this should be extracted"
'''
        result = extractor.extract_from_source(code)
        assert len(result) == 1
        assert result[0]["string"] == "this should be extracted"
        assert not any(s["string"] == "This is a module docstring." for s in result)

    def test_skips_class_docstring(self, extractor):
        """Test that class docstrings are skipped."""
        code = '''
class MyClass:
    """This is a class docstring."""

    x = "class variable string"
'''
        result = extractor.extract_from_source(code)
        assert len(result) == 1
        assert result[0]["string"] == "class variable string"
        assert not any("class docstring" in s["string"] for s in result)

    def test_skips_function_docstring(self, extractor):
        """Test that function docstrings are skipped."""
        code = '''
def my_function():
    """This is a function docstring."""
    return "actual string"
'''
        result = extractor.extract_from_source(code)
        assert len(result) == 1
        assert result[0]["string"] == "actual string"
        assert not any("function docstring" in s["string"] for s in result)

    def test_skips_async_function_docstring(self, extractor):
        """Test that async function docstrings are skipped."""
        code = '''
async def async_function():
    """This is an async function docstring."""
    return "actual string"
'''
        result = extractor.extract_from_source(code)
        assert len(result) == 1
        assert result[0]["string"] == "actual string"
        assert not any("async function docstring" in s["string"] for s in result)

    def test_skips_all_docstrings_combined(self, extractor):
        """Test that all types of docstrings are skipped."""
        code = '''
"""Module docstring."""

class MyClass:
    """Class docstring."""

    def method(self):
        """Method docstring."""
        x = "method string"

async def async_func():
    """Async docstring."""
    y = "async string"

z = "module level string"
'''
        result = extractor.extract_from_source(code)
        extracted_strings = [s["string"] for s in result]
        assert "method string" in extracted_strings
        assert "async string" in extracted_strings
        assert "module level string" in extracted_strings
        assert "Module docstring." not in extracted_strings
        assert "Class docstring." not in extracted_strings
        assert "Method docstring." not in extracted_strings
        assert "Async docstring." not in extracted_strings

    # Tests for string filtering

    def test_filters_short_strings(self, extractor):
        """Test that strings shorter than min_length are filtered."""
        code = """
a = "ab"
b = "abc"
c = "abcd"
"""
        result = extractor.extract_from_source(code)
        extracted_strings = [s["string"] for s in result]
        assert "ab" not in extracted_strings  # Length 2, below min_length 3
        assert "abc" in extracted_strings  # Length 3, equals min_length
        assert "abcd" in extracted_strings  # Length 4, above min_length

    def test_filters_whitespace_only_strings(self, extractor):
        """Test that whitespace-only strings are filtered."""
        code = """
a = "   "
b = "\\t\\n"
c = "  actual  "
"""
        result = extractor.extract_from_source(code)
        extracted_strings = [s["string"] for s in result]
        assert "   " not in extracted_strings
        assert "\t\n" not in extracted_strings
        assert "  actual  " in extracted_strings

    def test_extracts_strings_at_min_length(self, extractor_min_5):
        """Test that strings exactly at min_length are extracted."""
        code = """
a = "1234"
b = "12345"
c = "123456"
"""
        result = extractor_min_5.extract_from_source(code)
        extracted_strings = [s["string"] for s in result]
        assert "1234" not in extracted_strings  # Length 4, below min_length 5
        assert "12345" in extracted_strings  # Length 5, equals min_length
        assert "123456" in extracted_strings  # Length 6, above min_length

    def test_filters_empty_strings(self, extractor):
        """Test that empty strings are filtered."""
        code = """
a = ""
b = "not empty"
"""
        result = extractor.extract_from_source(code)
        assert len(result) == 1
        assert result[0]["string"] == "not empty"

    # Tests for f-string extraction

    def test_extracts_fstring_static_parts(self, extractor):
        """Test extracting static parts from f-strings."""
        code = """
name = "Alice"
x = f"Hello {name}"
"""
        result = extractor.extract_from_source(code)
        # Should extract "Alice" and "Hello " (static part of f-string)
        extracted_strings = [s["string"] for s in result]
        assert "Alice" in extracted_strings
        assert "Hello " in extracted_strings

    def test_extracts_fstring_combined_parts(self, extractor):
        """Test extracting combined static parts from f-strings."""
        code = """
x = 42
s = f"Value is {x} and more text"
"""
        result = extractor.extract_from_source(code)
        # Should extract "Value is " + " and more text" = "Value is  and more text"
        extracted_strings = [s["string"] for s in result]
        combined = "Value is  and more text"
        assert combined in extracted_strings

    def test_skips_fstring_only_dynamic(self, extractor):
        """Test that f-strings with only dynamic parts are skipped."""
        code = """
x = 42
s = f"{x}"
"""
        result = extractor.extract_from_source(code)
        # Should only extract regular strings, not f-string without static parts
        extracted_strings = [s["string"] for s in result]
        # The f-string has no static parts, so it shouldn't be in results
        assert len(extracted_strings) == 0

    def test_fstring_min_length_filtering(self, extractor):
        """Test that f-string static parts respect min_length."""
        code = """
x = 42
short = f"Hi {x}"
long = f"Hello {x}"
"""
        result = extractor.extract_from_source(code)
        extracted_strings = [s["string"] for s in result]
        # "Hi " is length 3, should be included
        # "Hello " is length 6, should be included
        assert "Hi " in extracted_strings
        assert "Hello " in extracted_strings

    def test_fstring_whitespace_filtering(self, extractor):
        """Test that f-string static parts with only whitespace are filtered."""
        code = """
x = 42
s = f"  {x}  "
"""
        result = extractor.extract_from_source(code)
        # The combined static parts "  " + "  " = "    " is whitespace only
        # Should be filtered
        extracted_strings = [s["string"] for s in result]
        assert "    " not in extracted_strings

    # Tests for function context tracking

    def test_tracks_function_context(self, extractor):
        """Test that function context is tracked correctly."""
        code = """
def my_function():
    x = "inside function"
"""
        result = extractor.extract_from_source(code)
        assert len(result) == 1
        assert result[0]["string"] == "inside function"
        assert result[0]["function"] == "my_function"

    def test_tracks_nested_function_context(self, extractor):
        """Test that nested function context is tracked."""
        code = """
def outer():
    x = "in outer"

    def inner():
        y = "in inner"

    z = "back in outer"
"""
        result = extractor.extract_from_source(code)
        assert len(result) == 3

        # Find each string and check its function context
        in_outer_results = [s for s in result if s["string"] == "in outer"]
        in_inner_results = [s for s in result if s["string"] == "in inner"]
        back_in_outer_results = [s for s in result if s["string"] == "back in outer"]

        assert len(in_outer_results) == 1
        assert in_outer_results[0]["function"] == "outer"

        assert len(in_inner_results) == 1
        assert in_inner_results[0]["function"] == "inner"

        assert len(back_in_outer_results) == 1
        assert back_in_outer_results[0]["function"] == "outer"

    def test_module_level_strings_no_function(self, extractor):
        """Test that module-level strings have no function context."""
        code = """
x = "module level"

def my_function():
    y = "in function"
"""
        result = extractor.extract_from_source(code)
        assert len(result) == 2

        module_level = [s for s in result if s["string"] == "module level"]
        in_function = [s for s in result if s["string"] == "in function"]

        assert len(module_level) == 1
        assert module_level[0]["function"] is None

        assert len(in_function) == 1
        assert in_function[0]["function"] == "my_function"

    def test_class_method_context(self, extractor):
        """Test function context in class methods."""
        code = """
class MyClass:
    def method(self):
        x = "in method"

    def another_method(self):
        y = "in another"
"""
        result = extractor.extract_from_source(code)
        assert len(result) == 2

        in_method = [s for s in result if s["string"] == "in method"]
        in_another = [s for s in result if s["string"] == "in another"]

        assert len(in_method) == 1
        assert in_method[0]["function"] == "method"

        assert len(in_another) == 1
        assert in_another[0]["function"] == "another_method"

    # Tests for line numbers

    def test_line_numbers_are_correct(self, extractor):
        """Test that line numbers are accurate."""
        code = """x = "line 1"

y = "line 3"


z = "line 6"
"""
        result = extractor.extract_from_source(code)
        assert len(result) == 3

        line_1 = [s for s in result if s["string"] == "line 1"]
        line_3 = [s for s in result if s["string"] == "line 3"]
        line_6 = [s for s in result if s["string"] == "line 6"]

        assert line_1[0]["line"] == 1
        assert line_3[0]["line"] == 3
        assert line_6[0]["line"] == 6

    def test_multiline_string_line_number(self, extractor):
        """Test line number for multiline strings."""
        code = '''x = """This is
a multiline
string"""
'''
        result = extractor.extract_from_source(code)
        # Should report the line where the string starts
        assert len(result) == 1
        assert result[0]["line"] == 1

    # Tests for async functions

    def test_async_function_strings(self, extractor):
        """Test extracting strings from async functions."""
        code = """
async def fetch_data():
    url = "https://api.example.com"
    return url
"""
        result = extractor.extract_from_source(code)
        assert len(result) == 1
        assert result[0]["string"] == "https://api.example.com"
        assert result[0]["function"] == "fetch_data"

    def test_async_function_docstring_skipped(self, extractor):
        """Test that async function docstrings are properly skipped."""
        code = '''
async def fetch_data():
    """Fetch data from API."""
    url = "https://api.example.com"
    return url
'''
        result = extractor.extract_from_source(code)
        assert len(result) == 1
        assert result[0]["string"] == "https://api.example.com"
        assert not any("Fetch data from API" in s["string"] for s in result)

    # Integration tests

    def test_real_world_python_code(self, extractor):
        """Test extracting from realistic Python code."""
        code = '''
"""
User authentication module.
"""

import hashlib


class UserAuth:
    """Handle user authentication."""

    def __init__(self, db):
        self.db = db
        self.salt = "random_salt_value"

    def authenticate(self, username, password):
        """Authenticate a user."""
        query = "SELECT * FROM users WHERE username = ?"
        user = self.db.execute(query, (username,))

        if not user:
            return False

        hashed = hashlib.sha256(password.encode()).hexdigest()
        return user.password_hash == hashed

    async def async_auth(self, token):
        """Async authentication."""
        api_url = f"https://auth.example.com/verify/{token}"
        return await self._verify(api_url)

    async def _verify(self, url):
        return True


def helper():
    msg = "Helper function"
    return msg
'''
        result = extractor.extract_from_source(code)

        extracted_strings = [s["string"] for s in result]

        # Should extract actual strings
        assert "random_salt_value" in extracted_strings
        assert "SELECT * FROM users WHERE username = ?" in extracted_strings
        assert "https://auth.example.com/verify/" in extracted_strings  # f-string static part
        assert "Helper function" in extracted_strings

        # Should NOT extract docstrings
        assert "User authentication module." not in extracted_strings
        assert "Handle user authentication." not in extracted_strings
        assert "Authenticate a user." not in extracted_strings
        assert "Async authentication." not in extracted_strings

        # Check function context
        salt_result = [s for s in result if s["string"] == "random_salt_value"][0]
        assert salt_result["function"] == "__init__"

        query_result = [
            s for s in result if s["string"] == "SELECT * FROM users WHERE username = ?"
        ][0]
        assert query_result["function"] == "authenticate"

        helper_result = [s for s in result if s["string"] == "Helper function"][0]
        assert helper_result["function"] == "helper"

    def test_complex_nesting_and_strings(self, extractor):
        """Test complex nesting scenarios."""
        code = """
class Outer:
    x = "outer class"

    def method(self):
        y = "outer method"

        class Inner:
            z = "inner class"

            def inner_method(self):
                w = "inner method"

        return Inner()
"""
        result = extractor.extract_from_source(code)
        extracted = {s["string"]: s["function"] for s in result}

        assert "outer class" in extracted
        assert "outer method" in extracted
        assert extracted["outer method"] == "method"
        assert "inner class" in extracted
        assert "inner method" in extracted
        assert extracted["inner method"] == "inner_method"

    def test_strings_in_comprehensions(self, extractor):
        """Test extracting strings from list/dict comprehensions."""
        code = """
def process():
    items = ["keep this", "and this"]
    result = [f"Item: {x}" for x in items]
    return result
"""
        result = extractor.extract_from_source(code)
        extracted_strings = [s["string"] for s in result]

        assert "keep this" in extracted_strings
        assert "and this" in extracted_strings
        assert "Item: " in extracted_strings  # f-string static part

    def test_strings_in_lambda(self, extractor):
        """Test extracting strings from lambda expressions."""
        code = """
def create_processor():
    processor = lambda x: f"Processed: {x}"
    return processor
"""
        result = extractor.extract_from_source(code)
        extracted_strings = [s["string"] for s in result]

        # F-string static part should be extracted
        assert "Processed: " in extracted_strings
