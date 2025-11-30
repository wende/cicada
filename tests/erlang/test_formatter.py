"""Tests for Erlang formatter."""

from cicada.languages.erlang.formatter import ErlangFormatter


def test_format_function_identifier():
    """Test Erlang module:func/arity notation."""
    formatter = ErlangFormatter()

    # Standard case
    assert formatter.format_function_identifier("lists", "map", 2) == "lists:map/2"

    # Zero arity
    assert formatter.format_function_identifier("mymod", "init", 0) == "mymod:init/0"

    # Underscored names
    assert formatter.format_function_identifier("my_module", "my_func", 3) == "my_module:my_func/3"
