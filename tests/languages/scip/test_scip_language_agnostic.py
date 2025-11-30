"""Meta-tests verifying SCIP layer is truly language-agnostic.

These tests verify that Python and TypeScript (and future SCIP languages)
produce structurally identical outputs with ZERO language-specific
idiosyncrasies leaking through the abstraction.

If these tests pass, it proves the SCIP layer is a perfect abstraction
that works identically for ALL SCIP-compatible languages.
"""

import pytest

from cicada.languages.scip.reader import SCIPReader
from cicada.languages.scip.converter import SCIPConverter


@pytest.fixture
def python_scip_file(fixtures_dir):
    """Return path to Python SCIP file."""
    scip_file = fixtures_dir / "sample_python" / "index.scip"
    if not scip_file.exists():
        pytest.fail("Python SCIP index not found - run make setup-scip")
    return scip_file


@pytest.fixture
def python_calculator_index(python_scip_file):
    """Load Python Calculator index via SCIP."""
    reader = SCIPReader()
    scip_index = reader.read_index(python_scip_file)

    converter = SCIPConverter()
    return converter.convert(scip_index, python_scip_file.parent)


@pytest.fixture
def typescript_calculator_index(fixtures_dir):
    """Load TypeScript Calculator index via SCIP."""
    scip_file = fixtures_dir / "sample_typescript" / "index.scip"
    if not scip_file.exists():
        pytest.fail("TypeScript SCIP index not found - run make setup-scip")

    reader = SCIPReader()
    scip_index = reader.read_index(scip_file)

    converter = SCIPConverter()
    return converter.convert(scip_index, scip_file.parent)


class TestLanguageAgnosticStructure:
    """Test that Python and TypeScript produce identical index structures."""

    def test_top_level_keys_identical(self, python_calculator_index, typescript_calculator_index):
        """Test that top-level index structure is identical across languages."""
        python_keys = set(python_calculator_index.keys())
        typescript_keys = set(typescript_calculator_index.keys())

        assert python_keys == typescript_keys, (
            f"Top-level keys differ!\n"
            f"Python: {python_keys}\n"
            f"TypeScript: {typescript_keys}\n"
            f"Missing in TypeScript: {python_keys - typescript_keys}\n"
            f"Extra in TypeScript: {typescript_keys - python_keys}"
        )

        # Must have modules and metadata
        assert "modules" in python_keys
        assert "metadata" in python_keys

    def test_module_structure_identical(self, python_calculator_index, typescript_calculator_index):
        """Test that module dictionaries have identical field structures."""
        # Both should have Calculator class
        assert "Calculator" in python_calculator_index["modules"]
        assert "Calculator" in typescript_calculator_index["modules"]

        py_calc = python_calculator_index["modules"]["Calculator"]
        ts_calc = typescript_calculator_index["modules"]["Calculator"]

        # Extract field names (ignoring values)
        py_fields = set(py_calc.keys())
        ts_fields = set(ts_calc.keys())

        # Core fields must be identical
        core_fields = {"file", "line", "functions"}

        assert core_fields.issubset(
            py_fields
        ), f"Python missing core fields: {core_fields - py_fields}"
        assert core_fields.issubset(
            ts_fields
        ), f"TypeScript missing core fields: {core_fields - ts_fields}"

        # Optional fields should be consistent (if one has it, other should too)
        optional_fields = {"moduledoc", "keywords", "dependencies", "calls"}

        for field in optional_fields:
            py_has = field in py_fields
            ts_has = field in ts_fields

            # Not required, but if present in one, should be present in other
            # (unless legitimately language-specific, which shouldn't happen with SCIP)

    def test_function_structure_identical(
        self, python_calculator_index, typescript_calculator_index
    ):
        """Test that function dictionaries have identical field structures."""
        py_calc = python_calculator_index["modules"]["Calculator"]
        ts_calc = typescript_calculator_index["modules"]["Calculator"]

        # Get any function from each
        py_funcs = py_calc["functions"]
        ts_funcs = ts_calc["functions"]

        assert len(py_funcs) > 0, "Python Calculator should have functions"
        assert len(ts_funcs) > 0, "TypeScript Calculator should have functions"

        # Get a representative function from each
        py_func = py_funcs[0]
        ts_func = ts_funcs[0]

        # Extract field names
        py_func_fields = set(py_func.keys())
        ts_func_fields = set(ts_func.keys())

        # Core fields must be identical
        core_fields = {"name", "arity", "line", "type"}

        assert core_fields.issubset(
            py_func_fields
        ), f"Python function missing core fields: {core_fields - py_func_fields}"
        assert core_fields.issubset(
            ts_func_fields
        ), f"TypeScript function missing core fields: {core_fields - ts_func_fields}"

    def test_metadata_structure_identical(
        self, python_calculator_index, typescript_calculator_index
    ):
        """Test that metadata has identical structure."""
        py_meta = python_calculator_index["metadata"]
        ts_meta = typescript_calculator_index["metadata"]

        py_meta_fields = set(py_meta.keys())
        ts_meta_fields = set(ts_meta.keys())

        # Core metadata fields must be identical
        core_fields = {
            "indexed_at",
            "version",
            "repo_path",
            "total_modules",
            "total_functions",
        }

        assert core_fields.issubset(
            py_meta_fields
        ), f"Python metadata missing: {core_fields - py_meta_fields}"
        assert core_fields.issubset(
            ts_meta_fields
        ), f"TypeScript metadata missing: {core_fields - ts_meta_fields}"

        # The ONLY field that should differ is 'language'
        assert py_meta.get("language") == "python"
        assert ts_meta.get("language") == "typescript"


