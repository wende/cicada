"""
Comprehensive tests for keyword expansion using word embeddings.

Tests the KeywordExpander class for semantic keyword expansion
using FastText embeddings.
"""

from unittest.mock import MagicMock, patch

import pytest

from cicada.keyword_expander import KeywordExpander


class TestKeywordExpanderInitialization:
    """Tests for KeywordExpander initialization"""

    def test_invalid_model_type(self):
        """Test that invalid model type raises ValueError"""
        with pytest.raises(ValueError, match="Unsupported model_type: invalid"):
            KeywordExpander(model_type="invalid")

    def test_fasttext_initialization(self):
        """Test initialization with fasttext model type"""
        expander = KeywordExpander(model_type="fasttext", verbose=False)
        assert expander.model_type == "fasttext"
        assert expander.verbose is False
        assert expander._model is None

    def test_verbose_initialization(self):
        """Test initialization with verbose mode"""
        expander = KeywordExpander(model_type="fasttext", verbose=True)
        assert expander.verbose is True


class TestKeywordExpanderModelLoading:
    """Tests for model loading functionality"""

    @patch("gensim.downloader")
    def test_model_loads_successfully(self, mock_downloader):
        """Test that model loads successfully on first use"""
        # Create mock model
        mock_model = MagicMock()
        mock_model.most_similar.return_value = [
            ("similar1", 0.9),
            ("similar2", 0.8),
        ]
        mock_downloader.load.return_value = mock_model

        # Create expander and trigger model load
        expander = KeywordExpander(model_type="fasttext", verbose=False)
        expander._load_model()

        # Verify model was loaded with correct name
        mock_downloader.load.assert_called_once_with("fasttext-wiki-news-subwords-300")
        assert expander._model_cache["fasttext"] is mock_model

    @patch("gensim.downloader")
    def test_model_cached_after_first_load(self, mock_downloader):
        """Test that model is cached and not reloaded"""
        # Create mock model
        mock_model = MagicMock()
        mock_downloader.load.return_value = mock_model

        # First expander loads model
        expander1 = KeywordExpander(model_type="fasttext", verbose=False)
        expander1._load_model()

        # Clear call count
        mock_downloader.load.reset_mock()

        # Second expander should use cached model
        expander2 = KeywordExpander(model_type="fasttext", verbose=False)
        expander2._load_model()

        # Should not call load again
        mock_downloader.load.assert_not_called()

    def test_import_error_when_gensim_missing(self):
        """Test that missing gensim raises helpful ImportError"""
        with patch.dict("sys.modules", {"gensim.downloader": None}):
            with patch("builtins.__import__", side_effect=ImportError("No module")):
                expander = KeywordExpander(model_type="fasttext", verbose=False)
                with pytest.raises(ImportError, match="gensim is required for keyword expansion"):
                    expander._load_model()

    @patch("gensim.downloader")
    def test_model_load_failure(self, mock_downloader):
        """Test handling of model loading failures"""
        mock_downloader.load.side_effect = Exception("Download failed")

        expander = KeywordExpander(model_type="fasttext", verbose=False)
        with pytest.raises(Exception, match="Failed to load fasttext model"):
            expander._load_model()

    @patch("gensim.downloader")
    def test_verbose_model_loading(self, mock_downloader, capsys):
        """Test that verbose mode prints progress messages"""
        mock_model = MagicMock()
        mock_downloader.load.return_value = mock_model

        # Clear cache to force fresh load
        KeywordExpander._model_cache.clear()

        expander = KeywordExpander(model_type="fasttext", verbose=True)
        expander._load_model()

        captured = capsys.readouterr()
        assert "Loading fasttext model" in captured.out
        assert "model loaded successfully" in captured.out


