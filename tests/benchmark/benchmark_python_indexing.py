"""
Benchmark suite for Python SCIP indexing performance.

This module provides benchmarks to measure:
- Overall indexing time
- SCIP conversion time specifically
- Per-file conversion metrics
- Memory usage

Used to validate the O(n²) → O(n) optimization.
"""

import time
import tracemalloc
from pathlib import Path
from typing import Dict, Any
import json
import cProfile
import pstats
from io import StringIO

from cicada.languages.python.indexer import PythonSCIPIndexer


class PythonIndexingBenchmark:
    """Benchmark Python SCIP indexing performance."""

    def __init__(self, repo_path: Path):
        """
        Initialize benchmark for a repository.

        Args:
            repo_path: Path to Python repository to index
        """
        self.repo_path = Path(repo_path)
        self.results: Dict[str, Any] = {}

    def run_baseline(self, extract_keywords: bool = True, profile: bool = False) -> Dict[str, Any]:
        """
        Run baseline benchmark on current implementation.

        Args:
            extract_keywords: Whether to extract keywords
            profile: Whether to run cProfile profiling

        Returns:
            Dictionary with benchmark results:
            - total_time: Total indexing time in seconds
            - conversion_time: SCIP conversion time in seconds (if available)
            - memory_peak_mb: Peak memory usage in MB
            - file_count: Number of files indexed
            - profile_stats: cProfile stats if profile=True
        """
        print(f"\n{'='*60}")
        print("BASELINE BENCHMARK - Current Implementation")
        print(f"{'='*60}")
        print(f"Repository: {self.repo_path}")
        print(f"Extract keywords: {extract_keywords}")
        print(f"{'='*60}\n")

        # Start memory tracking
        tracemalloc.start()
        start_time = time.time()

        # Create indexer
        indexer = PythonSCIPIndexer(verbose=True)

        # Profile if requested
        profiler = None
        if profile:
            profiler = cProfile.Profile()
            profiler.enable()

        # Run indexing (use incremental_index_repository for full control)
        # Note: We need to provide a temp output path since the method saves to disk
        import tempfile

        temp_output = tempfile.mktemp(suffix=".json")

        try:
            result = indexer.incremental_index_repository(
                repo_path=str(self.repo_path),
                output_path=temp_output,
                extract_keywords=extract_keywords,
                extract_string_keywords=False,
                compute_timestamps=True,
                extract_cochange=False,
                force_full=True,  # Force full index for accurate benchmark
                verbose=True,
            )

            # Stop profiling
            if profiler:
                profiler.disable()

            # Calculate metrics
            total_time = time.time() - start_time
            current_memory, peak_memory = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # Extract file count from result
            # Note: result is a dict with keys: success, modules_count, functions_count, files_indexed, errors
            file_count = result.get("files_indexed", 0)

            # Parse conversion time from indexer logs (if available)
            # This is a rough extraction - the actual timing is printed to stdout
            conversion_time = None  # Will be visible in verbose output

            # Store results
            self.results = {
                "total_time": round(total_time, 2),
                "conversion_time": conversion_time,  # Captured from logs
                "memory_peak_mb": round(peak_memory / 1024 / 1024, 2),
                "file_count": file_count,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

            # Add profile stats if available
            if profiler:
                s = StringIO()
                ps = pstats.Stats(profiler, stream=s)
                ps.sort_stats("cumulative")
                ps.print_stats(30)  # Top 30 functions
                self.results["profile_stats"] = s.getvalue()

            # Print results
            print(f"\n{'='*60}")
            print("BASELINE RESULTS")
            print(f"{'='*60}")
            print(f"Total time:        {self.results['total_time']:.2f}s")
            print(f"Peak memory:       {self.results['memory_peak_mb']:.2f} MB")
            print(f"Files indexed:     {file_count}")
            print(f"{'='*60}\n")

            if profile:
                print("\nTOP 30 FUNCTIONS BY CUMULATIVE TIME:")
                print("=" * 60)
                print(self.results["profile_stats"])

            # Clean up temp file
            try:
                import os

                if os.path.exists(temp_output):
                    os.remove(temp_output)
            except:
                pass

            return self.results

        except Exception as e:
            print(f"\n❌ Benchmark failed: {e}")
            tracemalloc.stop()
            # Clean up temp file
            try:
                import os

                if os.path.exists(temp_output):
                    os.remove(temp_output)
            except:
                pass
            raise

    def save_results(self, output_path: Path):
        """Save benchmark results to JSON file."""
        with open(output_path, "w") as f:
            # Don't save profile stats to JSON (too large)
            results_to_save = {k: v for k, v in self.results.items() if k != "profile_stats"}
            json.dump(results_to_save, f, indent=2)
        print(f"\n✅ Results saved to: {output_path}")

    def compare_results(self, baseline_path: Path):
        """
        Compare current results against saved baseline.

        Args:
            baseline_path: Path to baseline results JSON
        """
        if not baseline_path.exists():
            print(f"❌ Baseline file not found: {baseline_path}")
            return

        with open(baseline_path) as f:
            baseline = json.load(f)

        print(f"\n{'='*60}")
        print("PERFORMANCE COMPARISON")
        print(f"{'='*60}")
        print(f"{'Metric':<25} {'Baseline':<15} {'Current':<15} {'Change':<15}")
        print("-" * 60)

        # Compare total time
        baseline_time = baseline.get("total_time", 0)
        current_time = self.results.get("total_time", 0)
        time_change = ((current_time - baseline_time) / baseline_time * 100) if baseline_time else 0
        print(
            f"{'Total time (s)':<25} {baseline_time:<15.2f} {current_time:<15.2f} {time_change:+.1f}%"
        )

        # Compare memory
        baseline_mem = baseline.get("memory_peak_mb", 0)
        current_mem = self.results.get("memory_peak_mb", 0)
        mem_change = ((current_mem - baseline_mem) / baseline_mem * 100) if baseline_mem else 0
        print(
            f"{'Peak memory (MB)':<25} {baseline_mem:<15.2f} {current_mem:<15.2f} {mem_change:+.1f}%"
        )

        # Compare file count
        baseline_files = baseline.get("file_count", 0)
        current_files = self.results.get("file_count", 0)
        print(
            f"{'Files indexed':<25} {baseline_files:<15} {current_files:<15} {current_files - baseline_files:+}"
        )

        print(f"{'='*60}\n")

        # Highlight significant improvements
        if time_change < -10:
            print(f"✅ SIGNIFICANT IMPROVEMENT: {abs(time_change):.1f}% faster!")
        elif time_change > 10:
            print(f"⚠️  REGRESSION: {time_change:.1f}% slower")
        else:
            print("➡️  Performance roughly equivalent")


def run_benchmark_suite():
    """Run complete benchmark suite on test repositories."""
    import sys

    # Determine repo path
    if len(sys.argv) > 1:
        repo_path = Path(sys.argv[1])
    else:
        # Default: benchmark cicada itself
        repo_path = Path(__file__).parent.parent.parent

    print(f"\n🔥 Starting Python SCIP Indexing Benchmark")
    print(f"Repository: {repo_path}")

    # Run baseline benchmark
    benchmark = PythonIndexingBenchmark(repo_path)

    try:
        # Run with profiling
        results = benchmark.run_baseline(extract_keywords=True, profile=True)

        # Set up paths
        output_dir = Path(__file__).parent
        output_dir.mkdir(exist_ok=True)
        baseline_path = output_dir / "baseline_results.json"

        # If there's a previous baseline, compare BEFORE saving
        if baseline_path.exists():
            print("\n📊 Comparing against previous baseline...")
            benchmark.compare_results(baseline_path)

        # Save results (after comparison)
        benchmark.save_results(baseline_path)

        print("\n✅ Benchmark complete!")
        return 0

    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(run_benchmark_suite())