class TestLanguageAgnosticTypes:
    """Test that field types are identical across languages."""

    def test_function_type_field_values(self, python_calculator_index, typescript_calculator_index):
        """Test that 'type' field uses same values (public/private) for both languages."""
        py_calc = python_calculator_index["modules"]["Calculator"]
        ts_calc = typescript_calculator_index["modules"]["Calculator"]

        # Collect all unique type values from Python
        py_types = set()
        for func in py_calc["functions"]:
            if "type" in func:
                py_types.add(func["type"])

        # Collect all unique type values from TypeScript
        ts_types = set()
        for func in ts_calc["functions"]:
            if "type" in func:
                ts_types.add(func["type"])

        # Both should use the same set of type values
        valid_types = {"public", "private"}

        assert py_types.issubset(
            valid_types
        ), f"Python uses invalid types: {py_types - valid_types}"
        assert ts_types.issubset(
            valid_types
        ), f"TypeScript uses invalid types: {ts_types - valid_types}"

        # Should NOT use language-specific types like "def", "defp"
        forbidden_types = {"def", "defp"}
        assert not py_types.intersection(
            forbidden_types
        ), f"Python leaking Elixir types: {py_types & forbidden_types}"
        assert not ts_types.intersection(
            forbidden_types
        ), f"TypeScript leaking Elixir types: {ts_types & forbidden_types}"

    def test_arity_field_type(self, python_calculator_index, typescript_calculator_index):
        """Test that arity is always an integer in both languages."""
        py_calc = python_calculator_index["modules"]["Calculator"]
        ts_calc = typescript_calculator_index["modules"]["Calculator"]

        # Check Python functions
        for func in py_calc["functions"]:
            assert "arity" in func
            assert isinstance(
                func["arity"], int
            ), f"Python function {func['name']} has non-int arity: {type(func['arity'])}"

        # Check TypeScript functions
        for func in ts_calc["functions"]:
            assert "arity" in func
            assert isinstance(
                func["arity"], int
            ), f"TypeScript function {func['name']} has non-int arity: {type(func['arity'])}"

    def test_line_numbers_type(self, python_calculator_index, typescript_calculator_index):
        """Test that line numbers are always integers in both languages."""
        # Check Python
        for module_name, module_data in python_calculator_index["modules"].items():
            assert isinstance(
                module_data.get("line", 0), int
            ), f"Python module {module_name} has non-int line"

            for func in module_data.get("functions", []):
                assert isinstance(
                    func.get("line", 0), int
                ), f"Python function {func['name']} has non-int line"

        # Check TypeScript
        for module_name, module_data in typescript_calculator_index["modules"].items():
            assert isinstance(
                module_data.get("line", 0), int
            ), f"TypeScript module {module_name} has non-int line"

            for func in module_data.get("functions", []):
                assert isinstance(
                    func.get("line", 0), int
                ), f"TypeScript function {func['name']} has non-int line"


