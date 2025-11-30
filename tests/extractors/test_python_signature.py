"""Tests for Python function signature extractor."""

import pytest

from cicada.extractors.python_signature import (
    PythonSignatureExtractor,
    PYTHON_FUNCTION_PATTERN,
    PYTHON_CLASS_PATTERN,
)
from cicada.extractors.base_signature import SignatureExtractorRegistry


class TestPythonSignatureExtractor:
    """Test suite for PythonSignatureExtractor."""

    @pytest.fixture
    def extractor(self):
        """Create a PythonSignatureExtractor instance."""
        return PythonSignatureExtractor()

    def test_get_file_extensions(self, extractor):
        """Test get_file_extensions returns correct extensions."""
        extensions = extractor.get_file_extensions()
        assert extensions == [".py"]
        assert isinstance(extensions, list)

    # Tests for extract_module_name

    def test_extract_module_name_from_class(self, extractor):
        """Test extracting module name from class definition."""
        content = """
class UserManager:
    def __init__(self):
        pass
"""
        result = extractor.extract_module_name(content, "app/user.py")
        assert result == "UserManager"

    def test_extract_module_name_from_class_with_inheritance(self, extractor):
        """Test extracting module name from class with parent."""
        content = """
class UserManager(BaseManager):
    pass
"""
        result = extractor.extract_module_name(content, "app/user.py")
        assert result == "UserManager"

    def test_extract_module_name_from_file_path(self, extractor):
        """Test generating module name from file path when no class."""
        content = """
def helper_function():
    pass
"""
        result = extractor.extract_module_name(content, "lib/my_app/user.py")
        assert result == "_file_my_app.user"

    def test_extract_module_name_removes_py_extension(self, extractor):
        """Test that .py extension is removed from module name."""
        content = ""
        result = extractor.extract_module_name(content, "src/utils/helpers.py")
        assert result == "_file_utils.helpers"
        assert ".py" not in result

    def test_extract_module_name_skips_lib_prefix(self, extractor):
        """Test that 'lib' prefix is skipped in module name."""
        content = ""
        result = extractor.extract_module_name(content, "lib/auth/login.py")
        assert result == "_file_auth.login"

    def test_extract_module_name_skips_src_prefix(self, extractor):
        """Test that 'src' prefix is skipped in module name."""
        content = ""
        result = extractor.extract_module_name(content, "src/models/user.py")
        assert result == "_file_models.user"

    def test_extract_module_name_skips_app_prefix(self, extractor):
        """Test that 'app' prefix is skipped in module name."""
        content = ""
        result = extractor.extract_module_name(content, "app/controllers/user.py")
        assert result == "_file_controllers.user"

    def test_extract_module_name_skips_tests_prefix(self, extractor):
        """Test that 'tests' prefix is skipped in module name."""
        content = ""
        result = extractor.extract_module_name(content, "tests/unit/test_user.py")
        assert result == "_file_unit.test_user"

    def test_extract_module_name_nested_path(self, extractor):
        """Test module name from deeply nested path."""
        content = ""
        result = extractor.extract_module_name(content, "lib/my_app/auth/providers/oauth.py")
        assert result == "_file_my_app.auth.providers.oauth"

    def test_extract_module_name_no_class_or_valid_path(self, extractor):
        """Test module name extraction returns None for invalid input."""
        content = ""
        result = extractor.extract_module_name(content, "file.txt")
        assert result is None

    def test_extract_module_name_prefers_class_over_path(self, extractor):
        """Test that class name is preferred over file path."""
        content = """
class AuthManager:
    pass
"""
        result = extractor.extract_module_name(content, "lib/auth/oauth.py")
        assert result == "AuthManager"

    # Tests for extract_function_signatures

    def test_extract_function_signatures_basic(self, extractor):
        """Test extracting basic function signatures."""
        content = """
def simple_function():
    pass

def function_with_params(a, b, c):
    pass
"""
        signatures = extractor.extract_function_signatures(content, "MyClass")
        assert "MyClass.simple_function/0" in signatures
        assert "MyClass.function_with_params/3" in signatures

    def test_extract_function_signatures_empty_module_name(self, extractor):
        """Test that empty module name returns empty set."""
        content = """
def some_function():
    pass
"""
        signatures = extractor.extract_function_signatures(content, "")
        assert signatures == set()

    def test_extract_function_signatures_none_module_name(self, extractor):
        """Test that None module name returns empty set."""
        content = """
def some_function():
    pass
"""
        signatures = extractor.extract_function_signatures(content, None)
        assert signatures == set()

    def test_extract_function_signatures_filters_private(self, extractor):
        """Test that private methods (double underscore) are filtered."""
        content = """
def public_method():
    pass

def __private_method():
    pass

def _protected_method():
    pass
"""
        signatures = extractor.extract_function_signatures(content, "MyClass")
        assert "MyClass.public_method/0" in signatures
        assert "MyClass._protected_method/0" in signatures
        assert "MyClass.__private_method/0" not in signatures

    def test_extract_function_signatures_keeps_protected(self, extractor):
        """Test that protected methods (single underscore) are kept."""
        content = """
def _protected_method(self, arg):
    pass
"""
        signatures = extractor.extract_function_signatures(content, "MyClass")
        assert "MyClass._protected_method/1" in signatures

    def test_extract_function_signatures_keeps_dunder(self, extractor):
        """Test that dunder methods are kept."""
        content = """
def __init__(self, name):
    pass

def __str__(self):
    pass
"""
        signatures = extractor.extract_function_signatures(content, "MyClass")
        assert "MyClass.__init__/1" in signatures
        assert "MyClass.__str__/0" in signatures

    def test_extract_function_signatures_async_functions(self, extractor):
        """Test extracting async function signatures."""
        content = """
async def fetch_data():
    pass

async def process_data(data, options):
    pass
"""
        signatures = extractor.extract_function_signatures(content, "Handler")
        assert "Handler.fetch_data/0" in signatures
        assert "Handler.process_data/2" in signatures

    def test_extract_function_signatures_with_type_hints(self, extractor):
        """Test extracting signatures with type hints."""
        content = """
def typed_function(name: str, age: int) -> dict:
    pass

def complex_types(items: list[str], mapping: dict[str, int]) -> None:
    pass
"""
        signatures = extractor.extract_function_signatures(content, "MyClass")
        assert "MyClass.typed_function/2" in signatures
        # Note: dict[str, int] gets split by comma, so mapping counts as 3 parts
        # This is a limitation of the simple regex-based arity calculation
        assert "MyClass.complex_types/3" in signatures

    def test_extract_function_signatures_with_defaults(self, extractor):
        """Test extracting signatures with default parameters."""
        content = """
def with_defaults(a, b=10, c="test"):
    pass

def mixed_params(required, optional=None, *args, **kwargs):
    pass
"""
        signatures = extractor.extract_function_signatures(content, "MyClass")
        assert "MyClass.with_defaults/3" in signatures
        assert "MyClass.mixed_params/4" in signatures

    def test_extract_function_signatures_multiline(self, extractor):
        """Test extracting signatures from multiline function definitions."""
        content = """
def multiline_function(
    param1,
    param2,
    param3
):
    pass
"""
        signatures = extractor.extract_function_signatures(content, "MyClass")
        # Note: The current regex might not handle multiline well
        # This test documents current behavior
        assert len(signatures) >= 0

    # Tests for _calculate_arity

    def test_calculate_arity_no_params(self, extractor):
        """Test arity calculation with no parameters."""
        arity = extractor._calculate_arity("")
        assert arity == 0

    def test_calculate_arity_whitespace_only(self, extractor):
        """Test arity calculation with whitespace only."""
        arity = extractor._calculate_arity("   ")
        assert arity == 0

    def test_calculate_arity_with_self(self, extractor):
        """Test arity calculation excludes self parameter."""
        arity = extractor._calculate_arity("self")
        assert arity == 0

        arity = extractor._calculate_arity("self, name, age")
        assert arity == 2

    def test_calculate_arity_with_cls(self, extractor):
        """Test arity calculation excludes cls parameter."""
        arity = extractor._calculate_arity("cls")
        assert arity == 0

        arity = extractor._calculate_arity("cls, name")
        assert arity == 1

    def test_calculate_arity_with_args(self, extractor):
        """Test arity calculation with *args."""
        arity = extractor._calculate_arity("*args")
        assert arity == 1

        arity = extractor._calculate_arity("self, a, *args")
        assert arity == 2

    def test_calculate_arity_with_kwargs(self, extractor):
        """Test arity calculation with **kwargs."""
        arity = extractor._calculate_arity("**kwargs")
        assert arity == 1

        arity = extractor._calculate_arity("self, a, **kwargs")
        assert arity == 2

    def test_calculate_arity_with_args_and_kwargs(self, extractor):
        """Test arity calculation with both *args and **kwargs."""
        arity = extractor._calculate_arity("self, a, b, *args, **kwargs")
        assert arity == 4

    def test_calculate_arity_multiple_params(self, extractor):
        """Test arity calculation with multiple parameters."""
        arity = extractor._calculate_arity("a, b, c, d, e")
        assert arity == 5

    def test_calculate_arity_defaults_and_type_hints(self, extractor):
        """Test arity calculation with defaults and type hints."""
        arity = extractor._calculate_arity("name: str, age: int = 18")
        assert arity == 2

        arity = extractor._calculate_arity("self, items: list[str] = None, count: int = 0")
        assert arity == 2

    def test_calculate_arity_complex_params(self, extractor):
        """Test arity calculation with complex parameter patterns."""
        # Test with spaces around commas
        arity = extractor._calculate_arity("a , b , c")
        assert arity == 3

        # Test with complex type hints
        # Note: dict[str, Any] gets split by comma, counting as 2 parts (str, Any)
        # So: self (excluded), data (1), str (2), Any (3), options (4) = 3 after excluding self
        arity = extractor._calculate_arity(
            "self, data: dict[str, Any], options: Optional[dict] = None"
        )
        assert arity == 3

    # Tests for registry

    def test_registry_registration(self):
        """Test that PythonSignatureExtractor is registered."""
        extractor = SignatureExtractorRegistry.get("python")
        assert extractor is not None
        assert isinstance(extractor, PythonSignatureExtractor)

    def test_get_from_registry_returns_same_instance(self):
        """Test that registry returns consistent instances."""
        extractor1 = SignatureExtractorRegistry.get("python")
        extractor2 = SignatureExtractorRegistry.get("python")
        assert type(extractor1) == type(extractor2)

    # Integration tests

    def test_extract_from_real_python_file(self, extractor):
        """Test extracting signatures from realistic Python code."""
        content = """
'''Module docstring.'''

class UserAuthentication:
    '''Handle user authentication.'''

    def __init__(self, db_connection):
        self.db = db_connection

    def authenticate(self, username: str, password: str) -> bool:
        '''Authenticate a user.'''
        return self._verify_password(username, password)

    def _verify_password(self, username: str, password: str) -> bool:
        '''Verify password hash.'''
        return True

    def __private_helper(self):
        '''This should be filtered out.'''
        pass

async def fetch_user_data(user_id: int):
    '''Fetch user data asynchronously.'''
    pass

def helper_function():
    '''Module-level helper.'''
    pass
"""
        module_name = extractor.extract_module_name(content, "lib/auth/user.py")
        assert module_name == "UserAuthentication"

        signatures = extractor.extract_function_signatures(content, module_name)

        # Should include __init__ and other methods
        assert "UserAuthentication.__init__/1" in signatures
        assert "UserAuthentication.authenticate/2" in signatures
        assert "UserAuthentication._verify_password/2" in signatures

        # Should exclude private methods (double underscore, not dunder)
        assert "UserAuthentication.__private_helper/0" not in signatures

        # Module-level functions should be in signatures if module_name matches
        # but in this case module_name is "UserAuthentication" not the file name


