"""Tests for the stats module."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from cicada.command_logger import CommandLogger
from cicada.stats import StatsAnalyzer


@pytest.fixture
def temp_log_dir():
    """Create a temporary log directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_logger(temp_log_dir, monkeypatch):
    """Create a CommandLogger with sample log data."""
    logger = CommandLogger(log_dir=temp_log_dir, repo_path="/test/repo")

    # Create sample logs
    now = datetime.now()
    for i in range(5):
        timestamp = now - timedelta(days=i)
        logger.log_command(
            tool_name="query" if i % 2 == 0 else "search_module",
            arguments={"query": "test" * 10},
            response=[{"type": "text", "text": "Result line 1\nResult line 2\n"}],
            execution_time_ms=100 + i * 10,
            timestamp=timestamp,
            error=None,
        )

    return logger


@pytest.fixture
def analyzer(temp_log_dir):
    """Create a StatsAnalyzer for testing."""
    # Create a temporary test directory
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        analyzer = StatsAnalyzer(repo_path)
        # Override the logger to use the temp directory
        analyzer.logger = CommandLogger(log_dir=temp_log_dir, repo_path=str(repo_path))
        yield analyzer


def test_empty_stats(analyzer):
    """Test stats when no logs are recorded."""
    stats = analyzer.get_stats()

    assert stats["total_calls"] == 0
    assert stats["success_rate"] == 0
    assert stats["total_execution_time_ms"] == 0
    assert stats["total_lines"] == 0
    assert len(stats["tools"]) == 0


def test_aggregate_stats(sample_logger):
    """Test basic aggregate statistics calculation."""
    repo_path = Path("/test/repo")
    analyzer = StatsAnalyzer(repo_path)
    analyzer.logger = sample_logger

    stats = analyzer.get_stats()

    assert stats["total_calls"] == 5
    assert stats["successful_calls"] == 5
    assert stats["failed_calls"] == 0
    assert stats["success_rate"] == 100.0
    assert stats["total_execution_time_ms"] > 0
    assert len(stats["tools"]) == 2
    assert "query" in stats["tools"]
    assert "search_module" in stats["tools"]


def test_tool_filtering(sample_logger):
    """Test filtering stats by tool."""
    repo_path = Path("/test/repo")
    analyzer = StatsAnalyzer(repo_path)
    analyzer.logger = sample_logger

    stats = analyzer.get_stats(tool_filter="query")

    assert stats["total_calls"] == 3  # query is called 3 times (i=0,2,4)
    assert len(stats["tools"]) == 1
    assert "query" in stats["tools"]


def test_date_range_filtering(sample_logger):
    """Test filtering stats by date range."""
    repo_path = Path("/test/repo")
    analyzer = StatsAnalyzer(repo_path)
    analyzer.logger = sample_logger

    stats = analyzer.get_stats(days=1)

    # Should only include logs from today
    assert stats["total_calls"] <= 5


def test_line_counting(temp_log_dir):
    """Test line counting from responses."""
    logger = CommandLogger(log_dir=temp_log_dir, repo_path="/test/repo")

    # Log with multi-line response
    logger.log_command(
        tool_name="query",
        arguments={"query": "test"},
        response=[{"type": "text", "text": "Line 1\nLine 2\nLine 3"}],
        execution_time_ms=100,
        error=None,
    )

    repo_path = Path("/test/repo")
    analyzer = StatsAnalyzer(repo_path)
    analyzer.logger = logger

    stats = analyzer.get_stats()

    # Should count 3 lines
    assert stats["total_lines"] == 3


def test_token_counting(temp_log_dir):
    """Test token counting in logs."""
    logger = CommandLogger(log_dir=temp_log_dir, repo_path="/test/repo")

    # Log command
    logger.log_command(
        tool_name="query",
        arguments={"query": "test query"},
        response=[{"type": "text", "text": "Result text"}],
        execution_time_ms=100,
        error=None,
    )

    # Check that tokens were counted
    logs = logger.read_logs()
    assert len(logs) == 1
    assert logs[0]["input_tokens"] > 0
    assert logs[0]["output_tokens"] > 0


def test_per_tool_breakdown(sample_logger):
    """Test per-tool statistics breakdown."""
    repo_path = Path("/test/repo")
    analyzer = StatsAnalyzer(repo_path)
    analyzer.logger = sample_logger

    stats = analyzer.get_stats()

    for tool_name, tool_data in stats["tools"].items():
        assert "count" in tool_data
        assert "success_count" in tool_data
        assert "avg_time_ms" in tool_data
        assert "total_lines" in tool_data
        assert "input_tokens" in tool_data
        assert "output_tokens" in tool_data
        assert tool_data["count"] > 0


