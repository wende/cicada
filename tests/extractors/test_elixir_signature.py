"""Tests for Elixir function signature extractor."""

import pytest

from cicada.extractors.elixir_signature import (
    ElixirSignatureExtractor,
    ELIXIR_FUNCTION_PATTERN,
    ELIXIR_MODULE_PATTERN,
)
from cicada.extractors.base_signature import SignatureExtractorRegistry


class TestElixirSignatureExtractor:
    """Test suite for ElixirSignatureExtractor."""

    @pytest.fixture
    def extractor(self):
        """Create an ElixirSignatureExtractor instance."""
        return ElixirSignatureExtractor()

    def test_get_file_extensions(self, extractor):
        """Test get_file_extensions returns correct extensions."""
        extensions = extractor.get_file_extensions()
        assert ".ex" in extensions
        assert ".exs" in extensions
        assert len(extensions) == 2
        assert isinstance(extensions, list)

    # Tests for extract_module_name

    def test_extract_module_name_basic(self, extractor):
        """Test extracting basic module name."""
        content = """
defmodule MyApp.User do
  def create(name), do: {:ok, name}
end
"""
        result = extractor.extract_module_name(content, "lib/my_app/user.ex")
        assert result == "MyApp.User"

    def test_extract_module_name_nested(self, extractor):
        """Test extracting deeply nested module name."""
        content = """
defmodule MyApp.Auth.Providers.OAuth do
  def authenticate(token), do: {:ok, token}
end
"""
        result = extractor.extract_module_name(content, "lib/my_app/auth/providers/oauth.ex")
        assert result == "MyApp.Auth.Providers.OAuth"

    def test_extract_module_name_single_word(self, extractor):
        """Test extracting single-word module name."""
        content = """
defmodule User do
  def test(), do: :ok
end
"""
        result = extractor.extract_module_name(content, "lib/user.ex")
        assert result == "User"

    def test_extract_module_name_not_found(self, extractor):
        """Test module name extraction returns None when not found."""
        content = """
def standalone_function(arg) do
  arg
end
"""
        result = extractor.extract_module_name(content, "lib/helpers.ex")
        assert result is None

    def test_extract_module_name_empty_content(self, extractor):
        """Test module name extraction with empty content."""
        result = extractor.extract_module_name("", "lib/user.ex")
        assert result is None

    def test_extract_module_name_invalid_format(self, extractor):
        """Test module name extraction with malformed defmodule."""
        content = "defmodule"
        result = extractor.extract_module_name(content, "lib/user.ex")
        assert result is None

    def test_extract_module_name_with_underscores(self, extractor):
        """Test extracting module name with underscores."""
        content = """
defmodule My_App.User_Manager do
  def test(), do: :ok
end
"""
        result = extractor.extract_module_name(content, "lib/user.ex")
        assert result == "My_App.User_Manager"

    # Tests for extract_function_signatures

    def test_extract_function_signatures_basic(self, extractor):
        """Test extracting basic function signatures."""
        content = """
defmodule MyApp.User do
  def create() do
    :ok
  end

  def update(id, params) do
    {:ok, id}
  end
end
"""
        signatures = extractor.extract_function_signatures(content, "MyApp.User")
        assert "MyApp.User.create/0" in signatures
        assert "MyApp.User.update/2" in signatures

    def test_extract_function_signatures_private_defp(self, extractor):
        """Test extracting private function signatures (defp)."""
        content = """
defmodule MyApp.User do
  def public_method(arg) do
    private_method(arg)
  end

  defp private_method(arg) do
    arg
  end
end
"""
        signatures = extractor.extract_function_signatures(content, "MyApp.User")
        assert "MyApp.User.public_method/1" in signatures
        assert "MyApp.User.private_method/1" in signatures

    def test_extract_function_signatures_with_question_mark(self, extractor):
        """Test extracting function signatures with question mark."""
        content = """
defmodule MyApp.User do
  def admin?(user) do
    user.role == :admin
  end

  def active?(user) do
    user.active
  end
end
"""
        signatures = extractor.extract_function_signatures(content, "MyApp.User")
        assert "MyApp.User.admin?/1" in signatures
        assert "MyApp.User.active?/1" in signatures

    def test_extract_function_signatures_with_exclamation(self, extractor):
        """Test extracting function signatures with exclamation mark."""
        content = """
defmodule MyApp.User do
  def save!(user) do
    # Save or raise
    user
  end

  def delete!(id) do
    # Delete or raise
    id
  end
end
"""
        signatures = extractor.extract_function_signatures(content, "MyApp.User")
        assert "MyApp.User.save!/1" in signatures
        assert "MyApp.User.delete!/1" in signatures

    def test_extract_function_signatures_invalid_module_name(self, extractor):
        """Test that invalid module names return empty set."""
        content = """
def some_function(arg) do
  arg
end
"""
        # Module name starting with lowercase is invalid
        signatures = extractor.extract_function_signatures(content, "invalidModule")
        assert signatures == set()

    def test_extract_function_signatures_empty_module(self, extractor):
        """Test that empty module name returns empty set."""
        content = """
def some_function() do
  :ok
end
"""
        signatures = extractor.extract_function_signatures(content, "")
        assert signatures == set()

    def test_extract_function_signatures_none_module(self, extractor):
        """Test that None module name returns empty set."""
        content = """
def some_function() do
  :ok
end
"""
        signatures = extractor.extract_function_signatures(content, None)
        assert signatures == set()

    def test_extract_function_signatures_lowercase_module_rejected(self, extractor):
        """Test that lowercase module names are rejected."""
        content = """
def some_function(arg) do
  arg
end
"""
        signatures = extractor.extract_function_signatures(content, "lowercase")
        assert signatures == set()

    def test_extract_function_signatures_uppercase_function_rejected(self, extractor):
        """Test that uppercase function names are rejected (Elixir convention)."""
        # Note: The regex won't match uppercase function names anyway
        content = """
defmodule MyApp do
  def UpperCase() do
    :ok
  end
end
"""
        signatures = extractor.extract_function_signatures(content, "MyApp")
        # Uppercase function names don't match the pattern [a-z_]
        assert "MyApp.UpperCase/0" not in signatures

    def test_extract_function_signatures_with_underscores(self, extractor):
        """Test extracting function signatures with underscores."""
        content = """
defmodule MyApp.User do
  def create_user(name, email) do
    {:ok, %{name: name, email: email}}
  end

  def _internal_helper(arg) do
    arg
  end
end
"""
        signatures = extractor.extract_function_signatures(content, "MyApp.User")
        assert "MyApp.User.create_user/2" in signatures
        # Note: Functions starting with underscore are filtered out by islower() check
        # This is current behavior - only functions starting with lowercase letters are included
        assert "MyApp.User._internal_helper/1" not in signatures

    def test_extract_function_signatures_multiple_clauses(self, extractor):
        """Test extracting function signatures with multiple clauses."""
        content = """
defmodule MyApp.Math do
  def factorial(0), do: 1
  def factorial(n), do: n * factorial(n - 1)

  def fibonacci(0), do: 0
  def fibonacci(1), do: 1
  def fibonacci(n), do: fibonacci(n - 1) + fibonacci(n - 2)
end
"""
        signatures = extractor.extract_function_signatures(content, "MyApp.Math")
        # Each clause is matched separately, but we use a set so duplicates are removed
        assert "MyApp.Math.factorial/1" in signatures
        assert "MyApp.Math.fibonacci/1" in signatures

    def test_extract_function_signatures_with_guards(self, extractor):
        """Test extracting function signatures with guards."""
        content = """
defmodule MyApp.Math do
  def divide(a, b) when b != 0 do
    a / b
  end

  def safe_divide(a, b) when is_number(a) and is_number(b) do
    a / b
  end
end
"""
        # Guards are not captured in the parameter regex, so they don't affect arity
        signatures = extractor.extract_function_signatures(content, "MyApp.Math")
        assert "MyApp.Math.divide/2" in signatures
        assert "MyApp.Math.safe_divide/2" in signatures

    # Tests for _calculate_arity

    def test_calculate_arity_no_params(self, extractor):
        """Test arity calculation with no parameters."""
        arity = extractor._calculate_arity("")
        assert arity == 0

    def test_calculate_arity_whitespace_only(self, extractor):
        """Test arity calculation with whitespace only."""
        arity = extractor._calculate_arity("   ")
        assert arity == 0

    def test_calculate_arity_single_param(self, extractor):
        """Test arity calculation with single parameter."""
        arity = extractor._calculate_arity("arg")
        assert arity == 1

    def test_calculate_arity_multiple_params(self, extractor):
        """Test arity calculation with multiple parameters."""
        arity = extractor._calculate_arity("a, b, c")
        assert arity == 3

    def test_calculate_arity_whitespace_handling(self, extractor):
        """Test arity calculation handles whitespace correctly."""
        arity = extractor._calculate_arity("a , b , c")
        assert arity == 3

        arity = extractor._calculate_arity("a,b,c")
        assert arity == 3

    def test_calculate_arity_with_defaults(self, extractor):
        """Test arity calculation with default values."""
        # Elixir default syntax: arg \\ default
        arity = extractor._calculate_arity("a, b \\\\ 10")
        assert arity == 2

    def test_calculate_arity_pattern_matching(self, extractor):
        """Test arity calculation with pattern matching."""
        # Pattern matching in params: {a, b}, [h | t], etc.
        # Note: Simple comma-split counts commas inside braces/brackets
        arity = extractor._calculate_arity("{a, b}, c")
        assert arity == 3  # Splits on all commas: {a, b}, c

        arity = extractor._calculate_arity("[h | t]")
        assert arity == 1  # No commas, just one parameter

    def test_calculate_arity_complex_patterns(self, extractor):
        """Test arity calculation with complex parameter patterns."""
        # Map patterns
        arity = extractor._calculate_arity("%{id: id}, opts")
        assert arity == 2

        # Struct patterns
        arity = extractor._calculate_arity("%User{name: name}, %Config{}")
        assert arity == 2

    # Tests for registry

    def test_registry_registration(self):
        """Test that ElixirSignatureExtractor is registered."""
        extractor = SignatureExtractorRegistry.get("elixir")
        assert extractor is not None
        assert isinstance(extractor, ElixirSignatureExtractor)

    def test_get_from_registry_returns_same_type(self):
        """Test that registry returns consistent instances."""
        extractor1 = SignatureExtractorRegistry.get("elixir")
        extractor2 = SignatureExtractorRegistry.get("elixir")
        assert type(extractor1) == type(extractor2)

    # Integration tests

    def test_extract_from_real_elixir_file(self, extractor):
        """Test extracting signatures from realistic Elixir code."""
        content = """
defmodule MyApp.Auth.UserManager do
  @moduledoc \"\"\"
  Manages user authentication and authorization.
  \"\"\"

  alias MyApp.Repo
  alias MyApp.User

  def create_user(attrs) do
    %User{}
    |> User.changeset(attrs)
    |> Repo.insert()
  end

  def authenticate(email, password) do
    with %User{} = user <- get_by_email(email),
         true <- valid_password?(user, password) do
      {:ok, user}
    else
      _ -> {:error, :invalid_credentials}
    end
  end

  def admin?(user) do
    user.role == :admin
  end

  def update!(user, attrs) do
    user
    |> User.changeset(attrs)
    |> Repo.update!()
  end

  defp get_by_email(email) do
    Repo.get_by(User, email: email)
  end

  defp valid_password?(%User{password_hash: hash}, password) do
    Bcrypt.verify_pass(password, hash)
  end
end
"""
        module_name = extractor.extract_module_name(content, "lib/my_app/auth/user_manager.ex")
        assert module_name == "MyApp.Auth.UserManager"

        signatures = extractor.extract_function_signatures(content, module_name)

        # Public functions
        assert "MyApp.Auth.UserManager.create_user/1" in signatures
        assert "MyApp.Auth.UserManager.authenticate/2" in signatures
        assert "MyApp.Auth.UserManager.admin?/1" in signatures
        assert "MyApp.Auth.UserManager.update!/2" in signatures

        # Private functions
        assert "MyApp.Auth.UserManager.get_by_email/1" in signatures
        assert "MyApp.Auth.UserManager.valid_password?/2" in signatures

    def test_handles_pattern_matching_in_params(self, extractor):
        """Test handling pattern matching in function parameters."""
        content = """
defmodule MyApp.List do
  def sum([]), do: 0
  def sum([h | t]), do: h + sum(t)

  def process({:ok, value}), do: value
  def process({:error, _}), do: nil

  def handle_response(%{status: 200, body: body}), do: {:ok, body}
  def handle_response(%{status: status}), do: {:error, status}
end
"""
        signatures = extractor.extract_function_signatures(content, "MyApp.List")

        assert "MyApp.List.sum/1" in signatures
        # Note: {:ok, value} and {:error, _} have commas, so arity is counted as 2
        # This is a limitation of simple comma-split arity calculation
        assert "MyApp.List.process/2" in signatures
        # %{status: 200, body: body} has commas, counted as 2 params
        # %{status: status} has no comma, counted as 1 param
        # Multiple clauses with different arities are all captured
        assert "MyApp.List.handle_response/1" in signatures
        assert "MyApp.List.handle_response/2" in signatures


