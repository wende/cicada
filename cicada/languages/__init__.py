"""
Language registry and factory for multi-language support.

Provides dynamic loading of language-specific parsers and indexers.
"""

from cicada.languages.base import BaseIndexer, BaseParser
from cicada.languages.formatter_interface import BaseLanguageFormatter
from cicada.parsing.language_config import LanguageConfig


class LanguageNotSupportedError(Exception):
    """Raised when a requested language is not supported."""


class LanguageRegistry:
    """
    Factory for creating language-specific parsers and indexers.

    This registry maintains mappings from language names to their implementations.
    Languages can be registered dynamically, and the registry handles lazy loading.
    """

    # Registry of language implementations
    # Format: language_name -> {'parser': parser_class_path, 'indexer': indexer_class_path, 'config': LanguageConfig}
    _languages: dict[str, dict] = {}

    # Cache for loaded classes to avoid repeated imports
    _parser_cache: dict[str, type[BaseParser]] = {}
    _indexer_cache: dict[str, type[BaseIndexer]] = {}
    _formatter_cache: dict[str, type[BaseLanguageFormatter]] = {}

    @classmethod
    def register_language(
        cls,
        language: str,
        parser_class: str | None,
        indexer_class: str,
        config: LanguageConfig | None = None,
        formatter_class: str | None = None,
    ):
        """
        Register a new language with its parser, indexer, and formatter.

        Args:
            language: Language identifier (e.g., 'elixir', 'python')
            parser_class: Full import path to parser class (e.g., 'cicada.languages.elixir.parser.ElixirParser') or None if not needed
            indexer_class: Full import path to indexer class
            config: Optional LanguageConfig with default settings
            formatter_class: Full import path to formatter class (e.g., 'cicada.languages.scip.formatter.PythonFormatter')
        """
        cls._languages[language] = {
            "parser": parser_class,
            "indexer": indexer_class,
            "config": config,
            "formatter": formatter_class,
        }

    @classmethod
    def _load_class(cls, class_path: str):
        """
        Dynamically import and return a class from its import path.

        Args:
            class_path: Full import path (e.g., 'cicada.languages.elixir.parser.ElixirParser')

        Returns:
            The imported class

        Raises:
            ImportError: If the class cannot be imported
        """
        module_path, class_name = class_path.rsplit(".", 1)
        module = __import__(module_path, fromlist=[class_name])
        return getattr(module, class_name)

    @classmethod
    def get_parser(cls, language: str) -> BaseParser:
        """
        Get a parser instance for the specified language.

        Args:
            language: Language identifier (e.g., 'elixir', 'python')

        Returns:
            Instance of the language-specific parser

        Raises:
            LanguageNotSupportedError: If language is not registered
        """
        if language not in cls._languages:
            supported = ", ".join(cls._languages.keys())
            raise LanguageNotSupportedError(
                f"Language '{language}' is not supported. Supported languages: {supported}"
            )

        # Check cache first
        if language in cls._parser_cache:
            parser_class = cls._parser_cache[language]
        else:
            # Load and cache the class
            parser_path = cls._languages[language]["parser"]
            parser_class = cls._load_class(parser_path)
            cls._parser_cache[language] = parser_class

        return parser_class()

    @classmethod
    def get_indexer(cls, language: str) -> BaseIndexer:
        """
        Get an indexer instance for the specified language.

        Args:
            language: Language identifier (e.g., 'elixir', 'python')

        Returns:
            Instance of the language-specific indexer

        Raises:
            LanguageNotSupportedError: If language is not registered
        """
        if language not in cls._languages:
            supported = ", ".join(cls._languages.keys())
            raise LanguageNotSupportedError(
                f"Language '{language}' is not supported. Supported languages: {supported}"
            )

        # Check cache first
        if language in cls._indexer_cache:
            indexer_class = cls._indexer_cache[language]
        else:
            # Load and cache the class
            indexer_path = cls._languages[language]["indexer"]
            indexer_class = cls._load_class(indexer_path)
            cls._indexer_cache[language] = indexer_class

        return indexer_class()

    @classmethod
    def get_config(cls, language: str) -> LanguageConfig | None:
        """
        Get the default configuration for a language.

        Args:
            language: Language identifier

        Returns:
            LanguageConfig if available, None otherwise

        Raises:
            LanguageNotSupportedError: If language is not registered
        """
        if language not in cls._languages:
            supported = ", ".join(cls._languages.keys())
            raise LanguageNotSupportedError(
                f"Language '{language}' is not supported. Supported languages: {supported}"
            )

        return cls._languages[language].get("config")

    @classmethod
    def get_formatter(cls, language: str) -> BaseLanguageFormatter:
        """
        Get a formatter instance for the specified language.

        Args:
            language: Language identifier (e.g., 'elixir', 'python')

        Returns:
            Instance of the language-specific formatter

        Raises:
            LanguageNotSupportedError: If language is not registered
            ValueError: If language has no formatter registered
        """
        if language not in cls._languages:
            supported = ", ".join(cls._languages.keys())
            raise LanguageNotSupportedError(
                f"Language '{language}' is not supported. Supported languages: {supported}"
            )

        formatter_path = cls._languages[language].get("formatter")
        if not formatter_path:
            raise ValueError(f"No formatter registered for language '{language}'")

        # Check cache first
        if language in cls._formatter_cache:
            formatter_class = cls._formatter_cache[language]
        else:
            # Load and cache the class
            formatter_class = cls._load_class(formatter_path)
            cls._formatter_cache[language] = formatter_class

        return formatter_class()

    @classmethod
    def get_supported_languages(cls) -> list[str]:
        """
        Get list of all supported language identifiers.

        Returns:
            List of language names (e.g., ['elixir', 'python'])
        """
        return list(cls._languages.keys())

    @classmethod
    def is_language_supported(cls, language: str) -> bool:
        """
        Check if a language is supported.

        Args:
            language: Language identifier to check

        Returns:
            True if language is registered, False otherwise
        """
        return language in cls._languages