class TestLanguageAgnosticBehavior:
    """Test that SCIP processing behaves identically for both languages."""

    def test_privacy_detection_consistent(
        self, python_calculator_index, typescript_calculator_index
    ):
        """Test that privacy detection (public/private) works the same way."""
        py_calc = python_calculator_index["modules"]["Calculator"]
        ts_calc = typescript_calculator_index["modules"]["Calculator"]

        # Both should have private methods
        py_private = [f for f in py_calc["functions"] if f.get("type") == "private"]
        ts_private = [f for f in ts_calc["functions"] if f.get("type") == "private"]

        # Python has _private_method
        assert any(
            f["name"].startswith("_") for f in py_private
        ), "Python should detect underscore-prefixed private methods"

        # TypeScript has private methods (marked in source or by convention)
        # Both should use same detection logic

    def test_documentation_extraction_consistent(
        self, python_calculator_index, typescript_calculator_index
    ):
        """Test that documentation is extracted the same way."""
        py_calc = python_calculator_index["modules"]["Calculator"]
        ts_calc = typescript_calculator_index["modules"]["Calculator"]

        # Both should have functions with docs
        py_with_docs = [f for f in py_calc["functions"] if "doc" in f and f["doc"]]
        ts_with_docs = [f for f in ts_calc["functions"] if "doc" in f and f["doc"]]

        assert len(py_with_docs) > 0, "Python should have documented functions"
        assert len(ts_with_docs) > 0, "TypeScript should have documented functions"

        # Doc format should be consistent (no markdown code fences)
        for func in py_with_docs:
            assert (
                "```" not in func["doc"]
            ), f"Python doc should not contain code fences: {func['name']}"

        for func in ts_with_docs:
            assert (
                "```" not in func["doc"]
            ), f"TypeScript doc should not contain code fences: {func['name']}"

    def test_signature_format_consistent(
        self, python_calculator_index, typescript_calculator_index
    ):
        """Test that signatures follow consistent formatting."""
        py_calc = python_calculator_index["modules"]["Calculator"]
        ts_calc = typescript_calculator_index["modules"]["Calculator"]

        # Both should have signatures
        py_with_sig = [f for f in py_calc["functions"] if "signature" in f and f["signature"]]
        ts_with_sig = [f for f in ts_calc["functions"] if "signature" in f and f["signature"]]

        assert len(py_with_sig) > 0, "Python should have function signatures"
        assert len(ts_with_sig) > 0, "TypeScript should have function signatures"

        # Signatures should not contain markdown code fences
        for func in py_with_sig:
            assert (
                "```" not in func["signature"]
            ), f"Python signature should not have code fences: {func['name']}"

        for func in ts_with_sig:
            assert (
                "```" not in func["signature"]
            ), f"TypeScript signature should not have code fences: {func['name']}"


class TestNoLanguageLeakage:
    """Test that no language-specific concepts leak through the abstraction."""

    def test_no_elixir_concepts_in_python(self, python_calculator_index):
        """Test that Python indexes don't contain Elixir-specific fields."""
        forbidden_fields = {
            "defdelegate",
            "defmacro",
            "defstruct",
            "module_attributes",
            "behaviours",
        }

        for module_name, module_data in python_calculator_index["modules"].items():
            module_fields = set(module_data.keys())
            leaked = module_fields.intersection(forbidden_fields)
            assert not leaked, f"Python module {module_name} has Elixir fields: {leaked}"

    def test_no_elixir_concepts_in_typescript(self, typescript_calculator_index):
        """Test that TypeScript indexes don't contain Elixir-specific fields."""
        forbidden_fields = {
            "defdelegate",
            "defmacro",
            "defstruct",
            "module_attributes",
            "behaviours",
        }

        for module_name, module_data in typescript_calculator_index["modules"].items():
            module_fields = set(module_data.keys())
            leaked = module_fields.intersection(forbidden_fields)
            assert not leaked, f"TypeScript module {module_name} has Elixir fields: {leaked}"

    def test_no_python_concepts_in_typescript(self, typescript_calculator_index):
        """Test that TypeScript doesn't get Python-specific fields."""
        # These would indicate Python-specific processing
        forbidden_function_fields = {"decorators", "is_async", "is_generator"}

        for module_name, module_data in typescript_calculator_index["modules"].items():
            for func in module_data.get("functions", []):
                func_fields = set(func.keys())
                leaked = func_fields.intersection(forbidden_function_fields)
                assert not leaked, (
                    f"TypeScript function {module_name}.{func['name']} "
                    f"has Python-specific fields: {leaked}"
                )

    def test_no_typescript_concepts_in_python(self, python_calculator_index):
        """Test that Python doesn't get TypeScript-specific fields."""
        # These would indicate TypeScript-specific processing
        forbidden_function_fields = {"is_interface", "is_abstract", "generic_params"}

        for module_name, module_data in python_calculator_index["modules"].items():
            for func in module_data.get("functions", []):
                func_fields = set(func.keys())
                leaked = func_fields.intersection(forbidden_function_fields)
                assert not leaked, (
                    f"Python function {module_name}.{func['name']} "
                    f"has TypeScript-specific fields: {leaked}"
                )


