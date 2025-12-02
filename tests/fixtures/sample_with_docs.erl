%% @doc This module provides greeting utilities.
%% It demonstrates EDoc documentation format.
-module(sample_with_docs).
-export([hello/1, add/2]).

%% @doc Greets a person by name.
%% @param Name The name of the person to greet
%% @returns ok
hello(Name) ->
    io:format("Hello ~s~n", [Name]).

%% @doc Adds two numbers together.
%% This is a simple arithmetic function.
add(A, B) ->
    A + B.

%% This is a regular comment, not EDoc
private_helper() ->
    ok.
