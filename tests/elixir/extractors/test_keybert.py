"""
Comprehensive tests for KeyBERT keyword extraction

Tests the KeyBERTExtractor class for semantic keyword extraction
using transformer-based embeddings.
"""

from unittest.mock import MagicMock, patch

import pytest

from cicada.extractors.keybert import KeyBERTExtractor
from cicada.utils import extract_code_identifiers


class TestKeyBERTExtractorInitialization:
    """Tests for KeyBERTExtractor initialization"""

    @patch("cicada.extractors.keybert.KeyBERTExtractor._KeyBERT", None)
    def test_keybert_import_failure(self):
        """Test that missing KeyBERT raises helpful ImportError"""
        with patch.dict("sys.modules", {"keybert": None}):
            with patch("builtins.__import__", side_effect=ImportError("No module")):
                with pytest.raises(
                    ImportError, match=r"KeyBERT is not installed[\s\S]*uv add keybert"
                ):
                    KeyBERTExtractor(verbose=False)

    def test_initialization_success(self):
        """Test successful KeyBERTExtractor initialization"""
        mock_keybert_class = MagicMock()
        mock_keybert_instance = MagicMock()
        mock_keybert_class.return_value = mock_keybert_instance

        with patch("cicada.extractors.keybert.KeyBERTExtractor._KeyBERT", None):
            with patch("builtins.__import__") as mock_import:

                def import_side_effect(name, *args, **kwargs):
                    if name == "keybert":
                        module = MagicMock()
                        module.KeyBERT = mock_keybert_class
                        return module
                    return MagicMock()

                mock_import.side_effect = import_side_effect

                extractor = KeyBERTExtractor(verbose=False)

                # Should use single model name
                assert extractor.verbose is False
                # Model should be initialized with the configured model
                mock_keybert_class.assert_called_once_with(model="BAAI/bge-small-en-v1.5")

    def test_initialization_verbose_output(self, capsys):
        """Test verbose output during initialization"""
        mock_keybert_class = MagicMock()
        mock_keybert_instance = MagicMock()
        mock_keybert_class.return_value = mock_keybert_instance

        with patch("cicada.extractors.keybert.KeyBERTExtractor._KeyBERT", None):
            with patch("builtins.__import__") as mock_import:

                def import_side_effect(name, *args, **kwargs):
                    if name == "keybert":
                        module = MagicMock()
                        module.KeyBERT = mock_keybert_class
                        return module
                    return MagicMock()

                mock_import.side_effect = import_side_effect

                KeyBERTExtractor(verbose=True)

                captured = capsys.readouterr()
                assert "Loading KeyBERT model" in captured.err
                assert "BAAI/bge-small-en-v1.5" in captured.err
                assert "Model loaded successfully" in captured.err

    def test_model_loading_failure(self):
        """Test that model loading failure raises RuntimeError"""
        mock_keybert_class = MagicMock()
        mock_keybert_class.side_effect = Exception("Model download failed")

        with patch("cicada.extractors.keybert.KeyBERTExtractor._KeyBERT", None):
            with patch("builtins.__import__") as mock_import:

                def import_side_effect(name, *args, **kwargs):
                    if name == "keybert":
                        module = MagicMock()
                        module.KeyBERT = mock_keybert_class
                        return module
                    return MagicMock()

                mock_import.side_effect = import_side_effect

                with pytest.raises(RuntimeError, match="Failed to load KeyBERT model"):
                    KeyBERTExtractor(verbose=False)