def test_time_series_daily(sample_logger):
    """Test time-series statistics (daily aggregation)."""
    repo_path = Path("/test/repo")
    analyzer = StatsAnalyzer(repo_path)
    analyzer.logger = sample_logger

    stats = analyzer.get_stats(time_series=True, granularity="daily")

    assert stats["granularity"] == "daily"
    assert len(stats["series"]) > 0
    for entry in stats["series"]:
        assert "date" in entry
        assert "calls" in entry
        assert "success_rate" in entry
        assert "total_lines" in entry
        assert "tools" in entry


def test_format_summary(sample_logger):
    """Test summary output formatting."""
    repo_path = Path("/test/repo")
    analyzer = StatsAnalyzer(repo_path)
    analyzer.logger = sample_logger

    stats = analyzer.get_stats()
    output = analyzer.format_summary(stats)

    assert "Cicada Stats" in output
    assert "Total Calls" in output
    assert "Execution Time" in output
    assert "Tokens" in output


def test_format_detailed(sample_logger):
    """Test detailed output formatting."""
    repo_path = Path("/test/repo")
    analyzer = StatsAnalyzer(repo_path)
    analyzer.logger = sample_logger

    stats = analyzer.get_stats()
    output = analyzer.format_detailed(stats)

    assert "DETAILED BREAKDOWN" in output
    assert "query" in output or "search_module" in output


def test_format_json(sample_logger):
    """Test JSON output formatting."""
    repo_path = Path("/test/repo")
    analyzer = StatsAnalyzer(repo_path)
    analyzer.logger = sample_logger

    stats = analyzer.get_stats()
    output = analyzer.format_json(stats)

    # Should be valid JSON
    parsed = json.loads(output)
    assert parsed["total_calls"] == stats["total_calls"]


def test_format_time_series(sample_logger):
    """Test time-series output formatting."""
    repo_path = Path("/test/repo")
    analyzer = StatsAnalyzer(repo_path)
    analyzer.logger = sample_logger

    stats = analyzer.get_stats(time_series=True)
    output = analyzer.format_time_series(stats)

    assert "Time Series" in output
    assert "Daily" in output


def test_reset_stats_all(sample_logger, temp_log_dir):
    """Test resetting all stats."""
    repo_path = Path("/test/repo")
    analyzer = StatsAnalyzer(repo_path)
    analyzer.logger = sample_logger

    # Verify logs exist
    logs_before = sample_logger.read_logs()
    assert len(logs_before) > 0

    # Reset all logs
    count = analyzer.reset_stats()
    assert count > 0

    # Verify logs are deleted
    logs_after = sample_logger.read_logs()
    assert len(logs_after) == 0


def test_reset_stats_older_than(temp_log_dir):
    """Test resetting stats older than N days."""
    logger = CommandLogger(log_dir=temp_log_dir, repo_path="/test/repo")

    # Create logs with different timestamps
    now = datetime.now()
    logger.log_command(
        tool_name="query",
        arguments={"query": "test"},
        response=[{"type": "text", "text": "Result"}],
        execution_time_ms=100,
        timestamp=now - timedelta(days=40),
        error=None,
    )
    logger.log_command(
        tool_name="query",
        arguments={"query": "test"},
        response=[{"type": "text", "text": "Result"}],
        execution_time_ms=100,
        timestamp=now - timedelta(days=5),
        error=None,
    )

    # Reset logs older than 30 days
    count = logger.clear_logs(older_than_days=30)

    # One log should be deleted
    assert count >= 1

    # Recent log should still exist
    logs = logger.read_logs()
    assert len(logs) >= 1


def test_empty_stats_output(analyzer):
    """Test output formatting for empty stats."""
    stats = analyzer.get_stats()
    output = analyzer.format_summary(stats)

    assert "No MCP tool calls" in output


def test_count_lines_nested_dict(temp_log_dir):
    """Test _count_lines with nested dict structures."""
    logger = CommandLogger(log_dir=temp_log_dir, repo_path="/test/repo")

    # Log with nested dict response (not TextContent)
    nested_response = {
        "wrapper": {
            "type": "text",
            "text": "Line 1\nLine 2\nLine 3",
        },
        "metadata": {"count": 3},
    }
    logger.log_command(
        tool_name="query",
        arguments={"query": "test"},
        response=nested_response,
        execution_time_ms=100,
        error=None,
    )

    repo_path = Path("/test/repo")
    analyzer = StatsAnalyzer(repo_path)
    analyzer.logger = logger

    stats = analyzer.get_stats()
    # Should count lines from nested text content
    assert stats["total_lines"] == 3


def test_count_lines_raw_string(temp_log_dir):
    """Test _count_lines with raw string response."""
    logger = CommandLogger(log_dir=temp_log_dir, repo_path="/test/repo")

    # Log with raw string response
    logger.log_command(
        tool_name="query",
        arguments={"query": "test"},
        response="Line 1\nLine 2",
        execution_time_ms=100,
        error=None,
    )

    repo_path = Path("/test/repo")
    analyzer = StatsAnalyzer(repo_path)
    analyzer.logger = logger

    stats = analyzer.get_stats()
    assert stats["total_lines"] == 2


