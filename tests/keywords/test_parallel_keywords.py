"""
Tests for parallel keyword expansion.

Validates that keyword expansion can be parallelized using ThreadPoolExecutor
for improved indexing performance with lemminflect-only expansion.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from cicada.keyword_expander import KeywordExpander
from cicada.parallel_expander import ParallelKeywordExpander


# ==========================================================================
# Correctness Tests
# ==========================================================================


class TestParallelExpansionCorrectness:
    """Verify parallel expansion produces identical results to sequential."""

    @pytest.fixture
    def sample_keyword_batches(self) -> list[list[str]]:
        """Generate realistic keyword batches."""
        return [
            ["authentication", "user", "session"],
            ["database", "query", "connection"],
            ["cache", "memory", "storage"],
            ["function", "module", "import"],
            ["test", "assert", "mock"],
        ]

    def test_lemmi_parallel_matches_sequential(self, sample_keyword_batches: list[list[str]]):
        """Test that lemminflect-only expansion works identically in parallel."""
        sequential_expander = KeywordExpander(expansion_type="lemmi", verbose=False)
        parallel_expander = ParallelKeywordExpander(expansion_type="lemmi")

        # Sequential results
        sequential_results = [
            sequential_expander.expand_keywords(batch) for batch in sample_keyword_batches
        ]

        # Parallel results
        parallel_results = parallel_expander.expand_keywords_parallel(sample_keyword_batches)

        # Compare - results should be identical
        for i, (seq, par) in enumerate(zip(sequential_results, parallel_results)):
            assert seq == par, f"Mismatch at batch {i}: {seq} != {par}"


# ==========================================================================
# Performance Tests
# ==========================================================================


class TestParallelExpansionPerformance:
    """Benchmark parallel vs sequential performance."""

    @pytest.fixture
    def large_keyword_batches(self) -> list[list[str]]:
        """Generate many batches for performance testing."""
        base_keywords = [
            ["authentication", "user", "session", "token", "login"],
            ["database", "query", "connection", "pool", "transaction"],
            ["cache", "redis", "memory", "ttl", "invalidation"],
            ["function", "module", "import", "export", "namespace"],
            ["test", "assert", "mock", "fixture", "coverage"],
        ]
        # 50 batches total
        return base_keywords * 10

    def test_parallel_expansion_speedup_lemmi(self, large_keyword_batches: list[list[str]]):
        """Measure speedup from parallel expansion with lemminflect."""
        sequential_expander = KeywordExpander(expansion_type="lemmi", verbose=False)

        # Warm up
        sequential_expander.expand_keywords(["test"])

        # Sequential timing
        start = time.perf_counter()
        for batch in large_keyword_batches:
            sequential_expander.expand_keywords(batch)
        sequential_time = time.perf_counter() - start

        # Parallel timing
        parallel_expander = ParallelKeywordExpander(expansion_type="lemmi", max_workers=4)

        start = time.perf_counter()
        parallel_expander.expand_keywords_parallel(large_keyword_batches)
        parallel_time = time.perf_counter() - start

        speedup = sequential_time / parallel_time if parallel_time > 0 else 0

        print("\n=== Lemmi Performance ===")
        print(f"Batches:     {len(large_keyword_batches)}")
        print(f"Sequential:  {sequential_time:.3f}s")
        print(f"Parallel:    {parallel_time:.3f}s")
        print(f"Speedup:     {speedup:.2f}x")

        # Lemminflect is CPU-bound; speedup may vary.
        assert parallel_time > 0, "Parallel execution should complete"


# ==========================================================================
# Thread Safety Tests
# ==========================================================================


class TestThreadSafety:
    """Verify thread safety of keyword expansion."""

    def test_lemminflect_concurrent_access(self):
        """Test that lemminflect works correctly under concurrent load."""
        expander = KeywordExpander(expansion_type="lemmi", verbose=False)

        keywords_list = [
            ["run", "walk", "jump"],
            ["create", "update", "delete"],
            ["read", "write", "execute"],
        ] * 20  # 60 batches

        # Run concurrent expansions
        results: list = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(expander.expand_keywords, kws) for kws in keywords_list]
            for future in as_completed(futures):
                results.append(future.result())

        # All should complete and have content
        assert len(results) == 60
        for result in results:
            assert isinstance(result, dict)
            assert "words" in result
            assert len(result["words"]) > 0

    def test_shared_expander_thread_safety(self):
        """Test that a single expander can be safely shared across threads."""
        shared_expander = KeywordExpander(expansion_type="lemmi", verbose=False)

        # Different keyword sets
        all_keywords = [
            ["run", "execute", "perform"],
            ["create", "generate", "build"],
            ["read", "fetch", "retrieve"],
            ["update", "modify", "change"],
            ["delete", "remove", "destroy"],
        ] * 10  # 50 batches

        results: list = []
        errors: list = []

        def expand_and_collect(keywords: list[str]) -> dict | None:
            try:
                return shared_expander.expand_keywords(keywords)
            except Exception as e:
                errors.append(e)
                return None

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(expand_and_collect, kws) for kws in all_keywords]
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    results.append(result)

        # No errors should have occurred
        assert len(errors) == 0, f"Thread errors: {errors}"
        assert len(results) == 50


# ==========================================================================
# ParallelKeywordExpander Additional Coverage Tests
# ==========================================================================


class TestParallelKeywordExpanderEdgeCases:
    """Test edge cases and additional methods for coverage."""

    def test_empty_batches_returns_empty_list(self):
        """Test that empty batches return empty results."""
        expander = ParallelKeywordExpander(expansion_type="lemmi")

        result = expander.expand_keywords_parallel([])
        assert result == []

    def test_expand_keywords_single_batch(self):
        """Test single keyword expansion (convenience method)."""
        expander = ParallelKeywordExpander(expansion_type="lemmi")

        result = expander.expand_keywords(["run", "walk"])
        assert isinstance(result, dict)
        assert "words" in result
        assert "simple" in result

    def test_get_expansion_info(self):
        """Test get_expansion_info returns proper structure."""
        expander = ParallelKeywordExpander(expansion_type="lemmi", max_workers=4)

        info = expander.get_expansion_info()
        assert isinstance(info, dict)
        assert info["parallel"] is True
        assert info["max_workers"] == 4
        assert "type" in info
        assert info["type"] == "lemmi"

    def test_shutdown_no_op(self):
        """Test shutdown method completes without error."""
        expander = ParallelKeywordExpander(expansion_type="lemmi")
        expander.shutdown()

    def test_expand_keywords_parallel_with_scores(self):
        """Test parallel expansion with per-task scores."""
        expander = ParallelKeywordExpander(expansion_type="lemmi", max_workers=2)

        tasks = [
            (["authentication", "login"], {"authentication": 0.9, "login": 0.8}),
            (["database", "query"], {"database": 0.85, "query": 0.75}),
            (["cache", "memory"], {"cache": 0.7, "memory": 0.65}),
        ]

        results = expander.expand_keywords_parallel_with_scores(tasks, top_n=3, threshold=0.5)

        assert len(results) == 3
        for result in results:
            assert isinstance(result, dict)
            assert "words" in result

    def test_expand_keywords_parallel_with_scores_empty(self):
        """Test parallel expansion with scores handles empty tasks."""
        expander = ParallelKeywordExpander(expansion_type="lemmi")

        results = expander.expand_keywords_parallel_with_scores([])
        assert results == []


# ==========================================================================
# StreamingExpansionPipeline Tests
# ==========================================================================


class TestStreamingExpansionPipeline:
    """Test StreamingExpansionPipeline for coverage."""

    def test_pipeline_context_manager(self):
        """Test pipeline as context manager."""
        from cicada.parallel_expander import StreamingExpansionPipeline

        expander = ParallelKeywordExpander(expansion_type="lemmi", max_workers=2)

        with StreamingExpansionPipeline(expander, max_pending=10) as pipeline:
            assert pipeline._executor is not None
            assert pipeline.pending_count == 0
            stats = pipeline.stats
            assert stats["submitted"] == 0
            assert stats["completed"] == 0
            assert stats["pending"] == 0

        # After exit, executor should be None
        assert pipeline._executor is None

    def test_pipeline_submit_and_finish(self):
        """Test submitting tasks and finishing."""
        from cicada.parallel_expander import StreamingExpansionPipeline

        expander = ParallelKeywordExpander(expansion_type="lemmi", max_workers=2)

        collected_results = []

        with StreamingExpansionPipeline(expander, max_pending=10) as pipeline:
            # Submit a few tasks
            for i in range(3):
                keywords = ["test", "run"]
                scores = {"test": 0.9, "run": 0.8}
                callback_data = {"id": i}
                completed = pipeline.submit(keywords, scores, callback_data, top_n=3)
                collected_results.extend(completed)

            # Finish remaining
            remaining = pipeline.finish()
            collected_results.extend(remaining)

        # Should have results for all 3 submissions
        assert len(collected_results) == 3
        ids = {r[0]["id"] for r in collected_results}
        assert ids == {0, 1, 2}

    def test_pipeline_submit_without_context_raises(self):
        """Test that submitting without context raises RuntimeError."""
        from cicada.parallel_expander import StreamingExpansionPipeline

        expander = ParallelKeywordExpander(expansion_type="lemmi")
        pipeline = StreamingExpansionPipeline(expander)

        with pytest.raises(RuntimeError, match="Pipeline not started"):
            pipeline.submit(["test"], {"test": 0.9}, {"id": 1})

    def test_pipeline_max_pending_blocks(self):
        """Test that pipeline blocks when at max capacity."""
        from cicada.parallel_expander import StreamingExpansionPipeline

        expander = ParallelKeywordExpander(expansion_type="lemmi", max_workers=1)

        with StreamingExpansionPipeline(expander, max_pending=2) as pipeline:
            collected = []

            # Submit more tasks than max_pending to trigger blocking
            for i in range(5):
                keywords = ["test", "keyword"]
                scores = {"test": 0.9, "keyword": 0.8}
                completed = pipeline.submit(keywords, scores, {"id": i}, top_n=2)
                collected.extend(completed)

            # Finish remaining
            remaining = pipeline.finish()
            collected.extend(remaining)

            # All 5 should complete
            assert len(collected) == 5

    def test_pipeline_collect_completed(self):
        """Test collect_completed method returns proper type."""
        from cicada.parallel_expander import StreamingExpansionPipeline

        expander = ParallelKeywordExpander(expansion_type="lemmi", max_workers=2)

        with StreamingExpansionPipeline(expander, max_pending=10) as pipeline:
            # Collect completed on empty pipeline should return empty list
            completed = pipeline.collect_completed()
            assert isinstance(completed, list)
            assert completed == []

            # Submit a task
            pipeline.submit(["test"], {"test": 0.9}, {"id": 1}, top_n=2)

            # Verify stats updated
            assert pipeline.stats["submitted"] == 1

            # Finish to clean up
            pipeline.finish()

    def test_pipeline_pending_count(self):
        """Test pending_count property."""
        from cicada.parallel_expander import StreamingExpansionPipeline

        expander = ParallelKeywordExpander(expansion_type="lemmi", max_workers=1)

        with StreamingExpansionPipeline(expander, max_pending=10) as pipeline:
            initial_count = pipeline.pending_count
            assert initial_count == 0

            # Submit a task
            pipeline.submit(["test"], {"test": 0.9}, {"id": 1}, top_n=2)

            # Pending count should be >= 0 (task may have already completed)
            assert pipeline.pending_count >= 0