# Register built-in languages

# Register Elixir
LanguageRegistry.register_language(
    language="elixir",
    parser_class="cicada.languages.elixir.parser.ElixirParser",
    indexer_class="cicada.indexer.ElixirIndexer",
    config=LanguageConfig.default_elixir(),
    formatter_class="cicada.languages.elixir.formatter.ElixirFormatter",
)

# Register Python (SCIP-based)
LanguageRegistry.register_language(
    language="python",
    parser_class=None,  # No parser needed for SCIP-based indexing
    indexer_class="cicada.languages.python.indexer.PythonSCIPIndexer",
    config=LanguageConfig.default_python(),
    formatter_class="cicada.languages.scip.formatter.PythonFormatter",
)

# Register TypeScript (SCIP-based)
LanguageRegistry.register_language(
    language="typescript",
    parser_class=None,  # No parser needed for SCIP-based indexing
    indexer_class="cicada.languages.typescript.indexer.TypeScriptSCIPIndexer",
    config=LanguageConfig.default_typescript(),
    formatter_class="cicada.languages.scip.formatter.TypeScriptFormatter",
)

# Register JavaScript (SCIP-based, uses same tool as TypeScript)
LanguageRegistry.register_language(
    language="javascript",
    parser_class=None,  # No parser needed for SCIP-based indexing
    indexer_class="cicada.languages.typescript.indexer.JavaScriptSCIPIndexer",
    config=LanguageConfig.default_javascript(),
    formatter_class="cicada.languages.scip.formatter.JavaScriptFormatter",
)

# Register Rust (SCIP-based)
LanguageRegistry.register_language(
    language="rust",
    parser_class=None,  # No parser needed for SCIP-based indexing
    indexer_class="cicada.languages.rust.indexer.RustSCIPIndexer",
    config=LanguageConfig.default_rust(),
    formatter_class="cicada.languages.scip.formatter.RustFormatter",
)

# Register Erlang (tree-sitter based)
LanguageRegistry.register_language(
    language="erlang",
    parser_class="cicada.languages.erlang.parser.ErlangParser",
    indexer_class="cicada.languages.erlang.indexer.ErlangIndexer",
    config=LanguageConfig.default_erlang(),
    formatter_class="cicada.languages.erlang.formatter.ErlangFormatter",
)


# Global registry singleton
def get_language_registry() -> type[LanguageRegistry]:
    """
    Get the global language registry.

    Returns:
        The LanguageRegistry class (used as a singleton)
    """
    return LanguageRegistry


__all__ = [
    "LanguageRegistry",
    "LanguageNotSupportedError",
    "BaseParser",
    "BaseIndexer",
    "get_language_registry",
]