class TestElixirRegexPatterns:
    """Test regex patterns used for parsing."""

    def test_function_pattern_basic_def(self):
        """Test ELIXIR_FUNCTION_PATTERN matches basic def."""
        match = ELIXIR_FUNCTION_PATTERN.search("def test()")
        assert match is not None
        assert match.group(1) == "test"
        assert match.group(2) == ""

    def test_function_pattern_defp(self):
        """Test ELIXIR_FUNCTION_PATTERN matches defp."""
        match = ELIXIR_FUNCTION_PATTERN.search("defp private_test(arg)")
        assert match is not None
        assert match.group(1) == "private_test"
        assert match.group(2) == "arg"

    def test_function_pattern_with_params(self):
        """Test ELIXIR_FUNCTION_PATTERN matches functions with parameters."""
        match = ELIXIR_FUNCTION_PATTERN.search("def test(a, b, c)")
        assert match is not None
        assert match.group(1) == "test"
        assert match.group(2) == "a, b, c"

    def test_function_pattern_with_question_mark(self):
        """Test ELIXIR_FUNCTION_PATTERN matches functions with ?."""
        match = ELIXIR_FUNCTION_PATTERN.search("def active?(user)")
        assert match is not None
        assert match.group(1) == "active?"

    def test_function_pattern_with_exclamation(self):
        """Test ELIXIR_FUNCTION_PATTERN matches functions with !."""
        match = ELIXIR_FUNCTION_PATTERN.search("def save!(record)")
        assert match is not None
        assert match.group(1) == "save!"

    def test_function_pattern_indented(self):
        """Test ELIXIR_FUNCTION_PATTERN matches indented functions."""
        match = ELIXIR_FUNCTION_PATTERN.search("  def method(self)")
        assert match is not None
        assert match.group(1) == "method"

    def test_function_pattern_with_guard(self):
        """Test ELIXIR_FUNCTION_PATTERN matches functions with guards."""
        # The pattern only captures up to the closing paren
        match = ELIXIR_FUNCTION_PATTERN.search("def divide(a, b) when b != 0")
        assert match is not None
        assert match.group(1) == "divide"
        assert match.group(2) == "a, b"

    def test_module_pattern_basic(self):
        """Test ELIXIR_MODULE_PATTERN matches basic modules."""
        match = ELIXIR_MODULE_PATTERN.search("defmodule MyModule do")
        assert match is not None
        assert match.group(1) == "MyModule"

    def test_module_pattern_nested(self):
        """Test ELIXIR_MODULE_PATTERN matches nested modules."""
        match = ELIXIR_MODULE_PATTERN.search("defmodule MyApp.Auth.User do")
        assert match is not None
        assert match.group(1) == "MyApp.Auth.User"

    def test_module_pattern_with_underscores(self):
        """Test ELIXIR_MODULE_PATTERN matches modules with underscores."""
        match = ELIXIR_MODULE_PATTERN.search("defmodule My_App.User_Manager do")
        assert match is not None
        assert match.group(1) == "My_App.User_Manager"

    def test_module_pattern_requires_capital(self):
        """Test ELIXIR_MODULE_PATTERN requires capitalized module names."""
        match = ELIXIR_MODULE_PATTERN.search("defmodule myModule do")
        assert match is None  # lowercase first letter should not match

    def test_module_pattern_with_newline(self):
        """Test ELIXIR_MODULE_PATTERN handles newlines."""
        match = ELIXIR_MODULE_PATTERN.search("defmodule MyModule do\n  def test()")
        assert match is not None
        assert match.group(1) == "MyModule"
