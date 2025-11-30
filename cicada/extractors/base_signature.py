"""Base class for function signature extraction from source code.

This abstraction allows co-change analysis to work across different languages
by providing language-specific implementations of signature extraction.
"""

from abc import ABC, abstractmethod


class FunctionSignatureExtractor(ABC):
    """Abstract base class for extracting function signatures from source code."""

    @abstractmethod
    def get_file_extensions(self) -> list[str]:
        """Return file extensions this extractor handles.

        Returns:
            List of extensions (e.g., [".py"] or [".ex", ".exs"])
        """
        ...

    @abstractmethod
    def extract_module_name(self, content: str, file_path: str) -> str | None:
        """Extract the module/class name from source code.

        Args:
            content: Source code content
            file_path: Path to the file (for fallback naming)

        Returns:
            Module/class name or None if not found
        """
        ...

    @abstractmethod
    def extract_function_signatures(self, content: str, module_name: str) -> set[str]:
        """Extract all function signatures from source code.

        Args:
            content: Source code content
            module_name: Module/class name for qualifying functions

        Returns:
            Set of function signatures (e.g., {"ModuleName.func_name/2"})
        """
        ...

    def filter_files(self, files: list[str]) -> list[str]:
        """Filter list to include only files this extractor handles.

        Args:
            files: List of file paths

        Returns:
            List of file paths matching this extractor's extensions
        """
        extensions = tuple(self.get_file_extensions())
        return [f for f in files if f.endswith(extensions)]


class SignatureExtractorRegistry:
    """Registry for language-specific signature extractors."""

    _extractors: dict[str, type[FunctionSignatureExtractor]] = {}

    @classmethod
    def register(cls, language: str, extractor_class: type[FunctionSignatureExtractor]) -> None:
        """Register a signature extractor for a language.

        Args:
            language: Language identifier (e.g., "elixir", "python")
            extractor_class: FunctionSignatureExtractor subclass
        """
        cls._extractors[language] = extractor_class

    @classmethod
    def get(cls, language: str) -> FunctionSignatureExtractor | None:
        """Get a signature extractor instance for a language.

        Args:
            language: Language identifier

        Returns:
            FunctionSignatureExtractor instance or None if not registered
        """
        extractor_class = cls._extractors.get(language)
        if extractor_class:
            return extractor_class()
        return None

    @classmethod
    def get_supported_languages(cls) -> list[str]:
        """Get list of languages with registered extractors.

        Returns:
            List of language identifiers
        """
        return list(cls._extractors.keys())