class TestKeywordExpansion:
    """Tests for keyword expansion functionality"""

    def setup_method(self):
        """Clear model cache before each test"""
        KeywordExpander._model_cache.clear()

    @patch("gensim.downloader")
    def test_basic_expansion(self, mock_downloader):
        """Test basic keyword expansion with known similar words"""
        # Create mock model with predefined similar words
        mock_model = MagicMock()
        mock_model.most_similar.return_value = [
            ("authenticate", 0.90),
            ("verify", 0.85),
            ("authorize", 0.82),
            ("validate", 0.78),
            ("login", 0.75),
        ]
        mock_downloader.load.return_value = mock_model

        expander = KeywordExpander(model_type="fasttext", verbose=False)
        result = expander.expand_keywords(keywords=["authentication"], top_n=3, threshold=0.7)

        # Should return top 3 words above threshold
        assert "authentication" in result
        assert len(result["authentication"]) == 3
        assert result["authentication"][0] == ("authenticate", 0.90)
        assert result["authentication"][1] == ("verify", 0.85)
        assert result["authentication"][2] == ("authorize", 0.82)

    @patch("gensim.downloader")
    def test_threshold_filtering(self, mock_downloader):
        """Test that threshold correctly filters out low-similarity words"""
        mock_model = MagicMock()
        mock_model.most_similar.return_value = [
            ("high_sim", 0.90),
            ("medium_sim", 0.75),
            ("low_sim", 0.60),
            ("very_low_sim", 0.40),
        ]
        mock_downloader.load.return_value = mock_model

        expander = KeywordExpander(model_type="fasttext", verbose=False)
        result = expander.expand_keywords(keywords=["test"], top_n=10, threshold=0.7)

        # Only words >= 0.7 should be returned
        assert len(result["test"]) == 2
        assert result["test"][0] == ("high_sim", 0.90)
        assert result["test"][1] == ("medium_sim", 0.75)

    @patch("gensim.downloader")
    def test_top_n_limiting(self, mock_downloader):
        """Test that top_n correctly limits number of results"""
        mock_model = MagicMock()
        # Return many high-similarity words
        mock_model.most_similar.return_value = [(f"similar{i}", 0.9 - i * 0.01) for i in range(20)]
        mock_downloader.load.return_value = mock_model

        expander = KeywordExpander(model_type="fasttext", verbose=False)
        result = expander.expand_keywords(keywords=["test"], top_n=5, threshold=0.0)

        # Should only return top 5 despite many available
        assert len(result["test"]) == 5

    @patch("gensim.downloader")
    def test_multiple_keywords(self, mock_downloader):
        """Test expansion of multiple keywords"""
        mock_model = MagicMock()

        def most_similar_side_effect(word, topn):
            if word == "database":
                return [("postgresql", 0.88), ("mysql", 0.85), ("storage", 0.81)]
            elif word == "cache":
                return [("redis", 0.87), ("caching", 0.84), ("memcache", 0.79)]
            return []

        mock_model.most_similar.side_effect = most_similar_side_effect
        mock_downloader.load.return_value = mock_model

        expander = KeywordExpander(model_type="fasttext", verbose=False)
        result = expander.expand_keywords(keywords=["database", "cache"], top_n=3, threshold=0.7)

        # Should expand both keywords
        assert "database" in result
        assert "cache" in result
        assert len(result["database"]) == 3
        assert len(result["cache"]) == 3
        assert result["database"][0] == ("postgresql", 0.88)
        assert result["cache"][0] == ("redis", 0.87)

    @patch("gensim.downloader")
    def test_out_of_vocabulary_keyword(self, mock_downloader):
        """Test handling of keywords not in model vocabulary"""
        mock_model = MagicMock()
        mock_model.most_similar.side_effect = KeyError("not in vocab")
        mock_downloader.load.return_value = mock_model

        expander = KeywordExpander(model_type="fasttext", verbose=False)
        result = expander.expand_keywords(keywords=["zzz_nonexistent"], top_n=3, threshold=0.7)

        # Should return empty list for OOV words
        assert "zzz_nonexistent" in result
        assert result["zzz_nonexistent"] == []

    @patch("gensim.downloader")
    def test_verbose_oov_warning(self, mock_downloader, capsys):
        """Test that verbose mode prints warning for OOV words"""
        mock_model = MagicMock()
        mock_model.most_similar.side_effect = KeyError("not in vocab")
        mock_downloader.load.return_value = mock_model

        expander = KeywordExpander(model_type="fasttext", verbose=True)
        result = expander.expand_keywords(keywords=["nonexistent"], top_n=3, threshold=0.7)

        captured = capsys.readouterr()
        assert "not in vocabulary" in captured.out

    @patch("gensim.downloader")
    def test_empty_keyword_list(self, mock_downloader):
        """Test expansion with empty keyword list"""
        mock_model = MagicMock()
        mock_downloader.load.return_value = mock_model

        expander = KeywordExpander(model_type="fasttext", verbose=False)
        result = expander.expand_keywords(keywords=[], top_n=3, threshold=0.7)

        assert result == {}

    @patch("gensim.downloader")
    def test_case_insensitive_expansion(self, mock_downloader):
        """Test that keywords are converted to lowercase for lookup"""
        mock_model = MagicMock()
        mock_model.most_similar.return_value = [("similar", 0.9)]
        mock_downloader.load.return_value = mock_model

        expander = KeywordExpander(model_type="fasttext", verbose=False)
        result = expander.expand_keywords(keywords=["DATABASE"], top_n=3, threshold=0.7)

        # Should convert to lowercase for lookup
        mock_model.most_similar.assert_called_with("database", topn=9)
        assert "DATABASE" in result