class TestCodeIdentifierExtraction:
    """Tests for code identifier extraction functionality"""

    def test_extract_camel_case_identifiers(self):
        """Test extraction of camelCase identifiers"""
        text = "The getUserData function retrieves user information"
        identifiers, split_words = extract_code_identifiers(text)

        assert "getUserData" in identifiers
        assert "get" in split_words
        assert "user" in split_words
        assert "data" in split_words

    def test_extract_pascal_case_identifiers(self):
        """Test extraction of PascalCase identifiers"""
        text = "The UserController handles user operations"
        identifiers, split_words = extract_code_identifiers(text)

        assert "UserController" in identifiers
        assert "user" in split_words
        assert "controller" in split_words

    def test_extract_snake_case_identifiers(self):
        """Test extraction of snake_case identifiers"""
        text = "The get_user_data function is important"
        identifiers, split_words = extract_code_identifiers(text)

        assert "get_user_data" in identifiers
        assert "get" in split_words
        assert "user" in split_words
        assert "data" in split_words

    def test_extract_uppercase_acronyms(self):
        """Test extraction of all-uppercase acronyms"""
        text = "Using HTTP and API for the SQL database"
        identifiers, split_words = extract_code_identifiers(text)

        assert "HTTP" in identifiers
        assert "API" in identifiers
        assert "SQL" in identifiers

    def test_extract_mixed_patterns(self):
        """Test extraction of mixed case patterns"""
        text = "HTTPServer handles requests using XMLParser and PostgreSQL"
        identifiers, split_words = extract_code_identifiers(text)

        assert "HTTPServer" in identifiers
        assert "XMLParser" in identifiers
        assert "PostgreSQL" in identifiers

        # Check split words
        assert "http" in split_words
        assert "server" in split_words
        assert "xml" in split_words
        assert "parser" in split_words
        assert "postgre" in split_words
        assert "sql" in split_words

    def test_identifiers_deduplication(self):
        """Test that duplicate identifiers are removed"""
        text = "getUserData uses getUserData to getUserData"
        identifiers, split_words = extract_code_identifiers(text)

        # Should have only one instance of getUserData
        assert identifiers.count("getUserData") == 1

    def test_split_words_deduplication(self):
        """Test that duplicate split words are removed"""
        text = "getUserData and setUserData and UserModel"
        identifiers, split_words = extract_code_identifiers(text)

        # "user" should appear only once in split_words despite multiple occurrences
        assert split_words.count("user") == 1

    def test_empty_text_returns_empty_lists(self):
        """Test that empty text returns empty lists"""
        identifiers, split_words = extract_code_identifiers("")
        assert identifiers == []
        assert split_words == []


class TestExtractKeywordsSimple:
    """Tests for extract_keywords_simple method"""

    def _create_mock_extractor(self):
        """Create a mock KeyBERTExtractor with mocked kw_model"""
        extractor = KeyBERTExtractor.__new__(KeyBERTExtractor)
        extractor.verbose = False
        extractor.kw_model = MagicMock()
        return extractor

    def test_extract_keywords_simple_basic(self):
        """Test basic keyword extraction"""
        extractor = self._create_mock_extractor()

        # Mock KeyBERT to return specific keywords
        extractor.kw_model.extract_keywords.return_value = [
            ("authentication", 0.8),
            ("user", 0.6),
            ("validate", 0.5),
        ]

        text = "This function validates user authentication credentials"
        keywords = extractor.extract_keywords_simple(text, top_n=10)

        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert "authentication" in keywords
        assert "user" in keywords

    def test_extract_keywords_simple_empty_text(self):
        """Test extraction with empty text"""
        extractor = self._create_mock_extractor()

        assert extractor.extract_keywords_simple("", top_n=5) == []
        assert extractor.extract_keywords_simple("   ", top_n=5) == []
        assert extractor.extract_keywords_simple(None, top_n=5) == []

    def test_extract_keywords_simple_top_n(self):
        """Test that top_n parameter is respected"""
        extractor = self._create_mock_extractor()

        # Mock KeyBERT to return many keywords
        mock_keywords = [(f"keyword{i}", 1.0 - i * 0.1) for i in range(20)]
        extractor.kw_model.extract_keywords.return_value = mock_keywords

        text = "Sample text with many keywords"
        keywords = extractor.extract_keywords_simple(text, top_n=5)

        assert len(keywords) <= 5

    def test_extract_keywords_simple_error_handling(self, capsys):
        """Test error handling during extraction"""
        extractor = self._create_mock_extractor()
        extractor.verbose = True

        # Make extract_keywords raise an exception
        with patch.object(extractor, "extract_keywords", side_effect=Exception("Error")):
            result = extractor.extract_keywords_simple("test text", top_n=5)

            assert result == []
            captured = capsys.readouterr()
            assert "Warning: Keyword extraction failed" in captured.err

    def test_extract_keywords_simple_error_non_verbose(self):
        """Test error handling doesn't print when verbose=False"""
        extractor = self._create_mock_extractor()
        extractor.verbose = False

        with patch.object(extractor, "extract_keywords", side_effect=Exception("Error")):
            result = extractor.extract_keywords_simple("test text", top_n=5)
            assert result == []


