"""Comprehensive test suite for ALL SCIP-supported languages.

This test suite verifies that Cicada correctly handles all languages that have
SCIP indexer implementations. It tests both implemented languages (which should
pass) and unimplemented languages (which should fail with xfail markers).

The test suite is designed to:
1. Document all SCIP-supported languages in one place
2. Verify implemented languages work correctly
3. Track progress on unimplemented languages (xfail tests become TODOs)
4. Ensure consistent behavior across all SCIP languages

SCIP Languages Reference:
- https://github.com/sourcegraph/scip
- https://scip.dev/
"""

import pytest
from pathlib import Path
from typing import Optional

from cicada.languages.scip.reader import SCIPReader
from cicada.languages.scip.converter import SCIPConverter
from cicada.languages import LanguageRegistry, LanguageNotSupportedError
from cicada.parsing.schema import UniversalIndexSchema

from tests.languages.scip.scip_languages import (
    SCIPLanguage,
    ImplementationStatus,
    SCIP_LANGUAGES,
    get_implemented_languages,
    get_unimplemented_languages,
    get_all_languages,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the fixtures directory path."""
    return Path(__file__).parent.parent.parent / "fixtures"


def load_scip_index(fixtures_dir: Path, fixture_name: str) -> Optional[dict]:
    """Load and convert a SCIP index for a fixture.

    Returns None if the index.scip file doesn't exist.
    """
    scip_file = fixtures_dir / fixture_name / "index.scip"
    if not scip_file.exists():
        return None

    reader = SCIPReader()
    scip_index = reader.read_index(scip_file)

    converter = SCIPConverter()
    return converter.convert(scip_index, scip_file.parent)


# =============================================================================
# Language Parametrization Helpers
# =============================================================================


def implemented_language_ids():
    """Get pytest IDs for implemented languages."""
    return [lang.name for lang in get_implemented_languages()]


def unimplemented_language_ids():
    """Get pytest IDs for unimplemented languages."""
    return [lang.name for lang in get_unimplemented_languages()]


def all_language_ids():
    """Get pytest IDs for all languages."""
    return [lang.name for lang in get_all_languages()]


# =============================================================================
# IMPLEMENTED LANGUAGES TESTS (Should PASS)
# =============================================================================


class TestImplementedLanguages:
    """Tests for languages that ARE implemented in Cicada.

    These tests should all PASS. If any fail, it indicates a regression
    in the SCIP support for that language.
    """

    @pytest.mark.parametrize(
        "language", get_implemented_languages(), ids=implemented_language_ids()
    )
    def test_language_is_registered(self, language: SCIPLanguage):
        """Verify the language is registered in LanguageRegistry."""
        assert LanguageRegistry.is_language_supported(
            language.name
        ), f"Language '{language.display_name}' is marked as implemented but not registered"

    @pytest.mark.parametrize(
        "language", get_implemented_languages(), ids=implemented_language_ids()
    )
    def test_indexer_can_be_retrieved(self, language: SCIPLanguage):
        """Verify we can get an indexer for the language."""
        indexer = LanguageRegistry.get_indexer(language.name)
        assert indexer is not None
        assert indexer.get_language_name() == language.name

    @pytest.mark.parametrize(
        "language", get_implemented_languages(), ids=implemented_language_ids()
    )
    def test_formatter_can_be_retrieved(self, language: SCIPLanguage):
        """Verify we can get a formatter for the language."""
        formatter = LanguageRegistry.get_formatter(language.name)
        assert formatter is not None

    @pytest.mark.parametrize(
        "language", get_implemented_languages(), ids=implemented_language_ids()
    )
    def test_config_exists(self, language: SCIPLanguage):
        """Verify language config exists and has correct values."""
        config = LanguageRegistry.get_config(language.name)
        assert config is not None
        assert config.language == language.name

        # Check file extensions match
        for ext in language.file_extensions:
            assert (
                ext in config.file_extensions
            ), f"Extension {ext} not in config for {language.display_name}"

    @pytest.mark.parametrize(
        "language", get_implemented_languages(), ids=implemented_language_ids()
    )
    def test_fixture_exists(self, language: SCIPLanguage, fixtures_dir: Path):
        """Verify the language has a test fixture."""
        if language.fixture_dir is None:
            pytest.skip(f"No fixture directory defined for {language.display_name}")

        fixture_path = fixtures_dir / language.fixture_dir
        assert (
            fixture_path.exists()
        ), f"Fixture directory '{language.fixture_dir}' does not exist for {language.display_name}"

    @pytest.mark.parametrize(
        "language", get_implemented_languages(), ids=implemented_language_ids()
    )
    def test_scip_index_exists(self, language: SCIPLanguage, fixtures_dir: Path):
        """Verify the language has a pre-generated SCIP index (skips if not present)."""
        if language.fixture_dir is None:
            pytest.skip(f"No fixture directory defined for {language.display_name}")

        scip_file = fixtures_dir / language.fixture_dir / "index.scip"
        if not scip_file.exists():
            pytest.skip(
                f"SCIP index not found for {language.display_name}. "
                f"Install {language.scip_indexer} and run 'make setup-scip' to generate it."
            )
        # If we get here, the index exists - test passes
        assert scip_file.exists()

    @pytest.mark.parametrize(
        "language", get_implemented_languages(), ids=implemented_language_ids()
    )
    def test_index_has_modules(self, language: SCIPLanguage, fixtures_dir: Path):
        """Verify the converted index has modules."""
        if language.fixture_dir is None:
            pytest.skip(f"No fixture directory defined for {language.display_name}")

        index = load_scip_index(fixtures_dir, language.fixture_dir)
        if index is None:
            pytest.skip(f"SCIP index not found for {language.display_name}")

        assert "modules" in index
        assert len(index["modules"]) > 0, f"No modules extracted for {language.display_name}"

    @pytest.mark.parametrize(
        "language", get_implemented_languages(), ids=implemented_language_ids()
    )
    def test_index_has_metadata(self, language: SCIPLanguage, fixtures_dir: Path):
        """Verify the converted index has proper metadata."""
        if language.fixture_dir is None:
            pytest.skip(f"No fixture directory defined for {language.display_name}")

        index = load_scip_index(fixtures_dir, language.fixture_dir)
        if index is None:
            pytest.skip(f"SCIP index not found for {language.display_name}")

        assert "metadata" in index
        metadata = index["metadata"]

        # Required metadata fields
        required_fields = ["indexed_at", "version", "total_modules", "total_functions"]
        for field in required_fields:
            assert field in metadata, f"Metadata missing '{field}' for {language.display_name}"

    @pytest.mark.parametrize(
        "language", get_implemented_languages(), ids=implemented_language_ids()
    )
    def test_index_has_calculator_class(self, language: SCIPLanguage, fixtures_dir: Path):
        """Verify the index contains the Calculator class/module."""
        if language.fixture_dir is None:
            pytest.skip(f"No fixture directory defined for {language.display_name}")

        index = load_scip_index(fixtures_dir, language.fixture_dir)
        if index is None:
            pytest.skip(f"SCIP index not found for {language.display_name}")

        # Look for Calculator (case-insensitive search)
        module_names = list(index["modules"].keys())
        calculator_found = any("calculator" in name.lower() for name in module_names)

        assert calculator_found, (
            f"Calculator class/module not found for {language.display_name}. "
            f"Found modules: {module_names}"
        )

    @pytest.mark.parametrize(
        "language", get_implemented_languages(), ids=implemented_language_ids()
    )
    def test_calculator_has_functions(self, language: SCIPLanguage, fixtures_dir: Path):
        """Verify the Calculator class has extracted functions."""
        if language.fixture_dir is None:
            pytest.skip(f"No fixture directory defined for {language.display_name}")

        index = load_scip_index(fixtures_dir, language.fixture_dir)
        if index is None:
            pytest.skip(f"SCIP index not found for {language.display_name}")

        # Find Calculator module
        calculator = None
        for name, module in index["modules"].items():
            if "calculator" in name.lower():
                calculator = module
                break

        if calculator is None:
            pytest.skip(f"Calculator not found for {language.display_name}")

        functions = calculator.get("functions", [])
        assert (
            len(functions) > 0
        ), f"No functions extracted from Calculator for {language.display_name}"

    @pytest.mark.parametrize(
        "language", get_implemented_languages(), ids=implemented_language_ids()
    )
    def test_functions_have_required_fields(self, language: SCIPLanguage, fixtures_dir: Path):
        """Verify functions have all required fields."""
        if language.fixture_dir is None:
            pytest.skip(f"No fixture directory defined for {language.display_name}")

        index = load_scip_index(fixtures_dir, language.fixture_dir)
        if index is None:
            pytest.skip(f"SCIP index not found for {language.display_name}")

        # Find Calculator module
        calculator = None
        for name, module in index["modules"].items():
            if "calculator" in name.lower():
                calculator = module
                break

        if calculator is None:
            pytest.skip(f"Calculator not found for {language.display_name}")

        functions = calculator.get("functions", [])
        if not functions:
            pytest.skip(f"No functions found for {language.display_name}")

        required_fields = ["name", "arity", "line", "type"]
        for func in functions:
            for field in required_fields:
                assert (
                    field in func
                ), f"Function missing '{field}' for {language.display_name}: {func}"

    @pytest.mark.parametrize(
        "language", get_implemented_languages(), ids=implemented_language_ids()
    )
    def test_schema_validation(self, language: SCIPLanguage, fixtures_dir: Path):
        """Verify the index passes strict schema validation."""
        if language.fixture_dir is None:
            pytest.skip(f"No fixture directory defined for {language.display_name}")

        index = load_scip_index(fixtures_dir, language.fixture_dir)
        if index is None:
            pytest.skip(f"SCIP index not found for {language.display_name}")

        schema = UniversalIndexSchema.from_dict(index)
        is_valid, errors = schema.validate(strict=True)

        assert is_valid, f"Schema validation failed for {language.display_name}: {errors}"

    @pytest.mark.parametrize(
        "language", get_implemented_languages(), ids=implemented_language_ids()
    )
    def test_visibility_detection(self, language: SCIPLanguage, fixtures_dir: Path):
        """Verify public/private visibility is detected correctly."""
        if language.fixture_dir is None:
            pytest.skip(f"No fixture directory defined for {language.display_name}")

        index = load_scip_index(fixtures_dir, language.fixture_dir)
        if index is None:
            pytest.skip(f"SCIP index not found for {language.display_name}")

        # Collect all function types
        all_types = set()
        for module in index["modules"].values():
            for func in module.get("functions", []):
                if "type" in func:
                    all_types.add(func["type"])

        # Should use standard visibility types
        valid_types = {"public", "private"}
        assert all_types.issubset(
            valid_types | {""}
        ), f"Invalid visibility types for {language.display_name}: {all_types - valid_types}"


# =============================================================================
# UNIMPLEMENTED LANGUAGES TESTS (Should FAIL with xfail)
# =============================================================================


class TestUnimplementedLanguages:
    """Tests for languages that are NOT YET implemented in Cicada.

    These tests are marked with xfail - they document what SHOULD work
    once the language is implemented. When a language is implemented,
    remove the xfail marker and move tests to TestImplementedLanguages.

    Each failing test is effectively a TODO item for implementing that language.
    """

    @pytest.mark.parametrize(
        "language", get_unimplemented_languages(), ids=unimplemented_language_ids()
    )
    @pytest.mark.xfail(reason="Language not yet implemented in Cicada", strict=True)
    def test_language_is_registered(self, language: SCIPLanguage):
        """[XFAIL] Verify the language is registered in LanguageRegistry."""
        assert LanguageRegistry.is_language_supported(language.name), (
            f"Language '{language.display_name}' is not registered. "
            f"Implementation required: add to LanguageRegistry"
        )

    @pytest.mark.parametrize(
        "language", get_unimplemented_languages(), ids=unimplemented_language_ids()
    )
    @pytest.mark.xfail(reason="Language not yet implemented in Cicada", strict=True)
    def test_indexer_can_be_retrieved(self, language: SCIPLanguage):
        """[XFAIL] Verify we can get an indexer for the language."""
        indexer = LanguageRegistry.get_indexer(language.name)
        assert indexer is not None

    @pytest.mark.parametrize(
        "language", get_unimplemented_languages(), ids=unimplemented_language_ids()
    )
    @pytest.mark.xfail(reason="Language not yet implemented in Cicada", strict=True)
    def test_formatter_can_be_retrieved(self, language: SCIPLanguage):
        """[XFAIL] Verify we can get a formatter for the language."""
        formatter = LanguageRegistry.get_formatter(language.name)
        assert formatter is not None

    @pytest.mark.parametrize(
        "language", get_unimplemented_languages(), ids=unimplemented_language_ids()
    )
    @pytest.mark.xfail(reason="Language not yet implemented in Cicada", strict=True)
    def test_config_exists(self, language: SCIPLanguage):
        """[XFAIL] Verify language config exists."""
        config = LanguageRegistry.get_config(language.name)
        assert config is not None

    @pytest.mark.parametrize(
        "language", get_unimplemented_languages(), ids=unimplemented_language_ids()
    )
    def test_fixture_source_exists(self, language: SCIPLanguage, fixtures_dir: Path):
        """Verify the language has source files in its fixture (this SHOULD pass)."""
        if language.fixture_dir is None:
            pytest.skip(f"No fixture directory defined for {language.display_name}")

        fixture_path = fixtures_dir / language.fixture_dir
        if not fixture_path.exists():
            pytest.skip(f"Fixture directory not created yet for {language.display_name}")

        # Check for source files
        source_files = []
        for ext in language.file_extensions:
            source_files.extend(fixture_path.glob(f"*{ext}"))
            source_files.extend(fixture_path.glob(f"**/*{ext}"))

        assert len(source_files) > 0, (
            f"No source files ({language.file_extensions}) found in "
            f"fixture for {language.display_name}"
        )


# =============================================================================
# LANGUAGE COVERAGE TESTS
# =============================================================================


class TestLanguageCoverage:
    """Tests to ensure all SCIP languages are tracked and documented."""

    def test_all_major_scip_languages_defined(self):
        """Verify all major SCIP languages are defined in our registry."""
        # These are the production-ready SCIP indexers from Sourcegraph
        expected_languages = {
            "python",
            "typescript",
            "javascript",
            "rust",
            "go",
            "java",
            "scala",
            "c",
            "cpp",
            "ruby",
            "csharp",
        }

        defined_languages = set(SCIP_LANGUAGES.keys())
        missing = expected_languages - defined_languages

        assert not missing, (
            f"Missing SCIP language definitions: {missing}. "
            f"Add these to SCIP_LANGUAGES in scip_languages.py"
        )

    def test_implemented_languages_count(self):
        """Track the number of implemented languages."""
        implemented = get_implemented_languages()
        unimplemented = get_unimplemented_languages()

        print(f"\nSCIP Language Implementation Status:")
        print(f"  Implemented: {len(implemented)} languages")
        print(f"  Unimplemented: {len(unimplemented)} languages")
        print(f"  Total: {len(SCIP_LANGUAGES)} languages")
        print(f"\nImplemented languages: {[l.name for l in implemented]}")
        print(f"Unimplemented languages: {[l.name for l in unimplemented]}")

        # This assertion is for documentation purposes
        assert (
            len(implemented) >= 4
        ), "At least 4 languages should be implemented (Python, TypeScript, JavaScript, Rust)"

    def test_all_implemented_languages_have_fixtures(self, fixtures_dir: Path):
        """Verify all implemented languages have test fixtures."""
        for language in get_implemented_languages():
            if language.fixture_dir:
                fixture_path = fixtures_dir / language.fixture_dir
                assert (
                    fixture_path.exists()
                ), f"Missing fixture for implemented language: {language.display_name}"

    def test_language_status_consistency(self):
        """Verify language status matches actual implementation."""
        for language in get_implemented_languages():
            assert (
                language.cicada_indexer_class is not None
            ), f"Implemented language {language.display_name} missing indexer class"

            # Verify the class is actually importable
            try:
                module_path, class_name = language.cicada_indexer_class.rsplit(".", 1)
                module = __import__(module_path, fromlist=[class_name])
                getattr(module, class_name)
            except (ImportError, AttributeError) as e:
                pytest.fail(f"Indexer class for {language.display_name} not importable: {e}")


# =============================================================================
# CROSS-LANGUAGE CONSISTENCY TESTS
# =============================================================================


class TestCrossLanguageConsistency:
    """Tests that verify consistent behavior across all implemented languages.

    These tests ensure the SCIP layer is a perfect abstraction that works
    identically for ALL SCIP-compatible languages.
    """

    def test_all_indexes_have_same_structure(self, fixtures_dir: Path):
        """Verify all implemented languages produce the same index structure."""
        implemented = get_implemented_languages()
        indexes = {}

        for language in implemented:
            if language.fixture_dir:
                index = load_scip_index(fixtures_dir, language.fixture_dir)
                if index:
                    indexes[language.name] = index

        if len(indexes) < 2:
            pytest.skip("Need at least 2 indexes to compare")

        # All indexes should have the same top-level keys
        first_lang = next(iter(indexes))
        expected_keys = set(indexes[first_lang].keys())

        for lang_name, index in indexes.items():
            actual_keys = set(index.keys())
            assert actual_keys == expected_keys, (
                f"Index structure differs for {lang_name}. "
                f"Expected: {expected_keys}, Got: {actual_keys}"
            )

    def test_all_indexes_have_calculator(self, fixtures_dir: Path):
        """Verify all implemented languages have a Calculator in their index."""
        for language in get_implemented_languages():
            if language.fixture_dir is None:
                continue

            index = load_scip_index(fixtures_dir, language.fixture_dir)
            if index is None:
                continue

            has_calculator = any("calculator" in name.lower() for name in index["modules"].keys())

            assert has_calculator, (
                f"No Calculator found for {language.display_name}. "
                f"Modules: {list(index['modules'].keys())}"
            )

    def test_function_types_are_standardized(self, fixtures_dir: Path):
        """Verify all languages use standardized function types."""
        valid_types = {"public", "private", ""}

        for language in get_implemented_languages():
            if language.fixture_dir is None:
                continue

            index = load_scip_index(fixtures_dir, language.fixture_dir)
            if index is None:
                continue

            for module_name, module in index["modules"].items():
                for func in module.get("functions", []):
                    func_type = func.get("type", "")
                    assert func_type in valid_types, (
                        f"Invalid function type '{func_type}' in "
                        f"{language.display_name}.{module_name}.{func.get('name')}"
                    )

    def test_no_language_leakage(self, fixtures_dir: Path):
        """Verify no language-specific concepts leak through the abstraction."""
        # Fields that should NOT appear in SCIP indexes
        forbidden_fields = {
            # Elixir-specific
            "defdelegate",
            "defmacro",
            "defstruct",
            "behaviours",
            "module_attributes",
            # Python-specific (if they were accidentally exposed)
            "decorators",
            "is_async",
            "is_generator",
            # TypeScript-specific
            "is_interface",
            "is_abstract",
            "generic_params",
        }

        for language in get_implemented_languages():
            if language.fixture_dir is None:
                continue

            index = load_scip_index(fixtures_dir, language.fixture_dir)
            if index is None:
                continue

            for module_name, module in index["modules"].items():
                module_fields = set(module.keys())
                leaked = module_fields & forbidden_fields
                assert (
                    not leaked
                ), f"Language-specific fields leaked for {language.display_name}: {leaked}"


# =============================================================================
# SCIP INDEXER INFORMATION
# =============================================================================


class TestSCIPIndexerInfo:
    """Tests that document SCIP indexer information for each language."""

    @pytest.mark.parametrize("language", get_all_languages(), ids=all_language_ids())
    def test_scip_indexer_documented(self, language: SCIPLanguage):
        """Verify each language has its SCIP indexer documented."""
        assert language.scip_indexer, f"SCIP indexer not documented for {language.display_name}"
        assert (
            language.scip_indexer_repo
        ), f"SCIP indexer repo not documented for {language.display_name}"

    def test_print_scip_indexer_matrix(self):
        """Print a summary of all SCIP indexers and their status."""
        print("\n" + "=" * 80)
        print("SCIP LANGUAGE SUPPORT MATRIX")
        print("=" * 80)

        headers = ["Language", "SCIP Indexer", "Status", "Cicada Indexer"]
        col_widths = [12, 20, 15, 40]

        # Print header
        header_row = " | ".join(h.ljust(w) for h, w in zip(headers, col_widths))
        print(header_row)
        print("-" * len(header_row))

        # Print each language
        for language in get_all_languages():
            status = "IMPLEMENTED" if language.is_implemented else "NOT STARTED"
            indexer_class = language.cicada_indexer_class or "N/A"

            row = [
                language.display_name.ljust(col_widths[0]),
                language.scip_indexer.ljust(col_widths[1]),
                status.ljust(col_widths[2]),
                indexer_class[: col_widths[3]].ljust(col_widths[3]),
            ]
            print(" | ".join(row))

        print("=" * 80)

        # This always passes - it's for documentation
        assert True
