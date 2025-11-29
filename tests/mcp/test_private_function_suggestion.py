"""
Test private function suggestion in search_function.

Tests the refactored methods:
- _build_private_pattern_string
- _has_matching_private_function
- _suggest_private_function

Coverage target: lines 521-534, 546-553, 575-578
"""

import pytest

from cicada.mcp.handlers.function_handlers import FunctionSearchHandler


@pytest.mark.asyncio
async def test_private_function_suggestion_comprehensive():
    """
    Test private function suggestion with wildcard patterns.

    This single test covers:
    1. _build_private_pattern_string - with module, without module, with arity
    2. _has_matching_private_function - successful match
    3. _suggest_private_function - full orchestration

    Scenario: Search for public "create*" functions finds nothing,
    but private "_create*" functions exist, triggering suggestion.
    """
    index = {
        "metadata": {
            "language": "elixir",
            "repo_path": "/tmp/test",
        },
        "modules": {
            "MyApp.User": {
                "name": "MyApp.User",
                "file": "lib/my_app/user.ex",
                "line": 1,
                "moduledoc": "User module",
                "aliases": {},
                "functions": [
                    # Private function that should trigger suggestion
                    {
                        "name": "_create_user",
                        "arity": 2,
                        "line": 10,
                        "type": "defp",
                        "doc": "Internal user creation",
                        "dependencies": [],
                    },
                    # Another private function with wildcard match
                    {
                        "name": "_create_account",
                        "arity": 1,
                        "line": 20,
                        "type": "defp",
                        "doc": "Internal account creation",
                        "dependencies": [],
                    },
                    # Public function that doesn't match "create*"
                    {
                        "name": "update_user",
                        "arity": 2,
                        "line": 30,
                        "type": "def",
                        "doc": "Update user",
                        "dependencies": [],
                    },
                ],
            },
            "MyApp.Auth": {
                "name": "MyApp.Auth",
                "file": "lib/my_app/auth.ex",
                "line": 1,
                "moduledoc": "Auth module",
                "aliases": {},
                "functions": [
                    # Private function with module pattern match
                    {
                        "name": "_create_session",
                        "arity": 1,
                        "line": 5,
                        "type": "defp",
                        "doc": "Internal session creation",
                        "dependencies": [],
                    },
                ],
            },
            "*.Context.User": {
                "name": "MyApp.Context.User",
                "file": "lib/my_app/context/user.ex",
                "line": 1,
                "moduledoc": "User context",
                "aliases": {},
                "functions": [
                    # Private function with *.module pattern
                    {
                        "name": "_create_record",
                        "arity": 3,
                        "line": 15,
                        "type": "defp",
                        "doc": "Internal record creation",
                        "dependencies": [],
                    },
                ],
            },
        },
    }

    config = {"repository": {"path": "/tmp/test"}}
    handler = FunctionSearchHandler(index, config)

    # Test case 1: Simple wildcard pattern (no module)
    # Should find: _create* pattern
    result = await handler.search_function(
        function_name="create*",
        output_format="markdown",
        what_calls_it=False,
    )

    # Should return text content
    assert len(result) == 1
    text = result[0].text

    # No public functions found, but should suggest private version (compact format)
    assert "Not found:" in text
    assert "_create*" in text  # Suggestion for private pattern
    assert "(private)" in text  # Indicates it's a private function suggestion

    # Test case 2: Module-qualified pattern
    # Should find: MyApp.User._create* pattern
    result = await handler.search_function(
        function_name="User.create*",
        output_format="markdown",
        what_calls_it=False,
    )

    text = result[0].text
    assert "_create*" in text  # Suggestion should appear

    # Test case 3: Pattern with arity
    # Should find: _create*/2 pattern
    result = await handler.search_function(
        function_name="create*/2",
        output_format="markdown",
        what_calls_it=False,
    )

    text = result[0].text
    assert "_create*/2" in text  # Suggestion with arity

    # Test case 4: *.Module pattern (wildcard prefix)
    # Should strip *. prefix and suggest: Context.User._create*
    result = await handler.search_function(
        function_name="*.Context.User.create*",
        output_format="markdown",
        what_calls_it=False,
    )

    text = result[0].text
    # Should suggest private pattern for nested module
    assert "_create*" in text

    # Test case 5: No suggestion when public functions exist
    # Should NOT suggest private pattern
    result = await handler.search_function(
        function_name="update*",
        output_format="markdown",
        what_calls_it=False,
    )

    text = result[0].text
    # Should find the public update_user function, no suggestion needed
    assert "update_user" in text
    # When results are found, private suggestion section shouldn't appear
    assert "Did you mean private functions?" not in text

    # Test case 6: No suggestion when no private matches exist
    # Should NOT suggest private pattern
    result = await handler.search_function(
        function_name="delete*",
        output_format="markdown",
        what_calls_it=False,
    )

    text = result[0].text
    # Should find nothing and not suggest _delete* (doesn't exist)
    assert "_delete*" not in text
    # Generic suggestions appear, but not private function specific ones
    assert "Did you mean private functions?" not in text

    # Test case 7: No suggestion for non-wildcard patterns
    # Only wildcard patterns trigger private function suggestion
    result = await handler.search_function(
        function_name="create_user",  # No wildcard
        output_format="markdown",
        what_calls_it=False,
    )

    text = result[0].text
    # Non-wildcard patterns don't trigger suggestion logic (no * in pattern)
    # So no private suggestion should appear
    assert "Did you mean private functions?" not in text


