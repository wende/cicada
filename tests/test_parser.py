"""
Unit tests for the Elixir parser.
"""

from cicada.parser import ElixirParser


def test_simple_module():
    """Test parsing a simple module with one function."""
    parser = ElixirParser()
    result = parser.parse_file("tests/fixtures/sample.ex")

    assert result is not None
    assert len(result) == 1

    module = result[0]
    assert module["module"] == "Test"
    assert module["line"] == 1
    assert len(module["functions"]) == 5


def test_function_extraction():
    """Test that functions are correctly extracted."""
    parser = ElixirParser()
    result = parser.parse_file("tests/fixtures/sample.ex")

    functions = result[0]["functions"]

    # Check hello/1
    hello = next(f for f in functions if f["name"] == "hello")
    assert hello["arity"] == 1
    assert hello["full_name"] == "hello/1"
    assert hello["type"] == "def"
    assert hello["line"] == 6

    # Check private_func/0
    private = next(f for f in functions if f["name"] == "private_func")
    assert private["arity"] == 0
    assert private["full_name"] == "private_func/0"
    assert private["type"] == "defp"
    assert private["line"] == 10

    # Check multi_arity/3
    multi = next(f for f in functions if f["name"] == "multi_arity")
    assert multi["arity"] == 3
    assert multi["full_name"] == "multi_arity/3"
    assert multi["type"] == "def"

    # Check another_private/2
    another = next(f for f in functions if f["name"] == "another_private")
    assert another["arity"] == 2
    assert another["type"] == "defp"


def test_no_params_function():
    """Test function with no parameters."""
    parser = ElixirParser()
    result = parser.parse_file("tests/fixtures/sample.ex")

    functions = result[0]["functions"]
    no_params = next(f for f in functions if f["name"] == "no_params")

    assert no_params["arity"] == 0
    assert no_params["full_name"] == "no_params/0"


def test_return_type_extraction():
    """Test that return types are extracted from @spec declarations."""
    parser = ElixirParser()
    result = parser.parse_file("tests/fixtures/test_with_docs.ex")

    assert result is not None
    module = result[0]
    functions = module["functions"]

    # Test create_user/2 has return type from @spec
    create_user = next(f for f in functions if f["name"] == "create_user")
    assert create_user["return_type"] == "{:ok, map()} | {:error, atom()}"
    assert create_user["args_with_types"][0]["name"] == "name"
    assert create_user["args_with_types"][0]["type"] == "String.t()"
    assert create_user["args_with_types"][1]["name"] == "email"
    assert create_user["args_with_types"][1]["type"] == "String.t()"

    # Test find_user/1 has return type from @spec
    find_user = next(f for f in functions if f["name"] == "find_user")
    assert find_user["return_type"] == "{:ok, map()} | {:error, :not_found}"
    assert find_user["args_with_types"][0]["name"] == "id"
    assert find_user["args_with_types"][0]["type"] == "integer()"

    # Test update_email/2 has no @spec, so no return_type
    update_email = next(f for f in functions if f["name"] == "update_email")
    assert "return_type" not in update_email


def test_guard_clause_extraction():
    """Test that guard clauses are extracted from function definitions."""
    parser = ElixirParser()
    result = parser.parse_file("tests/fixtures/test_guard_clauses.ex")

    assert result is not None
    module = result[0]
    functions = module["functions"]

    # Test abs_value/1 has two clauses - one with guard, one without
    abs_value_funcs = [f for f in functions if f["name"] == "abs_value"]
    assert len(abs_value_funcs) == 2

    # First clause should have guard "n < 0"
    first_clause = abs_value_funcs[0]
    assert first_clause["guards"] == ["n < 0"]
    assert first_clause["line"] == 13

    # Second clause should have no guards
    second_clause = abs_value_funcs[1]
    assert second_clause["guards"] == []
    assert second_clause["line"] == 14

    # Test functions without guards have empty guards list
    add_numbers = next(f for f in functions if f["name"] == "add_numbers")
    assert add_numbers["guards"] == []


if __name__ == "__main__":
    print("Running parser tests...")

    try:
        test_simple_module()
        print("✓ test_simple_module passed")

        test_function_extraction()
        print("✓ test_function_extraction passed")

        test_no_params_function()
        print("✓ test_no_params_function passed")

        test_return_type_extraction()
        print("✓ test_return_type_extraction passed")

        test_guard_clause_extraction()
        print("✓ test_guard_clause_extraction passed")

        print("\nAll tests passed!")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