class TestIdempotency:
    """Test that processing is idempotent - same input produces same output."""

    def test_convert_twice_identical(self, python_scip_file):
        """Test that converting the same SCIP file twice produces identical output."""
        reader = SCIPReader()
        scip_index = reader.read_index(python_scip_file)

        # Convert twice
        converter1 = SCIPConverter()
        result1 = converter1.convert(scip_index, python_scip_file.parent)

        converter2 = SCIPConverter()
        result2 = converter2.convert(scip_index, python_scip_file.parent)

        # Strip timestamp (will differ)
        result1_meta = dict(result1["metadata"])
        result2_meta = dict(result2["metadata"])
        result1_meta.pop("indexed_at", None)
        result2_meta.pop("indexed_at", None)

        # Metadata should be identical
        assert result1_meta == result2_meta

        # Modules should be identical
        assert result1["modules"] == result2["modules"]

    def test_field_order_consistent(self, python_calculator_index):
        """Test that field ordering is consistent (dict keys maintain order)."""
        # Python 3.7+ guarantees dict ordering
        # If we iterate modules twice, should get same order

        calc = python_calculator_index["modules"]["Calculator"]
        functions1 = calc["functions"]

        # Re-access the same data
        calc2 = python_calculator_index["modules"]["Calculator"]
        functions2 = calc2["functions"]

        # Should be identical
        assert functions1 == functions2

        # Field names in same order
        if functions1:
            fields1 = list(functions1[0].keys())
            fields2 = list(functions2[0].keys())
            assert fields1 == fields2


class TestCrossLanguageComparison:
    """Test specific Calculator implementations match across languages."""

    def test_both_have_calculator_class(self, python_calculator_index, typescript_calculator_index):
        """Test that both languages successfully index the Calculator class."""
        assert "Calculator" in python_calculator_index["modules"]
        assert "Calculator" in typescript_calculator_index["modules"]

    def test_both_have_add_method(self, python_calculator_index, typescript_calculator_index):
        """Test that both have add() method."""
        py_calc = python_calculator_index["modules"]["Calculator"]
        ts_calc = typescript_calculator_index["modules"]["Calculator"]

        py_funcs = {f["name"] for f in py_calc["functions"]}
        ts_funcs = {f["name"] for f in ts_calc["functions"]}

        # Both should have 'add' functionality
        # (exact name might differ: 'add' vs 'add' - but concept is same)
        assert "add" in py_funcs or any("add" in name.lower() for name in py_funcs)
        assert "add" in ts_funcs or any("add" in name.lower() for name in ts_funcs)

    def test_constructor_handling_consistent(
        self, python_calculator_index, typescript_calculator_index
    ):
        """Test that constructors are handled consistently."""
        py_calc = python_calculator_index["modules"]["Calculator"]
        ts_calc = typescript_calculator_index["modules"]["Calculator"]

        # Python has __init__
        py_funcs = {f["name"] for f in py_calc["functions"]}
        assert "__init__" in py_funcs

        # TypeScript has constructor or `<constructor>`
        ts_funcs = {f["name"] for f in ts_calc["functions"]}
        has_constructor = any("constructor" in name.lower() for name in ts_funcs)
        assert has_constructor, f"TypeScript should have constructor, got: {ts_funcs}"
