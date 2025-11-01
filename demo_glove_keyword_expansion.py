#!/usr/bin/env python
"""
Demo: Keyword Extrapolation using GloVe Word Embeddings

This demo shows how to use the glove-wiki-gigaword-100 word embeddings
to expand search keywords with semantically similar terms.

Usage:
    python demo_glove_keyword_expansion.py "authentication user"
    python demo_glove_keyword_expansion.py "database query"
"""

import sys
from typing import List, Tuple

import gensim.downloader as api


class GloVeKeywordExpander:
    """Expand query keywords using GloVe word embeddings."""

    def __init__(self, model_name: str = "glove-wiki-gigaword-100"):
        """
        Initialize the keyword expander with a GloVe model.

        Args:
            model_name: Name of the GloVe model to use
                       Default: glove-wiki-gigaword-100 (100-dimensional vectors)
        """
        print(f"Loading {model_name} embeddings...")
        print("(This may take a minute on first run - the model will be cached)")
        self.model = api.load(model_name)
        print(f"✓ Model loaded: {len(self.model)} words in vocabulary\n")

    def expand_keywords(
        self, keywords: List[str], top_n: int = 5, min_similarity: float = 0.5
    ) -> dict:
        """
        Expand keywords with semantically similar terms.

        Args:
            keywords: List of keywords to expand
            top_n: Number of similar words to find for each keyword
            min_similarity: Minimum cosine similarity threshold (0.0 to 1.0)

        Returns:
            Dictionary mapping each keyword to its similar terms with scores
        """
        results = {}

        for keyword in keywords:
            keyword_lower = keyword.lower()

            # Check if keyword is in vocabulary
            if keyword_lower not in self.model:
                results[keyword] = {
                    "in_vocab": False,
                    "similar_words": [],
                    "message": f"'{keyword}' not found in GloVe vocabulary",
                }
                continue

            # Find most similar words
            similar_words = self.model.most_similar(keyword_lower, topn=top_n)

            # Filter by minimum similarity threshold
            filtered_words = [
                (word, score) for word, score in similar_words if score >= min_similarity
            ]

            results[keyword] = {
                "in_vocab": True,
                "similar_words": filtered_words,
                "vector_norm": float(self.model[keyword_lower].sum()),
            }

        return results

    def expand_query(self, query: str, top_n: int = 3, min_similarity: float = 0.6) -> List[str]:
        """
        Expand a search query with semantically similar terms.

        Args:
            query: Space-separated search query
            top_n: Number of similar words per keyword
            min_similarity: Minimum similarity threshold

        Returns:
            Expanded list of keywords (original + similar)
        """
        keywords = query.lower().split()
        expansion_results = self.expand_keywords(keywords, top_n, min_similarity)

        expanded_keywords = set(keywords)  # Start with original keywords

        for keyword, result in expansion_results.items():
            if result["in_vocab"]:
                # Add similar words
                for similar_word, _score in result["similar_words"]:
                    expanded_keywords.add(similar_word)

        return sorted(expanded_keywords)

    def find_semantic_neighbors(
        self, word: str, positive: List[str] = None, negative: List[str] = None, top_n: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Find words semantically related to a concept defined by positive and negative examples.

        This enables queries like:
        - "database" + "search" - "sql" = NoSQL-related terms
        - "user" + "create" = user creation related terms

        Args:
            word: Primary word
            positive: Words to add to the semantic direction
            negative: Words to subtract from the semantic direction
            top_n: Number of results to return

        Returns:
            List of (word, similarity_score) tuples
        """
        positive = positive or []
        negative = negative or []

        # Combine all positive terms
        all_positive = [word.lower()] + [w.lower() for w in positive]

        # Filter out any words not in vocabulary
        valid_positive = [w for w in all_positive if w in self.model]
        valid_negative = [w.lower() for w in negative if w.lower() in self.model]

        if not valid_positive:
            return []

        try:
            results = self.model.most_similar(
                positive=valid_positive, negative=valid_negative, topn=top_n
            )
            return results
        except Exception as e:
            print(f"Error finding semantic neighbors: {e}")
            return []


def demo_basic_expansion():
    """Demonstrate basic keyword expansion."""
    print("=" * 70)
    print("DEMO 1: Basic Keyword Expansion")
    print("=" * 70)

    expander = GloVeKeywordExpander()

    # Example queries
    test_queries = [
        "authentication user",
        "database query",
        "validate input",
        "error handling",
    ]

    for query in test_queries:
        print(f"\n📝 Original query: '{query}'")
        print("-" * 70)

        keywords = query.split()
        expansion = expander.expand_keywords(keywords, top_n=5, min_similarity=0.5)

        for keyword, result in expansion.items():
            if result["in_vocab"]:
                print(f"\n  Keyword: '{keyword}'")
                print(f"  Similar terms:")
                for word, score in result["similar_words"]:
                    print(f"    • {word:<20} (similarity: {score:.3f})")
            else:
                print(f"\n  ⚠️  {result['message']}")

        # Show expanded query
        expanded = expander.expand_query(query, top_n=3, min_similarity=0.6)
        print(f"\n  🔍 Expanded search terms: {', '.join(expanded)}")


def demo_semantic_search():
    """Demonstrate semantic search with concept combinations."""
    print("\n" + "=" * 70)
    print("DEMO 2: Semantic Concept Search")
    print("=" * 70)

    expander = GloVeKeywordExpander()

    examples = [
        {
            "concept": "User registration process",
            "word": "user",
            "positive": ["create", "register"],
            "negative": [],
        },
        {
            "concept": "Data validation (not SQL)",
            "word": "validate",
            "positive": ["input", "check"],
            "negative": ["sql"],
        },
        {
            "concept": "Authentication methods",
            "word": "authentication",
            "positive": ["login", "security"],
            "negative": [],
        },
    ]

    for example in examples:
        print(f"\n📍 Concept: {example['concept']}")
        print(f"   Formula: {example['word']}", end="")
        if example["positive"]:
            print(f" + {', '.join(example['positive'])}", end="")
        if example["negative"]:
            print(f" - {', '.join(example['negative'])}", end="")
        print()
        print("-" * 70)

        neighbors = expander.find_semantic_neighbors(
            example["word"], positive=example["positive"], negative=example["negative"], top_n=8
        )

        if neighbors:
            print("  Related terms:")
            for word, score in neighbors:
                print(f"    • {word:<25} (similarity: {score:.3f})")
        else:
            print("  ⚠️  No results found")


def demo_code_search_scenario():
    """Demonstrate how this could improve code search."""
    print("\n" + "=" * 70)
    print("DEMO 3: Code Search Enhancement Scenario")
    print("=" * 70)

    expander = GloVeKeywordExpander()

    print("\n📚 Use Case: Searching for authentication-related functions")
    print("-" * 70)

    # Original query
    original_query = "authentication login"
    print(f"\n1. Developer searches for: '{original_query}'")

    # Expand with GloVe
    expanded_keywords = expander.expand_query(original_query, top_n=4, min_similarity=0.6)

    print(f"\n2. System expands query with GloVe embeddings:")
    print(f"   Original: {original_query.split()}")
    print(f"   Expanded: {expanded_keywords}")

    print(f"\n3. Benefits:")
    print(f"   ✓ Finds functions with keywords like: 'credentials', 'signin', 'verify'")
    print(f"   ✓ Catches synonyms and related terms developers might use")
    print(f"   ✓ Improves recall without sacrificing precision")

    print(f"\n4. Example matches that would be found:")
    print(f"   • verify_credentials/2")
    print(f"   • authenticate_user/1")
    print(f"   • check_login_token/1")
    print(f"   • validate_session/2")


def main():
    """Run all demonstrations."""
    if len(sys.argv) > 1:
        # Interactive mode: user provided a query
        query = " ".join(sys.argv[1:])
        print("=" * 70)
        print(f"Interactive Keyword Expansion")
        print("=" * 70)

        expander = GloVeKeywordExpander()

        print(f"\n📝 Your query: '{query}'")
        print("-" * 70)

        expanded = expander.expand_query(query, top_n=5, min_similarity=0.5)
        print(f"\n🔍 Expanded keywords: {', '.join(expanded)}")

        print("\n📊 Detailed expansion:")
        keywords = query.split()
        expansion = expander.expand_keywords(keywords, top_n=5, min_similarity=0.5)

        for keyword, result in expansion.items():
            if result["in_vocab"]:
                print(f"\n  '{keyword}' →")
                for word, score in result["similar_words"]:
                    print(f"    • {word:<20} ({score:.3f})")
            else:
                print(f"\n  ⚠️  '{keyword}': {result['message']}")

    else:
        # Demo mode: run all demonstrations
        demo_basic_expansion()
        demo_semantic_search()
        demo_code_search_scenario()

        print("\n" + "=" * 70)
        print("💡 Try it yourself!")
        print("=" * 70)
        print(f'\nRun: python {sys.argv[0]} "your search query here"\n')


if __name__ == "__main__":
    main()
