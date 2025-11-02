"""
Comprehensive tests for keyword expansion using word embeddings.

Tests the KeywordExpander class for semantic keyword expansion
using GloVe and FastText embeddings.
"""

from unittest.mock import MagicMock, patch

import pytest

from cicada.keyword_expander import KeywordExpander


class TestKeywordExpanderInitialization:
    """Tests for KeywordExpander initialization"""

    def test_invalid_expansion_type(self):
        """Test that invalid expansion_type raises ValueError"""
        with pytest.raises(ValueError, match="Unsupported expansion_type: invalid"):
            KeywordExpander(expansion_type="invalid")

    def test_lemmi_initialization(self):
        """Test initialization with lemmi expansion type"""
        expander = KeywordExpander(expansion_type="lemmi", verbose=False)
        assert expander.expansion_type == "lemmi"
        assert expander.verbose is False
        assert expander._embedding_model is None

    def test_fasttext_initialization(self):
        """Test initialization with fasttext expansion type"""
        expander = KeywordExpander(expansion_type="fasttext", verbose=False)
        assert expander.expansion_type == "fasttext"
        assert expander.verbose is False
        assert expander._embedding_model is None

    def test_glove_initialization(self):
        """Test initialization with glove expansion type"""
        expander = KeywordExpander(expansion_type="glove", verbose=False)
        assert expander.expansion_type == "glove"
        assert expander.verbose is False
        assert expander._embedding_model is None

    def test_verbose_initialization(self):
        """Test initialization with verbose mode"""
        expander = KeywordExpander(expansion_type="fasttext", verbose=True)
        assert expander.verbose is True


class TestKeywordExpanderModelLoading:
    """Tests for model loading functionality"""

    def setup_method(self):
        """Clear model cache before each test"""
        KeywordExpander._model_cache.clear()

    @patch("cicada.keyword_expander.KeywordExpander._load_embedding_model")
    def test_model_loads_successfully(self, mock_load):
        """Test that model loads successfully on first use"""
        # Create mock model
        mock_model = MagicMock()
        mock_model.most_similar.return_value = [
            ("similar1", 0.9),
            ("similar2", 0.8),
        ]
        mock_load.return_value = mock_model

        # Create expander and expand (triggers lazy load)
        expander = KeywordExpander(expansion_type="fasttext", verbose=False)
        result = expander.expand_keywords(["test"])

        # Should have loaded the model
        mock_load.assert_called_once()

    def test_model_cached_after_first_load(self):
        """Test that model is cached and not reloaded"""
        with patch("gensim.downloader.load") as mock_gensim_load:
            # Create mock model
            mock_model = MagicMock()
            mock_model.most_similar.return_value = [("similar", 0.9)]
            mock_gensim_load.return_value = mock_model

            # First expander loads model
            expander1 = KeywordExpander(expansion_type="fasttext", verbose=False)
            expander1.expand_keywords(["test1"])

            # Second expander should use cached model (not call load again)
            expander2 = KeywordExpander(expansion_type="fasttext", verbose=False)
            expander2.expand_keywords(["test2"])

            # Should only load once (cached) - gensim.downloader.load called once
            assert mock_gensim_load.call_count == 1

    def test_import_error_when_gensim_missing(self):
        """Test that missing gensim raises helpful ImportError"""
        with patch.dict("sys.modules", {"gensim.downloader": None}):
            with patch("builtins.__import__", side_effect=ImportError("No module")):
                expander = KeywordExpander(expansion_type="fasttext", verbose=False)
                with pytest.raises(ImportError, match="gensim is required"):
                    expander._load_embedding_model()

    def test_verbose_model_loading(self, capsys):
        """Test that verbose mode prints progress messages"""
        with patch("gensim.downloader.load") as mock_gensim_load:
            mock_model = MagicMock()
            mock_model.most_similar.return_value = [("similar", 0.9)]
            mock_gensim_load.return_value = mock_model

            expander = KeywordExpander(expansion_type="fasttext", verbose=True)
            expander.expand_keywords(["test"])

            captured = capsys.readouterr()
            # Verbose output should mention fasttext (either loading or cached message)
            assert "fasttext" in (captured.out + captured.err).lower()


