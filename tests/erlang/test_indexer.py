"""Tests for Erlang indexer with keyword extraction."""

import json
import tempfile
from pathlib import Path

from cicada.languages.erlang.indexer import ErlangIndexer


def test_indexer_basic():
    """Test basic indexing without keyword extraction."""
    indexer = ErlangIndexer()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a simple Erlang file
        src_dir = Path(tmpdir) / "src"
        src_dir.mkdir()

        erl_file = src_dir / "test_module.erl"
        erl_file.write_text(
            """
-module(test_module).
-export([hello/1]).

hello(Name) ->
    io:format("Hello ~s~n", [Name]).
"""
        )

        output_path = Path(tmpdir) / "index.json"
        result = indexer.index_repository(tmpdir, output_path)

        assert result["success"] is True
        assert result["modules_count"] == 1
        assert result["functions_count"] == 1

        with open(output_path) as f:
            data = json.load(f)

        assert "test_module" in data["modules"]
        assert data["modules"]["test_module"]["functions"][0]["name"] == "hello"


def test_indexer_with_docs():
    """Test indexing with EDoc documentation."""
    indexer = ErlangIndexer()

    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = Path(tmpdir) / "src"
        src_dir.mkdir()

        erl_file = src_dir / "greeting.erl"
        erl_file.write_text(
            """
%% @doc A module for greeting users.
-module(greeting).
-export([greet/1]).

%% @doc Greets a user by their name.
greet(Name) ->
    io:format("Hello ~s~n", [Name]).
"""
        )

        output_path = Path(tmpdir) / "index.json"
        result = indexer.index_repository(tmpdir, output_path)

        assert result["success"] is True

        with open(output_path) as f:
            data = json.load(f)

        module = data["modules"]["greeting"]
        assert module["moduledoc"] == "A module for greeting users."
        assert module["functions"][0]["doc"] == "Greets a user by their name."


def test_indexer_keyword_extraction():
    """Test that keywords are extracted from docs."""
    indexer = ErlangIndexer()

    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = Path(tmpdir) / "src"
        src_dir.mkdir()

        erl_file = src_dir / "auth_handler.erl"
        erl_file.write_text(
            """
%% @doc Authentication handler for user login.
-module(auth_handler).
-export([authenticate/2, validate_token/1]).

%% @doc Authenticate a user with username and password.
authenticate(Username, Password) ->
    ok.

%% @doc Validate an authentication token.
validate_token(Token) ->
    ok.
"""
        )

        output_path = Path(tmpdir) / "index.json"
        result = indexer.index_repository(tmpdir, output_path)

        assert result["success"] is True

        with open(output_path) as f:
            data = json.load(f)

        keywords = data["modules"]["auth_handler"]["keywords"]

        # Module name parts should be keywords
        assert "auth" in keywords
        assert "handler" in keywords

        # Function name parts should be keywords
        assert "authenticate" in keywords
        assert "validate" in keywords
        assert "token" in keywords


def test_indexer_verbose_output(capsys):
    """Test verbose output during indexing."""
    indexer = ErlangIndexer()

    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = Path(tmpdir) / "src"
        src_dir.mkdir()

        erl_file = src_dir / "mymod.erl"
        erl_file.write_text(
            """
-module(mymod).
-export([foo/0]).
foo() -> ok.
"""
        )

        output_path = Path(tmpdir) / "index.json"
        indexer.index_repository(tmpdir, output_path, verbose=True)

        captured = capsys.readouterr()
        assert "Indexed 1 Erlang modules" in captured.out


def test_indexer_empty_repo():
    """Test indexing an empty repository (no Erlang files)."""
    indexer = ErlangIndexer()

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "index.json"
        result = indexer.index_repository(tmpdir, output_path)

        assert result["success"] is True
        assert result["modules_count"] == 0
        assert result["files_indexed"] == 0


def test_indexer_header_files():
    """Test that .hrl header files are indexed."""
    indexer = ErlangIndexer()

    with tempfile.TemporaryDirectory() as tmpdir:
        include_dir = Path(tmpdir) / "include"
        include_dir.mkdir()

        hrl_file = include_dir / "records.hrl"
        hrl_file.write_text(
            """
-record(user, {name, email}).
"""
        )

        output_path = Path(tmpdir) / "index.json"
        result = indexer.index_repository(tmpdir, output_path)

        # Header files are scanned but may not produce modules
        # (records aren't module declarations)
        assert result["success"] is True
        assert result["files_indexed"] == 1