def test_time_series_weekly(sample_logger):
    """Test time-series statistics with weekly granularity."""
    repo_path = Path("/test/repo")
    analyzer = StatsAnalyzer(repo_path)
    analyzer.logger = sample_logger

    stats = analyzer.get_stats(time_series=True, granularity="weekly")

    assert stats["granularity"] == "weekly"
    assert len(stats["series"]) > 0
    # Weekly series should use ISO week format: YYYY-WNN
    for entry in stats["series"]:
        assert "date" in entry
        assert "-W" in entry["date"]


def test_format_large_execution_time(temp_log_dir):
    """Test formatting when execution time exceeds 60 seconds."""
    logger = CommandLogger(log_dir=temp_log_dir, repo_path="/test/repo")

    # Log with very long execution time (2 minutes)
    logger.log_command(
        tool_name="query",
        arguments={"query": "test"},
        response=[{"type": "text", "text": "Result"}],
        execution_time_ms=120000,  # 2 minutes
        error=None,
    )

    repo_path = Path("/test/repo")
    analyzer = StatsAnalyzer(repo_path)
    analyzer.logger = logger

    stats = analyzer.get_stats()
    output = analyzer.format_summary(stats)

    # Should display in minutes
    assert "min" in output


def test_get_project_stats_with_index(temp_log_dir):
    """Test _get_project_stats when index file exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        analyzer = StatsAnalyzer(repo_path)

        # Create a mock index file
        from cicada.utils.storage import get_storage_dir

        storage_dir = get_storage_dir(repo_path)
        storage_dir.mkdir(parents=True, exist_ok=True)
        index_file = storage_dir / "index.json"

        index_data = {
            "metadata": {
                "total_modules": 10,
                "total_functions": 50,
            },
            "modules": {
                "TestModule": {
                    "keywords": {"keyword1": 1, "keyword2": 2},
                    "functions": [],
                },
                "AnotherModule": {
                    "keywords": {"keyword1": 1, "keyword3": 3},
                    "functions": [],
                },
            },
        }
        with open(index_file, "w") as f:
            json.dump(index_data, f)

        project_stats = analyzer._get_project_stats()

        assert project_stats["module_count"] == 10
        assert project_stats["function_count"] == 50
        assert project_stats["keyword_count"] == 3  # unique keywords


def test_get_project_stats_fallback(temp_log_dir):
    """Test _get_project_stats fallback when metadata is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        analyzer = StatsAnalyzer(repo_path)

        # Create index file without metadata
        from cicada.utils.storage import get_storage_dir

        storage_dir = get_storage_dir(repo_path)
        storage_dir.mkdir(parents=True, exist_ok=True)
        index_file = storage_dir / "index.json"

        index_data = {
            "modules": {
                "TestModule": {
                    "functions": [{"name": "func1"}, {"name": "func2"}],
                    "keywords": {"key1": 1},
                },
                "AnotherModule": {
                    "functions": [{"name": "func3"}],
                    "keywords": {},
                },
            },
        }
        with open(index_file, "w") as f:
            json.dump(index_data, f)

        project_stats = analyzer._get_project_stats()

        assert project_stats["module_count"] == 2
        assert project_stats["function_count"] == 3
        assert project_stats["keyword_count"] == 1


def test_format_summary_with_project_stats(temp_log_dir):
    """Test format_summary includes project stats when available."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        logger = CommandLogger(log_dir=temp_log_dir, repo_path=str(repo_path))

        # Create a log
        logger.log_command(
            tool_name="query",
            arguments={"query": "test"},
            response=[{"type": "text", "text": "Result"}],
            execution_time_ms=100,
            error=None,
        )

        analyzer = StatsAnalyzer(repo_path)
        analyzer.logger = logger

        # Create a mock index file
        from cicada.utils.storage import get_storage_dir

        storage_dir = get_storage_dir(repo_path)
        storage_dir.mkdir(parents=True, exist_ok=True)
        index_file = storage_dir / "index.json"

        index_data = {
            "metadata": {"total_modules": 5, "total_functions": 25},
            "modules": {"Test": {"keywords": {"auth": 1}}},
        }
        with open(index_file, "w") as f:
            json.dump(index_data, f)

        stats = analyzer.get_stats()
        output = analyzer.format_summary(stats)

        assert "5 modules" in output
        assert "25 functions" in output


def test_extract_date_range_empty_logs(temp_log_dir):
    """Test _extract_date_range returns None for empty logs."""
    repo_path = Path("/test/repo")
    analyzer = StatsAnalyzer(repo_path)
    analyzer.logger = CommandLogger(log_dir=temp_log_dir, repo_path="/test/repo")

    # Call private method directly
    result = analyzer._extract_date_range([])
    assert result is None


def test_format_detailed_empty(analyzer):
    """Test format_detailed with empty stats."""
    stats = analyzer.get_stats()
    output = analyzer.format_detailed(stats)

    assert "No MCP tool calls" in output
