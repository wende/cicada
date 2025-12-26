"""Tests for PR embeddings functionality."""

import pytest
from unittest.mock import MagicMock, patch

from cicada.embeddings.text_builder import (
    build_pr_document_id,
    build_pr_metadata,
    build_pr_text,
)


class TestBuildPrText:
    """Tests for build_pr_text function."""

    def test_title_only(self):
        """PR with only title returns formatted text."""
        pr_data = {"title": "Fix authentication bug"}
        result = build_pr_text(pr_data)
        assert result == "PR: Fix authentication bug"

    def test_title_and_description(self):
        """PR with title and description combines both."""
        pr_data = {
            "title": "Add new feature",
            "description": "This PR adds a new authentication system.",
        }
        result = build_pr_text(pr_data)
        assert "PR: Add new feature" in result
        assert "This PR adds a new authentication system." in result

    def test_empty_description(self):
        """PR with empty description only shows title."""
        pr_data = {"title": "Quick fix", "description": ""}
        result = build_pr_text(pr_data)
        assert result == "PR: Quick fix"

    def test_long_description_truncated(self):
        """Long descriptions are truncated to 2000 chars."""
        long_desc = "x" * 3000
        pr_data = {"title": "Test PR", "description": long_desc}
        result = build_pr_text(pr_data)
        # Should be truncated with "..."
        assert "..." in result
        # Title should still be there
        assert "PR: Test PR" in result

    def test_no_title_no_description(self):
        """PR with neither title nor description returns empty string."""
        pr_data = {}
        result = build_pr_text(pr_data)
        assert result == ""

    def test_whitespace_only_description(self):
        """Whitespace-only description is treated as empty."""
        pr_data = {"title": "Test", "description": "   \n\t  "}
        result = build_pr_text(pr_data)
        assert result == "PR: Test"


class TestBuildPrDocumentId:
    """Tests for build_pr_document_id function."""

    def test_returns_pr_prefix(self):
        """Document ID has pr: prefix."""
        result = build_pr_document_id(123)
        assert result == "pr:123"

    def test_different_numbers(self):
        """Different PR numbers produce different IDs."""
        assert build_pr_document_id(1) != build_pr_document_id(2)


class TestBuildPrMetadata:
    """Tests for build_pr_metadata function."""

    def test_basic_metadata(self):
        """Basic PR data produces correct metadata."""
        pr_data = {
            "number": 42,
            "title": "Test PR",
            "state": "merged",
            "author": "testuser",
        }
        result = build_pr_metadata(pr_data)

        assert result["type"] == "pr"
        assert result["name"] == "PR #42"
        assert result["pr_number"] == 42
        assert result["title"] == "Test PR"
        assert result["state"] == "merged"
        assert result["author"] == "testuser"

    def test_optional_fields(self):
        """Optional fields are included when present."""
        pr_data = {
            "number": 1,
            "title": "Test",
            "merged_at": "2024-01-01T00:00:00Z",
            "created_at": "2023-12-01T00:00:00Z",
        }
        result = build_pr_metadata(pr_data)

        assert result["merged_at"] == "2024-01-01T00:00:00Z"
        assert result["created_at"] == "2023-12-01T00:00:00Z"

    def test_missing_optional_fields(self):
        """Missing optional fields are None."""
        pr_data = {"number": 1, "title": "Test"}
        result = build_pr_metadata(pr_data)

        assert result["merged_at"] is None
        assert result["created_at"] is None


class TestEmbeddingsIndexerPrIndexing:
    """Tests for EmbeddingsIndexer.index_prs_from_pr_index method."""

    @pytest.fixture
    def mock_store(self):
        """Create a mock Store."""
        with patch("cicada.embeddings.indexer.Store") as mock:
            store_instance = MagicMock()
            mock.return_value = store_instance
            yield store_instance

    @pytest.fixture
    def sample_pr_index(self):
        """Create a sample PR index for testing."""
        return {
            "prs": {
                "1": {
                    "number": 1,
                    "title": "Add authentication",
                    "description": "Implements OAuth2 authentication flow.",
                    "state": "merged",
                    "author": "dev1",
                },
                "2": {
                    "number": 2,
                    "title": "Fix bug",
                    "description": "",
                    "state": "closed",
                    "author": "dev2",
                },
                "3": {
                    "number": 3,
                    "title": "",  # Empty title - should be skipped
                    "description": "",
                    "state": "open",
                    "author": "dev3",
                },
            },
            "metadata": {"total_prs": 3},
        }

    def test_indexes_prs_with_content(self, tmp_path, mock_store, sample_pr_index):
        """PRs with content are indexed."""
        from cicada.embeddings.indexer import EmbeddingsIndexer

        indexer = EmbeddingsIndexer(tmp_path, verbose=False)
        indexer.index_prs_from_pr_index(sample_pr_index)

        # Should have called add for PR 1 and PR 2 (PR 3 has no content)
        assert mock_store.add.call_count == 2

    def test_skips_empty_prs(self, tmp_path, mock_store):
        """PRs with no title or description are skipped."""
        from cicada.embeddings.indexer import EmbeddingsIndexer

        pr_index = {
            "prs": {
                "1": {"number": 1, "title": "", "description": ""},
            }
        }

        indexer = EmbeddingsIndexer(tmp_path, verbose=False)
        indexer.index_prs_from_pr_index(pr_index)

        # Should not have called add for empty PR
        assert mock_store.add.call_count == 0

    def test_empty_pr_index(self, tmp_path, mock_store):
        """Empty PR index doesn't call store.add."""
        from cicada.embeddings.indexer import EmbeddingsIndexer

        indexer = EmbeddingsIndexer(tmp_path, verbose=False)
        indexer.index_prs_from_pr_index({"prs": {}})

        assert mock_store.add.call_count == 0


class TestPRSearchResult:
    """Tests for PRSearchResult class."""

    def test_basic_construction(self):
        """PRSearchResult can be constructed with required fields."""
        from cicada.embeddings.searcher import PRSearchResult

        result = PRSearchResult(
            pr_number=42,
            title="Test PR",
            score=0.85,
        )

        assert result.pr_number == 42
        assert result.title == "Test PR"
        assert result.score == 0.85
        assert result.state == "unknown"
        assert result.author == "unknown"

    def test_all_fields(self):
        """PRSearchResult stores all fields correctly."""
        from cicada.embeddings.searcher import PRSearchResult

        result = PRSearchResult(
            pr_number=1,
            title="Full PR",
            score=0.9,
            state="merged",
            author="testuser",
            merged_at="2024-01-01",
            created_at="2023-12-01",
        )

        assert result.state == "merged"
        assert result.author == "testuser"
        assert result.merged_at == "2024-01-01"
        assert result.created_at == "2023-12-01"
