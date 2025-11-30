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


def test_format_function_name_with_args():
    """Test formatting function name with args shows args."""
    formatter = ErlangFormatter()
    result = formatter.format_function_name("map", 2, ["List", "Fun"])
    assert result == "map(List, Fun)"


def test_format_function_name_empty_args():
    """Test formatting function name with empty args list uses arity."""
    formatter = ErlangFormatter()
    result = formatter.format_function_name("init", 0, [])
    assert result == "init/0"


def test_format_function_name_none_args():
    """Test formatting function name with None args falls back to arity."""
    formatter = ErlangFormatter()
    result = formatter.format_function_name("handle_call", 3, None)
    assert result == "handle_call/3"


def test_format_function_name_single_arg():
    """Test formatting function name with single argument."""
    formatter = ErlangFormatter()
    result = formatter.format_function_name("start_link", 1, ["Args"])
    assert result == "start_link(Args)"