class TestKeywordExpansion:
    """Tests for keyword expansion functionality"""

    def setup_method(self):
        """Clear model cache and lemminflect cache before each test"""
        KeywordExpander._model_cache.clear()
        KeywordExpander._lemminflect_cache = None

    @patch("cicada.keyword_expander.KeywordExpander._load_embedding_model")
    def test_basic_expansion(self, mock_load):
        """Test basic keyword expansion returns sorted list"""
        mock_model = MagicMock()
        mock_model.most_similar.return_value = [
            ("database2", 0.90),
            ("database3", 0.85),
        ]
        mock_load.return_value = mock_model

        expander = KeywordExpander(expansion_type="fasttext", verbose=False)
        result = expander.expand_keywords(keywords=["database"])

        # Should return sorted list of strings
        assert isinstance(result, list)
        assert all(isinstance(w, str) for w in result)
        assert "database" in result

    @patch("cicada.keyword_expander.KeywordExpander._load_embedding_model")
    def test_threshold_filtering(self, mock_load):
        """Test that threshold correctly filters out low-similarity words"""
        mock_model = MagicMock()
        mock_model.most_similar.return_value = [
            ("high_sim", 0.90),
            ("medium_sim", 0.75),
            ("low_sim", 0.60),
        ]
        mock_load.return_value = mock_model

        expander = KeywordExpander(expansion_type="fasttext", verbose=False)
        result = expander.expand_keywords(keywords=["test"], top_n=10, threshold=0.7)

        # Only high_sim and medium_sim should be included (>= 0.7)
        assert "high_sim" in result
        assert "medium_sim" in result
        assert "low_sim" not in result

    @patch("cicada.keyword_expander.KeywordExpander._load_embedding_model")
    def test_top_n_limiting(self, mock_load):
        """Test that top_n correctly limits number of similar results"""
        mock_model = MagicMock()
        # Return many high-similarity words
        mock_model.most_similar.return_value = [(f"similar{i}", 0.95 - i * 0.01) for i in range(20)]
        mock_load.return_value = mock_model

        expander = KeywordExpander(expansion_type="fasttext", verbose=False)
        result = expander.expand_keywords(keywords=["test"], top_n=5, threshold=0.0)

        # Should include top_n similar words plus the keyword itself
        assert "test" in result
        # Other words should be there but limited by top_n
        similar_words = [w for w in result if w.startswith("similar")]
        assert len(similar_words) <= 5

    @patch("cicada.keyword_expander.KeywordExpander._load_embedding_model")
    def test_multiple_keywords(self, mock_load):
        """Test expansion of multiple keywords"""
        mock_model = MagicMock()

        def most_similar_side_effect(word, topn):
            if word == "database":
                return [("postgresql", 0.88), ("mysql", 0.85)]
            elif word == "cache":
                return [("redis", 0.87), ("memcache", 0.79)]
            return []

        mock_model.most_similar.side_effect = most_similar_side_effect
        mock_load.return_value = mock_model

        expander = KeywordExpander(expansion_type="fasttext", verbose=False)
        result = expander.expand_keywords(keywords=["database", "cache"], top_n=3, threshold=0.7)

        # Should include both original keywords and similar words
        assert "database" in result
        assert "cache" in result
        assert "postgresql" in result
        assert "redis" in result

    @patch("cicada.keyword_expander.KeywordExpander._load_embedding_model")
    def test_out_of_vocabulary_keyword(self, mock_load):
        """Test handling of keywords not in model vocabulary"""
        mock_model = MagicMock()
        mock_model.most_similar.side_effect = KeyError("not in vocab")
        mock_load.return_value = mock_model

        expander = KeywordExpander(expansion_type="fasttext", verbose=False)
        # Should not raise, just skip OOV words silently
        result = expander.expand_keywords(keywords=["zzz_nonexistent"], top_n=3, threshold=0.7)

        # Should still include the keyword itself
        assert isinstance(result, list)

    @patch("cicada.keyword_expander.KeywordExpander._load_embedding_model")
    def test_empty_keyword_list(self, mock_load):
        """Test expansion with empty keyword list"""
        expander = KeywordExpander(expansion_type="fasttext", verbose=False)
        result = expander.expand_keywords(keywords=[], top_n=3, threshold=0.7)

        assert result == []

    @patch("cicada.keyword_expander.KeywordExpander._load_embedding_model")
    def test_case_insensitive_expansion(self, mock_load):
        """Test that keywords are converted to lowercase"""
        mock_model = MagicMock()
        mock_model.most_similar.return_value = [("similar", 0.9)]
        mock_load.return_value = mock_model

        expander = KeywordExpander(expansion_type="fasttext", verbose=False)
        result = expander.expand_keywords(keywords=["DATABASE"], top_n=3, threshold=0.7)

        # Should lowercase the keyword
        assert "database" in result
        assert "DATABASE" not in result


