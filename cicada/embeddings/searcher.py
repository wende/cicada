"""
Embeddings searcher for semantic code search.

Wraps cicada-vector Store.search() and returns results compatible with
the existing KeywordSearcher format.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cicada_vector import Store

from cicada.embeddings.indexer import _read_embeddings_config
from cicada.utils.storage import get_embeddings_path


class EmbeddingsSearcher:
    """
    Semantic search using cicada-vector embeddings.

    Returns results in a format compatible with KeywordSearcher for
    seamless integration with the existing query pipeline.
    """

    def __init__(self, repo_path: str | Path):
        """
        Initialize the embeddings searcher.

        Args:
            repo_path: Path to the repository

        Raises:
            FileNotFoundError: If embeddings have not been indexed
        """
        self.repo_path = Path(repo_path).resolve()
        self.embeddings_path = get_embeddings_path(repo_path)

        if not self.embeddings_path.exists():
            raise FileNotFoundError(
                f"Embeddings not found at {self.embeddings_path}. "
                f"Run 'cicada index --force --embeddings' first."
            )

        # Read embeddings configuration
        config = _read_embeddings_config(self.repo_path)

        # Initialize the store for searching with same Ollama config
        self.store = Store(
            str(self.embeddings_path.parent),
            ollama_host=config["ollama_host"],
            ollama_model=config["model"],
        )

    def search(
        self,
        query: str | list[str],
        top_n: int = 20,
        filter_type: str = "all",
    ) -> list[dict[str, Any]]:
        """
        Perform semantic search and return results in KeywordSearcher format.

        Args:
            query: Search query string or list of query terms
            top_n: Maximum number of results to return
            filter_type: Type filter ("all", "modules", "functions")

        Returns:
            List of result dictionaries compatible with KeywordSearcher output
        """
        # Convert query list to string if needed
        query_str = " ".join(str(q) for q in query) if isinstance(query, list) else query

        # Perform semantic search
        raw_results = self.store.search(query_str, k=top_n * 2)  # Fetch extra for filtering

        # Convert to KeywordSearcher format
        results: list[dict[str, Any]] = []
        for doc_id, score, meta in raw_results:
            doc_type = meta.get("type", "unknown")

            # Apply type filter
            if filter_type == "modules" and doc_type != "module":
                continue
            if filter_type == "functions" and doc_type != "function":
                continue

            result = self._convert_to_search_result(doc_id, score, meta)
            results.append(result)

            if len(results) >= top_n:
                break

        return results

    def _convert_to_search_result(
        self, doc_id: str, score: float, meta: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Convert a cicada-vector result to KeywordSearcher format.

        Args:
            doc_id: Document ID from the store
            score: Similarity score (0-1)
            meta: Metadata dictionary

        Returns:
            Dictionary compatible with KeywordSearcher results
        """
        doc_type = meta.get("type", "unknown")

        result: dict[str, Any] = {
            "type": doc_type,
            "name": meta.get("name", doc_id),
            "module": meta.get("module", ""),
            "file": meta.get("file", ""),
            "line": meta.get("line", 1),
            "score": score,
            "confidence": score * 100,  # Convert to percentage
            "matched_keywords": [],  # Semantic search doesn't have explicit keywords
            "pattern_match": False,
            "semantic_match": True,  # Flag this as a semantic match
        }

        if doc_type == "function":
            result["function"] = meta.get("function", "")
            result["arity"] = meta.get("arity", 0)
            result["visibility"] = meta.get("visibility", "def")

        # Include doc if available (for display)
        doc = meta.get("doc")
        if doc:
            result["doc"] = doc

        return result


def has_embeddings(repo_path: str | Path) -> bool:
    """
    Check if embeddings exist for a repository.

    Args:
        repo_path: Path to the repository

    Returns:
        True if embeddings have been indexed
    """
    embeddings_path = get_embeddings_path(repo_path)
    return embeddings_path.exists()


class PRSearchResult:
    """Result from PR semantic search."""

    def __init__(
        self,
        pr_number: int,
        title: str,
        score: float,
        state: str = "unknown",
        author: str = "unknown",
        merged_at: str | None = None,
        created_at: str | None = None,
    ):
        self.pr_number = pr_number
        self.title = title
        self.score = score
        self.state = state
        self.author = author
        self.merged_at = merged_at
        self.created_at = created_at


def search_prs_semantically(
    repo_path: str | Path, query: str, top_n: int = 5
) -> list[PRSearchResult]:
    """
    Search PRs semantically using embeddings.

    Args:
        repo_path: Path to the repository
        query: Search query string
        top_n: Maximum number of PR results to return

    Returns:
        List of PRSearchResult objects for matching PRs
    """
    repo_path = Path(repo_path).resolve()
    embeddings_path = get_embeddings_path(repo_path)

    if not embeddings_path.exists():
        return []

    try:
        config = _read_embeddings_config(repo_path)
        store = Store(
            str(embeddings_path.parent),
            ollama_host=config["ollama_host"],
            ollama_model=config["model"],
        )

        # Search with extra results to filter for PRs only
        raw_results = store.search(query, k=top_n * 3)

        # Filter for PR results only
        pr_results: list[PRSearchResult] = []
        for _doc_id, score, meta in raw_results:
            if meta.get("type") != "pr":
                continue

            pr_results.append(
                PRSearchResult(
                    pr_number=meta.get("pr_number", 0),
                    title=meta.get("title", ""),
                    score=score,
                    state=meta.get("state", "unknown"),
                    author=meta.get("author", "unknown"),
                    merged_at=meta.get("merged_at"),
                    created_at=meta.get("created_at"),
                )
            )

            if len(pr_results) >= top_n:
                break

        return pr_results

    except Exception:
        # If anything fails, return empty list (don't break the query)
        return []
