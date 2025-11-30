-module(sample).
-export([hello/1, add/2]).

hello(Name) ->
    io:format("Hello ~s~n", [Name]).

add(A, B) ->
    A + B.