class TestGetModelInfo:
    """Tests for get_expansion_info"""

    def setup_method(self):
        """Clear model cache before each test"""
        KeywordExpander._model_cache.clear()

    def test_get_expansion_info_before_load(self):
        """Test that get_expansion_info returns type before model loads"""
        expander = KeywordExpander(expansion_type="fasttext", verbose=False)
        info = expander.get_expansion_info()
        assert info["type"] == "fasttext"

    @patch("cicada.keyword_expander.KeywordExpander._load_embedding_model")
    def test_get_expansion_info_after_load(self, mock_load):
        """Test that get_expansion_info returns metadata after load"""
        # Create mock model with metadata
        mock_model = MagicMock()
        mock_model.key_to_index = {"word1": 0, "word2": 1, "word3": 2}
        mock_model.vector_size = 300
        mock_load.return_value = mock_model

        expander = KeywordExpander(expansion_type="fasttext", verbose=False)
        expander.expand_keywords(["test"])

        info = expander.get_expansion_info()
        assert info["type"] == "fasttext"
        assert info["embedding_vocab_size"] == 3
        assert info["embedding_vector_size"] == 300


class TestModelCaching:
    """Tests for model caching behavior"""

    def setup_method(self):
        """Clear model cache before each test"""
        KeywordExpander._model_cache.clear()

    def test_cache_shared_across_instances(self):
        """Test that model cache is shared across multiple instances"""
        with patch("gensim.downloader.load") as mock_gensim_load:
            mock_model = MagicMock()
            mock_model.most_similar.return_value = [("similar", 0.9)]
            mock_gensim_load.return_value = mock_model

            # Load model in first instance
            expander1 = KeywordExpander(expansion_type="fasttext", verbose=False)
            expander1.expand_keywords(["test1"])

            assert mock_gensim_load.call_count == 1

            # Second instance should reuse cached model
            expander2 = KeywordExpander(expansion_type="fasttext", verbose=False)
            expander2.expand_keywords(["test2"])

            # Should not load again (cached)
            assert mock_gensim_load.call_count == 1

    @patch("cicada.keyword_expander.KeywordExpander._load_embedding_model")
    def test_lazy_loading_on_first_expand(self, mock_load):
        """Test that model is lazy-loaded on first expand_keywords call"""
        mock_model = MagicMock()
        mock_model.most_similar.return_value = [("similar", 0.9)]
        mock_load.return_value = mock_model

        expander = KeywordExpander(expansion_type="fasttext", verbose=False)

        # Model should not be loaded yet
        assert expander._embedding_model is None
        assert mock_load.call_count == 0

        # First expand_keywords should trigger load
        expander.expand_keywords(["test"], top_n=3, threshold=0.7)

        assert expander._embedding_model is not None
        assert mock_load.call_count == 1
