"""
Parallel keyword expansion wrapper.

Provides thread-parallel keyword expansion by wrapping KeywordExpander
with ThreadPoolExecutor. Keeps parallel logic separate from core expansion.

Two modes:
1. Batch mode: Collect all tasks, expand in parallel, return results
2. Streaming mode: Submit tasks as extracted, collect results as they complete
"""

import os
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, as_completed, wait
from typing import Any

from cicada.keyword_expander import KeywordExpander


def get_default_workers() -> int:
    """Get default number of workers (CPU count, or 4 if undetectable)."""
    return os.cpu_count() or 4


class ParallelKeywordExpander:
    """Thread-parallel wrapper for KeywordExpander.

    Uses ThreadPoolExecutor to expand multiple keyword batches concurrently.
    Thread-safe for lemminflect expansion.

    Example:
        >>> expander = ParallelKeywordExpander(expansion_type="lemmi", max_workers=4)
        >>> batches = [["auth", "user"], ["db", "query"], ["cache", "redis"]]
        >>> results = expander.expand_keywords_parallel(batches)
    """

    def __init__(
        self,
        expansion_type: str = "lemmi",
        max_workers: int | None = None,
        verbose: bool = False,
    ):
        """Initialize parallel expander.

        Args:
            expansion_type: Type of expansion ("lemmi")
            max_workers: Maximum number of worker threads (default: 4)
            verbose: Whether to print progress messages
        """
        if expansion_type != "lemmi":
            raise ValueError("Only lemmi expansion is supported.")

        self.expander = KeywordExpander(expansion_type=expansion_type, verbose=verbose)
        self.max_workers = max_workers if max_workers is not None else get_default_workers()
        self.verbose = verbose

        # Set the total workers count for progress reporting
        KeywordExpander._total_workers = self.max_workers

        # No embedding model preload for lemmi expansion.

    def expand_keywords_parallel(
        self,
        keyword_batches: list[list[str]],
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Expand multiple keyword sets in parallel.

        Args:
            keyword_batches: List of keyword lists to expand
            **kwargs: Additional arguments passed to expand_keywords
                      (e.g., top_n=3, threshold=0.7)

        Returns:
            List of expansion results in the same order as input batches.
            Each result is a dict with 'words' and 'simple' keys.
        """
        if not keyword_batches:
            return []

        results: list[dict[str, Any] | None] = [None] * len(keyword_batches)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_idx = {
                executor.submit(self.expander.expand_keywords, kws, **kwargs): idx
                for idx, kws in enumerate(keyword_batches)
            }

            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                results[idx] = future.result()

        return results  # type: ignore[return-value]

    def expand_keywords_parallel_with_scores(
        self,
        tasks: list[tuple[list[str], dict[str, float]]],
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Expand multiple keyword sets with per-task scores in parallel.

        Args:
            tasks: List of (keywords, keyword_scores) tuples
            **kwargs: Additional arguments passed to expand_keywords
                      (e.g., top_n=3, threshold=0.7)

        Returns:
            List of expansion results in the same order as input tasks.
            Each result is a dict with 'words' and 'simple' keys.
        """
        if not tasks:
            return []

        results: list[dict[str, Any] | None] = [None] * len(tasks)

        def expand_with_scores(
            idx: int, keywords: list[str], keyword_scores: dict[str, float]
        ) -> tuple[int, dict[str, Any]]:
            result = self.expander.expand_keywords(
                keywords, keyword_scores=keyword_scores, **kwargs
            )
            return idx, result

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(expand_with_scores, idx, keywords, scores)
                for idx, (keywords, scores) in enumerate(tasks)
            ]

            for future in as_completed(futures):
                idx, result = future.result()
                results[idx] = result

        return results  # type: ignore[return-value]

    def expand_keywords(
        self,
        keywords: list[str],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Expand a single keyword set (delegates to underlying expander).

        Convenience method for single-batch expansion.

        Args:
            keywords: Keywords to expand
            **kwargs: Additional arguments passed to expand_keywords

        Returns:
            Dict with 'words' (list of dicts with word/score/source) and 'simple' (flat list).
        """
        return self.expander.expand_keywords(keywords, **kwargs)

    def get_expansion_info(self) -> dict[str, Any]:
        """Get information about the expansion configuration."""
        info = self.expander.get_expansion_info()
        info["parallel"] = True
        info["max_workers"] = self.max_workers
        return info

    def shutdown(self) -> None:
        """Shutdown (no-op for ThreadPoolExecutor, kept for API compatibility)."""


class StreamingExpansionPipeline:
    """Streaming pipeline for keyword expansion.

    Submits expansion tasks immediately as items are extracted, and collects
    results as they complete. Bounds memory by limiting pending tasks.

    Ready for future parallel extraction - just change the extraction loop
    to use as_completed() on extraction futures.

    Example:
        >>> with StreamingExpansionPipeline(expander, max_pending=50) as pipeline:
        ...     for item in items:
        ...         keywords, scores = extract(item)
        ...         # Submit and collect any completed results
        ...         for data, result in pipeline.submit(keywords, scores, item):
        ...             apply_result(data, result)
        ...     # Collect remaining
        ...     for data, result in pipeline.finish():
        ...         apply_result(data, result)
    """

    def __init__(
        self,
        expander: ParallelKeywordExpander,
        max_pending: int = 100,
        verbose: bool = False,
    ):
        """Initialize streaming pipeline.

        Args:
            expander: ParallelKeywordExpander instance (with pre-loaded model)
            max_pending: Maximum pending tasks before blocking (bounds memory)
            verbose: Whether to print progress messages
        """
        self.expander = expander
        self.max_pending = max_pending
        self.verbose = verbose
        self._executor: ThreadPoolExecutor | None = None
        self._pending: dict[Any, Any] = {}  # future -> callback_data
        self._submitted = 0
        self._completed = 0

    def __enter__(self) -> "StreamingExpansionPipeline":
        self._executor = ThreadPoolExecutor(max_workers=self.expander.max_workers)
        self._pending = {}
        self._submitted = 0
        self._completed = 0
        return self

    def __exit__(self, *args: Any) -> None:
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None

    def submit(
        self,
        keywords: list[str],
        scores: dict[str, float],
        callback_data: Any,
        **kwargs: Any,
    ) -> list[tuple[Any, dict[str, Any]]]:
        """Submit expansion task, return any completed results.

        Non-blocking unless queue is full (>= max_pending), then blocks
        until at least one task completes.

        Args:
            keywords: Keywords to expand
            scores: Keyword scores dict
            callback_data: Data to return with result (e.g., target dict and key)
            **kwargs: Additional args for expand_keywords (top_n, threshold)

        Returns:
            List of (callback_data, result) for any completed tasks.
        """
        if self._executor is None:
            raise RuntimeError("Pipeline not started. Use 'with' statement.")

        # Submit the task
        future = self._executor.submit(
            self.expander.expander.expand_keywords,
            keywords,
            keyword_scores=scores,
            **kwargs,
        )
        self._pending[future] = callback_data
        self._submitted += 1

        # Collect any completed results (non-blocking)
        completed = self._collect_done()

        # If at max capacity, block until one completes
        if len(self._pending) >= self.max_pending:
            done, _ = wait(self._pending.keys(), return_when=FIRST_COMPLETED)
            for f in done:
                data = self._pending.pop(f)
                self._completed += 1
                completed.append((data, f.result()))

        return completed

    def _collect_done(self) -> list[tuple[Any, dict[str, Any]]]:
        """Non-blocking: collect completed futures."""
        completed: list[tuple[Any, dict[str, Any]]] = []
        for future in list(self._pending.keys()):
            if future.done():
                data = self._pending.pop(future)
                self._completed += 1
                completed.append((data, future.result()))
        return completed

    def collect_completed(self) -> list[tuple[Any, dict[str, Any]]]:
        """Non-blocking: collect any completed results.

        Call this periodically if you want to process results
        without submitting new tasks.
        """
        return self._collect_done()

    def finish(self) -> list[tuple[Any, dict[str, Any]]]:
        """Block until all pending tasks complete.

        Returns:
            List of (callback_data, result) for all remaining tasks.
        """
        results: list[tuple[Any, dict[str, Any]]] = []
        for future in as_completed(self._pending):
            data = self._pending.pop(future)
            self._completed += 1
            results.append((data, future.result()))
        return results

    @property
    def pending_count(self) -> int:
        """Number of tasks still pending."""
        return len(self._pending)

    @property
    def stats(self) -> dict[str, int]:
        """Get pipeline statistics."""
        return {
            "submitted": self._submitted,
            "completed": self._completed,
            "pending": len(self._pending),
        }


class NoOpExpansionPipeline:
    """No-op pipeline for extraction-only mode (when expander is unavailable).

    Provides the same interface as StreamingExpansionPipeline but doesn't
    perform any expansion. Keywords are stored as-is during extraction.

    This enables graceful fallback when the keyword expander fails to
    initialize (e.g., missing embeddings), allowing search to work with
    raw extracted keywords instead of failing entirely.

    Example:
        >>> with NoOpExpansionPipeline() as pipeline:
        ...     for item in items:
        ...         keywords, scores = extract(item)
        ...         item["keywords"] = scores  # Store raw keywords
        ...         # Submit returns empty (no expansion results)
        ...         for data, result in pipeline.submit(keywords, scores, callback):
        ...             pass  # Never reached
        ...     # finish() also returns empty
        ...     for data, result in pipeline.finish():
        ...         pass
    """

    def __init__(self, verbose: bool = False):
        """Initialize no-op pipeline.

        Args:
            verbose: Whether to print progress messages
        """
        self.verbose = verbose
        self._submitted = 0

    def __enter__(self) -> "NoOpExpansionPipeline":
        self._submitted = 0
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def submit(
        self,
        keywords: list[str],
        scores: dict[str, float],
        callback_data: Any,
        **kwargs: Any,
    ) -> list[tuple[Any, dict[str, Any]]]:
        """No-op submit: just track count, return empty.

        Keywords should already be stored on the target by the caller
        before calling submit(). This method just tracks the count.

        Returns:
            Empty list (no expansion results)
        """
        self._submitted += 1
        return []

    def collect_completed(self) -> list[tuple[Any, dict[str, Any]]]:
        """No-op: return empty."""
        return []

    def finish(self) -> list[tuple[Any, dict[str, Any]]]:
        """No-op: return empty."""
        return []

    @property
    def pending_count(self) -> int:
        """Always 0 (no pending tasks)."""
        return 0

    @property
    def stats(self) -> dict[str, int]:
        """Get pipeline statistics."""
        return {
            "submitted": self._submitted,
            "completed": 0,
            "pending": 0,
        }
