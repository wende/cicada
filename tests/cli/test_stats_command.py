"""Integration tests for the stats CLI command."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cicada.command_logger import CommandLogger
from cicada.commands import handle_stats
from cicada.stats import StatsAnalyzer


def test_stats_handler_with_no_logs(capsys):
    """Test stats handler when no logs exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with tempfile.TemporaryDirectory() as temp_log:
            repo_path = Path(tmpdir)

            args = MagicMock()
            args.repo = str(repo_path)
            args.reset = False
            args.detailed = False
            args.time_series = False
            args.weekly = False
            args.tool = None
            args.last_7_days = False
            args.last_30_days = False
            args.format = "text"

            # Should not crash even with no logs
            handle_stats(args)

    captured = capsys.readouterr()
    assert "No MCP tool calls" in captured.out


def test_stats_analyzer_basic():
    """Test basic stats analyzer functionality."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with tempfile.TemporaryDirectory() as temp_log:
            repo_path = Path(tmpdir)
            logger = CommandLogger(log_dir=temp_log, repo_path=str(repo_path))

            # Create sample logs
            now = datetime.now()
            for i in range(3):
                logger.log_command(
                    tool_name="query",
                    arguments={"query": "test"},
                    response=[{"type": "text", "text": "Result line 1\nResult line 2"}],
                    execution_time_ms=100,
                    timestamp=now - timedelta(days=i),
                    error=None,
                )

            # Create analyzer
            analyzer = StatsAnalyzer(repo_path)
            analyzer.logger = logger

            # Get stats
            stats = analyzer.get_stats()

            assert stats["total_calls"] == 3
            assert stats["success_rate"] == 100.0
            assert "query" in stats["tools"]
            assert stats["total_lines"] > 0


def test_stats_analyzer_with_filtering():
    """Test stats analyzer with tool filtering."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with tempfile.TemporaryDirectory() as temp_log:
            repo_path = Path(tmpdir)
            logger = CommandLogger(log_dir=temp_log, repo_path=str(repo_path))

            # Create logs with different tools
            now = datetime.now()
            for i in range(2):
                logger.log_command(
                    tool_name="query",
                    arguments={"query": "test"},
                    response=[{"type": "text", "text": "Result"}],
                    execution_time_ms=100,
                    timestamp=now - timedelta(days=i),
                    error=None,
                )
                logger.log_command(
                    tool_name="search_module",
                    arguments={"query": "test"},
                    response=[{"type": "text", "text": "Result"}],
                    execution_time_ms=150,
                    timestamp=now - timedelta(days=i),
                    error=None,
                )

            analyzer = StatsAnalyzer(repo_path)
            analyzer.logger = logger

            # Filter by tool
            stats = analyzer.get_stats(tool_filter="query")

            assert stats["total_calls"] == 2
            assert len(stats["tools"]) == 1
            assert "query" in stats["tools"]


def test_stats_format_summary():
    """Test stats summary formatting."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with tempfile.TemporaryDirectory() as temp_log:
            repo_path = Path(tmpdir)
            logger = CommandLogger(log_dir=temp_log, repo_path=str(repo_path))

            # Create sample logs
            logger.log_command(
                tool_name="query",
                arguments={"query": "test"},
                response=[{"type": "text", "text": "Line 1\nLine 2\nLine 3"}],
                execution_time_ms=100,
                error=None,
            )

            analyzer = StatsAnalyzer(repo_path)
            analyzer.logger = logger

            stats = analyzer.get_stats()
            summary = analyzer.format_summary(stats)

            assert "Cicada Stats" in summary
            assert "Total Calls" in summary
            assert "Execution Time" in summary
            assert "Tokens" in summary


def test_stats_format_detailed():
    """Test stats detailed formatting."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with tempfile.TemporaryDirectory() as temp_log:
            repo_path = Path(tmpdir)
            logger = CommandLogger(log_dir=temp_log, repo_path=str(repo_path))

            logger.log_command(
                tool_name="query",
                arguments={"query": "test"},
                response=[{"type": "text", "text": "Result"}],
                execution_time_ms=100,
                error=None,
            )

            analyzer = StatsAnalyzer(repo_path)
            analyzer.logger = logger

            stats = analyzer.get_stats()
            detailed = analyzer.format_detailed(stats)

            assert "DETAILED BREAKDOWN" in detailed
            assert "query" in detailed


def test_stats_format_json():
    """Test stats JSON formatting."""
    import json

    with tempfile.TemporaryDirectory() as tmpdir:
        with tempfile.TemporaryDirectory() as temp_log:
            repo_path = Path(tmpdir)
            logger = CommandLogger(log_dir=temp_log, repo_path=str(repo_path))

            logger.log_command(
                tool_name="query",
                arguments={"query": "test"},
                response=[{"type": "text", "text": "Result"}],
                execution_time_ms=100,
                error=None,
            )

            analyzer = StatsAnalyzer(repo_path)
            analyzer.logger = logger

            stats = analyzer.get_stats()
            json_output = analyzer.format_json(stats)

            parsed = json.loads(json_output)
            assert "total_calls" in parsed
            assert "tools" in parsed