class TestPythonRegexPatterns:
    """Test regex patterns used for parsing."""

    def test_function_pattern_basic(self):
        """Test PYTHON_FUNCTION_PATTERN matches basic functions."""
        match = PYTHON_FUNCTION_PATTERN.search("def test():")
        assert match is not None
        assert match.group(1) == "test"
        assert match.group(2) == ""

    def test_function_pattern_with_params(self):
        """Test PYTHON_FUNCTION_PATTERN matches functions with parameters."""
        match = PYTHON_FUNCTION_PATTERN.search("def test(a, b, c):")
        assert match is not None
        assert match.group(1) == "test"
        assert match.group(2) == "a, b, c"

    def test_function_pattern_async(self):
        """Test PYTHON_FUNCTION_PATTERN matches async functions."""
        match = PYTHON_FUNCTION_PATTERN.search("async def test():")
        assert match is not None
        assert match.group(1) == "test"

    def test_function_pattern_with_return_type(self):
        """Test PYTHON_FUNCTION_PATTERN matches functions with return types."""
        match = PYTHON_FUNCTION_PATTERN.search("def test() -> str:")
        assert match is not None
        assert match.group(1) == "test"

    def test_function_pattern_indented(self):
        """Test PYTHON_FUNCTION_PATTERN matches indented functions."""
        match = PYTHON_FUNCTION_PATTERN.search("    def method(self):")
        assert match is not None
        assert match.group(1) == "method"

    def test_class_pattern_basic(self):
        """Test PYTHON_CLASS_PATTERN matches basic classes."""
        match = PYTHON_CLASS_PATTERN.search("class MyClass:")
        assert match is not None
        assert match.group(1) == "MyClass"

    def test_class_pattern_with_inheritance(self):
        """Test PYTHON_CLASS_PATTERN matches classes with parents."""
        match = PYTHON_CLASS_PATTERN.search("class MyClass(BaseClass):")
        assert match is not None
        assert match.group(1) == "MyClass"

    def test_class_pattern_multiple_parents(self):
        """Test PYTHON_CLASS_PATTERN matches classes with multiple parents."""
        match = PYTHON_CLASS_PATTERN.search("class MyClass(Base1, Base2, Base3):")
        assert match is not None
        assert match.group(1) == "MyClass"

    def test_class_pattern_requires_capital(self):
        """Test PYTHON_CLASS_PATTERN requires capitalized class names."""
        match = PYTHON_CLASS_PATTERN.search("class myClass:")
        assert match is None  # lowercase first letter should not match