class TestGetModelInfo:
    """Tests for model info retrieval"""

    def setup_method(self):
        """Clear model cache before each test"""
        KeywordExpander._model_cache.clear()

    def test_get_model_info_before_load(self):
        """Test that get_model_info returns empty dict before model loads"""
        expander = KeywordExpander(model_type="fasttext", verbose=False)
        info = expander.get_model_info()
        assert info == {}

    @patch("gensim.downloader")
    def test_get_model_info_after_load(self, mock_downloader):
        """Test that get_model_info returns correct metadata after load"""
        # Create mock model with metadata
        mock_model = MagicMock()
        mock_model.key_to_index = {"word1": 0, "word2": 1, "word3": 2}
        mock_model.vector_size = 300
        mock_downloader.load.return_value = mock_model

        expander = KeywordExpander(model_type="fasttext", verbose=False)
        expander._load_model()

        info = expander.get_model_info()
        assert info["type"] == "fasttext"
        assert info["vocab_size"] == 3
        assert info["vector_size"] == 300


class TestModelCaching:
    """Tests for model caching behavior"""

    def setup_method(self):
        """Clear model cache before each test"""
        KeywordExpander._model_cache.clear()

    @patch("gensim.downloader")
    def test_cache_shared_across_instances(self, mock_downloader):
        """Test that model cache is shared across multiple instances"""
        mock_model = MagicMock()
        mock_downloader.load.return_value = mock_model

        # Load model in first instance
        expander1 = KeywordExpander(model_type="fasttext", verbose=False)
        expander1._load_model()

        assert mock_downloader.load.call_count == 1

        # Second instance should reuse cached model
        expander2 = KeywordExpander(model_type="fasttext", verbose=False)
        expander2._load_model()

        # Should not call load again
        assert mock_downloader.load.call_count == 1

        # Both should reference same cached model
        assert expander1._model is expander2._model

    @patch("gensim.downloader")
    def test_lazy_loading_on_first_expand(self, mock_downloader):
        """Test that model is lazy-loaded on first expand_keywords call"""
        mock_model = MagicMock()
        mock_model.most_similar.return_value = [("similar", 0.9)]
        mock_downloader.load.return_value = mock_model

        expander = KeywordExpander(model_type="fasttext", verbose=False)

        # Model should not be loaded yet
        assert expander._model is None
        assert mock_downloader.load.call_count == 0

        # First expand_keywords should trigger load
        expander.expand_keywords(["test"], top_n=3, threshold=0.7)

        assert expander._model is not None
        assert mock_downloader.load.call_count == 1