def test_stats_reset_functionality():
    """Test stats reset functionality."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with tempfile.TemporaryDirectory() as temp_log:
            repo_path = Path(tmpdir)
            logger = CommandLogger(log_dir=temp_log, repo_path=str(repo_path))

            # Create logs
            logger.log_command(
                tool_name="query",
                arguments={"query": "test"},
                response=[{"type": "text", "text": "Result"}],
                execution_time_ms=100,
                error=None,
            )

            # Verify logs exist
            logs_before = logger.read_logs(repo_hash=logger.repo_hash)
            assert len(logs_before) > 0

            # Reset
            analyzer = StatsAnalyzer(repo_path)
            analyzer.logger = logger

            count = analyzer.reset_stats()
            assert count > 0

            # Verify logs are cleared
            logs_after = logger.read_logs(repo_hash=logger.repo_hash)
            assert len(logs_after) == 0


def test_stats_per_tool_breakdown():
    """Test per-tool statistics breakdown."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with tempfile.TemporaryDirectory() as temp_log:
            repo_path = Path(tmpdir)
            logger = CommandLogger(log_dir=temp_log, repo_path=str(repo_path))

            # Create logs for different tools
            tools = ["query", "search_module", "search_function"]
            for tool in tools:
                for i in range(2):
                    logger.log_command(
                        tool_name=tool,
                        arguments={"test": "data"},
                        response=[{"type": "text", "text": f"Result from {tool}"}],
                        execution_time_ms=100 + i * 10,
                        error=None,
                    )

            analyzer = StatsAnalyzer(repo_path)
            analyzer.logger = logger

            stats = analyzer.get_stats()

            assert stats["total_calls"] == 6
            assert len(stats["tools"]) == 3
            for tool in tools:
                assert tool in stats["tools"]
                assert stats["tools"][tool]["count"] == 2


def test_stats_time_series_weekly_format():
    """Test time-series weekly output formatting."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with tempfile.TemporaryDirectory() as temp_log:
            repo_path = Path(tmpdir)
            logger = CommandLogger(log_dir=temp_log, repo_path=str(repo_path))

            # Create sample logs spanning multiple weeks
            now = datetime.now()
            for i in range(3):
                logger.log_command(
                    tool_name="query",
                    arguments={"query": "test"},
                    response=[{"type": "text", "text": "Result"}],
                    execution_time_ms=100,
                    timestamp=now - timedelta(days=i * 7),
                    error=None,
                )

            analyzer = StatsAnalyzer(repo_path)
            analyzer.logger = logger

            stats = analyzer.get_stats(time_series=True, granularity="weekly")
            output = analyzer.format_time_series(stats)

            assert "Weekly" in output


def test_stats_json_format_output():
    """Test JSON output format directly."""
    import json as json_module

    with tempfile.TemporaryDirectory() as tmpdir:
        with tempfile.TemporaryDirectory() as temp_log:
            repo_path = Path(tmpdir)
            logger = CommandLogger(log_dir=temp_log, repo_path=str(repo_path))

            logger.log_command(
                tool_name="query",
                arguments={"query": "test"},
                response=[{"type": "text", "text": "Result"}],
                execution_time_ms=100,
                error=None,
            )

            analyzer = StatsAnalyzer(repo_path)
            analyzer.logger = logger

            stats = analyzer.get_stats()
            output = analyzer.format_json(stats)

            parsed = json_module.loads(output)
            assert "total_calls" in parsed
            assert parsed["total_calls"] == 1


def test_stats_with_days_filter():
    """Test stats with days filter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with tempfile.TemporaryDirectory() as temp_log:
            repo_path = Path(tmpdir)
            logger = CommandLogger(log_dir=temp_log, repo_path=str(repo_path))

            now = datetime.now()
            # Log within 7 days
            logger.log_command(
                tool_name="query",
                arguments={"query": "test"},
                response=[{"type": "text", "text": "Result"}],
                execution_time_ms=100,
                timestamp=now - timedelta(days=2),
                error=None,
            )
            # Log outside 7 days
            logger.log_command(
                tool_name="query",
                arguments={"query": "old"},
                response=[{"type": "text", "text": "Result"}],
                execution_time_ms=100,
                timestamp=now - timedelta(days=10),
                error=None,
            )

            analyzer = StatsAnalyzer(repo_path)
            analyzer.logger = logger

            # Filter to last 7 days
            stats = analyzer.get_stats(days=7)
            assert stats["total_calls"] == 1

            # Filter to last 30 days - should include both
            stats = analyzer.get_stats(days=30)
            assert stats["total_calls"] == 2


def test_stats_reset_with_force(capsys):
    """Test stats reset with force flag (no confirmation)."""
    from cicada.commands import _handle_stats_reset

    with tempfile.TemporaryDirectory() as tmpdir:
        with tempfile.TemporaryDirectory() as temp_log:
            repo_path = Path(tmpdir)
            logger = CommandLogger(log_dir=temp_log, repo_path=str(repo_path))

            logger.log_command(
                tool_name="query",
                arguments={"query": "test"},
                response=[{"type": "text", "text": "Result"}],
                execution_time_ms=100,
                error=None,
            )

            analyzer = StatsAnalyzer(repo_path)
            analyzer.logger = logger

            args = MagicMock()
            args.older_than = None
            args.force = True

            _handle_stats_reset(args, analyzer)

    captured = capsys.readouterr()
    assert "Deleted" in captured.out


def test_stats_reset_older_than(capsys):
    """Test stats reset with older_than parameter."""
    from cicada.commands import _handle_stats_reset

    with tempfile.TemporaryDirectory() as tmpdir:
        with tempfile.TemporaryDirectory() as temp_log:
            repo_path = Path(tmpdir)
            logger = CommandLogger(log_dir=temp_log, repo_path=str(repo_path))

            now = datetime.now()
            # Create old log
            logger.log_command(
                tool_name="query",
                arguments={"query": "test"},
                response=[{"type": "text", "text": "Result"}],
                execution_time_ms=100,
                timestamp=now - timedelta(days=40),
                error=None,
            )

            analyzer = StatsAnalyzer(repo_path)
            analyzer.logger = logger

            args = MagicMock()
            args.older_than = 30
            args.force = False

            _handle_stats_reset(args, analyzer)

    captured = capsys.readouterr()
    assert "older than 30 days" in captured.out
