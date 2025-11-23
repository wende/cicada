"""
Tests for dunder method search functionality (Bug #3).

Ensures that searching for dunder methods like __init__, __str__, etc.
works correctly by matching against function names.
"""

from cicada.keyword_search import KeywordSearcher
from cicada.scoring import calculate_score, calculate_wildcard_score


def test_dunder_method_exact_match():
    """Test that searching for __init__ matches functions with that name."""
    # Simulate a function document with __init__ as the name
    query_keywords = ["__init__"]
    keyword_groups = [0]
    total_terms = 1
    doc_keywords = {"initialize": 1.0, "args": 0.8}  # No "__init__" in keywords
    doc_name = "cicada.git.HistoryAnalyzer.__init__/3"

    result = calculate_score(
        query_keywords, keyword_groups, total_terms, doc_keywords, doc_name=doc_name
    )

    assert result["score"] == 3.0, "Should match function name with score 3.0"
    assert "__init__" in result["matched_keywords"], "Should match __init__"
    assert result["confidence"] == 100.0, "Should be 100% confident"


def test_dunder_str_exact_match():
    """Test that searching for __str__ matches functions with that name."""
    query_keywords = ["__str__"]
    keyword_groups = [0]
    total_terms = 1
    doc_keywords = {"string": 1.0, "representation": 0.8}
    doc_name = "myapp.models.User.__str__/1"

    result = calculate_score(
        query_keywords, keyword_groups, total_terms, doc_keywords, doc_name=doc_name
    )

    assert result["score"] == 3.0, "Should match function name"
    assert "__str__" in result["matched_keywords"], "Should match __str__"


def test_dunder_method_wildcard_match():
    """Test that wildcard patterns work with dunder methods."""
    query_keywords = ["__init__*"]
    keyword_groups = [0]
    total_terms = 1
    doc_keywords = {"initialize": 1.0}
    doc_name = "myapp.Base.__init__/2"

    def match_wildcard(pattern, text):
        import fnmatch

        return fnmatch.fnmatch(text.lower(), pattern.lower())

    result = calculate_wildcard_score(
        query_keywords,
        keyword_groups,
        total_terms,
        doc_keywords,
        match_wildcard,
        doc_name=doc_name,
    )

    assert result["score"] == 3.0, "Should match with wildcard"
    assert "__init__*" in result["matched_keywords"], "Should match pattern"


def test_no_match_when_names_differ():
    """Test that different dunder methods don't match."""
    query_keywords = ["__init__"]
    keyword_groups = [0]
    total_terms = 1
    doc_keywords = {"string": 1.0}
    doc_name = "myapp.User.__str__/1"

    result = calculate_score(
        query_keywords, keyword_groups, total_terms, doc_keywords, doc_name=doc_name
    )

    assert result["score"] == 0.0, "Should not match different dunder method"
    assert len(result["matched_keywords"]) == 0, "Should have no matches"


def test_module_name_not_confused_with_function_name():
    """Test that module names don't accidentally match function queries."""
    query_keywords = ["user"]
    keyword_groups = [0]
    total_terms = 1
    doc_keywords = {"database": 1.0}
    doc_name = "myapp.User.create_user/2"  # "User" in module name

    result = calculate_score(
        query_keywords, keyword_groups, total_terms, doc_keywords, doc_name=doc_name
    )

    # Should not match because we only match the simple function name (create_user)
    assert result["score"] == 0.0, "Should not match module name"


def _assert_function_search(searcher, query_keyword, expected_function, expected_score=None):
    """
    Helper to search for a function and assert expected results.

    Args:
        searcher: KeywordSearcher instance
        query_keyword: Keyword to search for
        expected_function: Expected function name in results
        expected_score: Optional expected score (if None, score check is skipped)
    """
    results = searcher.search([query_keyword], top_n=10, filter_type="functions")
    assert len(results) == 1, f"Should find {expected_function} method"
    assert results[0]["function"] == expected_function, f"Should match {expected_function}"
    if expected_score is not None:
        assert results[0]["score"] == expected_score, f"Should have score {expected_score}"


def test_keyword_search_with_dunder_methods():
    """Integration test with KeywordSearcher."""
    # Create a simple index with dunder methods
    index = {
        "modules": {
            "myapp.User": {
                "file": "myapp/user.py",
                "line": 1,
                "keywords": {"user": 1.0},
                "functions": [
                    {
                        "name": "__init__",
                        "arity": 2,
                        "line": 10,
                        "type": "def",
                        "keywords": {"initialize": 1.0, "args": 0.8},
                    },
                    {
                        "name": "__str__",
                        "arity": 1,
                        "line": 20,
                        "type": "def",
                        "keywords": {"string": 1.0, "representation": 0.8},
                    },
                    {
                        "name": "save",
                        "arity": 1,
                        "line": 30,
                        "type": "def",
                        "keywords": {"save": 1.5, "database": 1.2},
                    },
                ],
            }
        }
    }

    searcher = KeywordSearcher(index)

    # Search for dunder methods and regular function
    _assert_function_search(searcher, "__init__", "__init__", expected_score=3.0)
    _assert_function_search(searcher, "__str__", "__str__")
    _assert_function_search(searcher, "save", "save", expected_score=1.5)


def test_name_extraction_with_arity():
    """Test that arity suffix is properly removed when extracting name."""
    query_keywords = ["__init__"]
    keyword_groups = [0]
    total_terms = 1
    doc_keywords = {}
    doc_name = "myapp.User.__init__/3"

    result = calculate_score(
        query_keywords, keyword_groups, total_terms, doc_keywords, doc_name=doc_name
    )

    assert result["score"] == 3.0, "Should extract __init__ from __init__/3"


def test_name_extraction_with_dots():
    """Test that dots in module path are handled correctly."""
    query_keywords = ["__init__"]
    keyword_groups = [0]
    total_terms = 1
    doc_keywords = {}
    doc_name = "myapp.models.user.User.__init__/2"

    result = calculate_score(
        query_keywords, keyword_groups, total_terms, doc_keywords, doc_name=doc_name
    )

    assert result["score"] == 3.0, "Should extract __init__ from nested module path"