class TestExtractKeywords:
    """Tests for full extract_keywords method"""

    def _create_mock_extractor(self):
        """Create a mock KeyBERTExtractor with mocked kw_model"""
        extractor = KeyBERTExtractor.__new__(KeyBERTExtractor)
        extractor.verbose = False
        extractor.kw_model = MagicMock()
        return extractor

    def test_extract_keywords_empty_text(self):
        """Test extraction with empty text returns proper structure"""
        extractor = self._create_mock_extractor()

        result = extractor.extract_keywords("", top_n=10)

        assert isinstance(result, dict)
        assert result["top_keywords"] == []
        assert result["code_identifiers"] == []
        assert result["code_split_words"] == []
        assert result["stats"]["total_tokens"] == 0

    def test_extract_keywords_structure(self):
        """Test that extraction returns proper dictionary structure"""
        extractor = self._create_mock_extractor()

        # Mock KeyBERT extraction
        extractor.kw_model.extract_keywords.return_value = [
            ("database", 0.7),
            ("server", 0.6),
        ]

        text = "Using PostgreSQL database for storage"
        result = extractor.extract_keywords(text, top_n=10)

        assert isinstance(result, dict)
        assert "top_keywords" in result
        assert "code_identifiers" in result
        assert "code_split_words" in result
        assert "tf_scores" in result
        assert "stats" in result

    def test_extract_keywords_stats_calculation(self):
        """Test statistics calculation"""
        extractor = self._create_mock_extractor()

        extractor.kw_model.extract_keywords.return_value = []

        text = "This is a simple test. It has two sentences!"
        result = extractor.extract_keywords(text, top_n=10)

        stats = result["stats"]
        assert stats["total_tokens"] > 0
        assert stats["total_words"] > 0
        assert stats["unique_words"] > 0
        assert stats["sentences"] == 2

    def test_code_identifier_10x_weight(self):
        """Test that code identifiers get 10x weight boost"""
        extractor = self._create_mock_extractor()

        # Mock KeyBERT to return lowercase "postgresql" with score 0.5
        extractor.kw_model.extract_keywords.return_value = [
            ("postgresql", 0.5),
            ("database", 0.4),
        ]

        text = "Using PostgreSQL database for storage"
        result = extractor.extract_keywords(text, top_n=10)

        keyword_dict = dict(result["top_keywords"])

        # PostgreSQL identifier should be boosted 10x: 0.5 * 10 = 5.0
        assert "postgresql" in keyword_dict
        assert keyword_dict["postgresql"] == pytest.approx(5.0, rel=0.1)

    def test_code_split_words_3x_weight(self):
        """Test that code split words get 3x weight boost"""
        extractor = self._create_mock_extractor()

        # Mock KeyBERT to return split words
        extractor.kw_model.extract_keywords.return_value = [
            ("postgre", 0.3),
            ("sql", 0.3),
            ("database", 0.4),
        ]

        text = "Using PostgreSQL database"
        result = extractor.extract_keywords(text, top_n=10)

        keyword_dict = dict(result["top_keywords"])

        # "postgre" and "sql" are split words from PostgreSQL, should get 3x: 0.3 * 3 = 0.9
        assert "postgre" in keyword_dict
        assert "sql" in keyword_dict
        assert keyword_dict["postgre"] == pytest.approx(0.9, rel=0.1)
        assert keyword_dict["sql"] == pytest.approx(0.9, rel=0.1)

    def test_code_identifiers_not_in_keybert_results(self):
        """Test that code identifiers not found by KeyBERT get base score"""
        extractor = self._create_mock_extractor()

        # Mock KeyBERT to NOT return "getUserData"
        extractor.kw_model.extract_keywords.return_value = [
            ("function", 0.5),
        ]

        text = "The getUserData function"
        result = extractor.extract_keywords(text, top_n=10)

        keyword_dict = dict(result["top_keywords"])

        # getUserData not in KeyBERT results, should get base score 0.5 * 10 = 5.0
        assert "getuserdata" in keyword_dict
        assert keyword_dict["getuserdata"] == pytest.approx(5.0, rel=0.1)

    def test_top_keywords_sorted_by_score(self):
        """Test that top keywords are sorted by weighted score"""
        extractor = self._create_mock_extractor()

        extractor.kw_model.extract_keywords.return_value = [
            ("database", 0.5),
            ("server", 0.4),
            ("storage", 0.3),
        ]

        text = "Using PostgreSQL database server for storage"
        result = extractor.extract_keywords(text, top_n=10)

        # Scores should be in descending order
        scores = [score for _, score in result["top_keywords"]]
        assert scores == sorted(scores, reverse=True)

    def test_top_n_parameter(self):
        """Test that top_n parameter limits results"""
        extractor = self._create_mock_extractor()

        # Return many keywords
        mock_keywords = [(f"keyword{i}", 1.0 - i * 0.05) for i in range(30)]
        extractor.kw_model.extract_keywords.return_value = mock_keywords

        text = "Text with many potential keywords"
        result = extractor.extract_keywords(text, top_n=5)

        assert len(result["top_keywords"]) <= 5

    def test_keybert_extraction_failure(self, capsys):
        """Test handling of KeyBERT extraction failures"""
        extractor = self._create_mock_extractor()
        extractor.verbose = True

        # Make KeyBERT raise an exception
        extractor.kw_model.extract_keywords.side_effect = Exception("Model error")

        text = "Test text"
        result = extractor.extract_keywords(text, top_n=10)

        # Should still return valid structure
        assert isinstance(result, dict)
        assert "top_keywords" in result

        captured = capsys.readouterr()
        assert "Warning: KeyBERT extraction failed" in captured.err

    def test_keybert_extraction_failure_non_verbose(self):
        """Test that failures don't print when verbose=False"""
        extractor = self._create_mock_extractor()
        extractor.verbose = False

        extractor.kw_model.extract_keywords.side_effect = Exception("Model error")

        text = "Test text"
        result = extractor.extract_keywords(text, top_n=10)

        assert isinstance(result, dict)

    def test_code_identifiers_in_result(self):
        """Test that code identifiers are included in results"""
        extractor = self._create_mock_extractor()

        extractor.kw_model.extract_keywords.return_value = []

        text = "The HTTPServer and getUserData function"
        result = extractor.extract_keywords(text, top_n=10)

        assert "HTTPServer" in result["code_identifiers"]
        assert "getUserData" in result["code_identifiers"]

    def test_code_split_words_in_result(self):
        """Test that code split words are included in results"""
        extractor = self._create_mock_extractor()

        extractor.kw_model.extract_keywords.return_value = []

        text = "The HTTPServer function"
        result = extractor.extract_keywords(text, top_n=10)

        assert "http" in result["code_split_words"]
        assert "server" in result["code_split_words"]

    def test_keybert_requests_3x_candidates(self):
        """Test that KeyBERT is called with 3x top_n for candidate selection"""
        extractor = self._create_mock_extractor()

        extractor.kw_model.extract_keywords.return_value = []

        text = "Sample text"
        extractor.extract_keywords(text, top_n=10)

        # Verify KeyBERT was called with top_n=30 (3x of 10)
        extractor.kw_model.extract_keywords.assert_called_once()
        call_args = extractor.kw_model.extract_keywords.call_args
        assert call_args[1]["top_n"] == 30

    def test_single_word_keyphrases_only(self):
        """Test that only single words are extracted (ngram_range=1,1)"""
        extractor = self._create_mock_extractor()

        extractor.kw_model.extract_keywords.return_value = []

        text = "Sample text"
        extractor.extract_keywords(text, top_n=10)

        # Verify KeyBERT was called with keyphrase_ngram_range=(1, 1)
        call_args = extractor.kw_model.extract_keywords.call_args
        assert call_args[1]["keyphrase_ngram_range"] == (1, 1)
