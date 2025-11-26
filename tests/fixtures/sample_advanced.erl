%% @doc Advanced Erlang module for testing pattern matching and multiple clauses.
-module(sample_advanced).
-export([factorial/1, handle_response/1, process_tuple/1]).

%% @doc Calculate factorial recursively using multiple clauses.
factorial(0) ->
    1;
factorial(N) when N > 0 ->
    N * factorial(N - 1).

%% @doc Handle different response types with pattern matching.
handle_response({ok, Value}) ->
    {success, Value};
handle_response({error, Reason}) ->
    {failure, Reason};
handle_response(undefined) ->
    {failure, no_data}.

%% @doc Process a tuple argument.
process_tuple({A, B, C}) ->
    A + B + C.

%% Private helper function (not exported)
internal_helper(X) ->
    X * 2.