@pytest.mark.asyncio
async def test_private_function_suggestion_respects_file_scope():
    """
    Test that private function suggestions respect file-scoped patterns.

    Bug: Searching lib/foo.ex:create* suggests _create* even when private
    functions only exist in other files like lib/bar.ex.

    Expected: Suggestions should only appear when private functions exist
    within the same file scope.
    """
    index = {
        "metadata": {
            "language": "elixir",
            "repo_path": "/tmp/test",
        },
        "modules": {
            "MyApp.Foo": {
                "name": "MyApp.Foo",
                "file": "lib/foo.ex",
                "line": 1,
                "moduledoc": "Foo module",
                "aliases": {},
                "functions": [
                    # No private create* functions in this file
                    {
                        "name": "update_foo",
                        "arity": 1,
                        "line": 10,
                        "type": "def",
                        "doc": "Update foo",
                        "dependencies": [],
                    },
                ],
            },
            "MyApp.Bar": {
                "name": "MyApp.Bar",
                "file": "lib/bar.ex",
                "line": 1,
                "moduledoc": "Bar module",
                "aliases": {},
                "functions": [
                    # Private create* function in a DIFFERENT file
                    {
                        "name": "_create_bar",
                        "arity": 1,
                        "line": 5,
                        "type": "defp",
                        "doc": "Internal bar creation",
                        "dependencies": [],
                    },
                ],
            },
        },
    }

    config = {"repository": {"path": "/tmp/test"}}
    handler = FunctionSearchHandler(index, config)

    # Search for create* functions in lib/foo.ex specifically
    result = await handler.search_function(
        function_name="lib/foo.ex:create*",
        output_format="markdown",
        what_calls_it=False,
    )

    text = result[0].text

    # Should NOT suggest private functions because:
    # - No _create* functions exist in lib/foo.ex
    # - The _create_bar function is in lib/bar.ex (different file)
    assert "(private)" not in text  # No private suggestion
    assert "_create*" not in text

    # Now test the opposite: file with private functions
    result = await handler.search_function(
        function_name="lib/bar.ex:create*",
        output_format="markdown",
        what_calls_it=False,
    )

    text = result[0].text

    # SHOULD suggest private functions because _create_bar exists in lib/bar.ex
    assert "(private)" in text  # Has private suggestion (compact format)
    assert "lib/bar.ex:_create*" in text  # Suggestion should preserve file scope
