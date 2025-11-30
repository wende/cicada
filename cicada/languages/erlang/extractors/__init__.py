"""Erlang extraction utilities."""

from cicada.languages.erlang.extractors.doc import (
    extract_docs_from_comments,
    match_docs_to_declarations,
)

__all__ = ["extract_docs_from_comments", "match_docs_to_declarations"]
