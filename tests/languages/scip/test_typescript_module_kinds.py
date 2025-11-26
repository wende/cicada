"""Tests for module_kind detection in SCIP converter.

These tests verify that the SCIP converter correctly uses SCIP's SymbolInformation.kind
field to distinguish between different symbol types:
- type_alias: Type aliases (TypeAlias kind = 55)
- interface: Interfaces (Interface kind = 21)
- class: Classes (Class kind = 7)
- module: File-level modules (Module kind = 29)

This is language-agnostic - works for any language that SCIP supports.
"""

import pytest
from pathlib import Path

from cicada.languages.scip.reader import SCIPReader
from cicada.languages.scip.converter import SCIPConverter


@pytest.fixture
def typescript_index(fixtures_dir):
    """Load the TypeScript SCIP index for testing."""
    scip_path = fixtures_dir / "sample_typescript" / "index.scip"

    if not scip_path.exists():
        pytest.skip("TypeScript SCIP index not generated. Run tests/setup_fixtures.sh")

    reader = SCIPReader()
    scip_index = reader.read_index(scip_path)
    converter = SCIPConverter(verbose=False)
    return converter.convert(scip_index, scip_path.parent)


class TestModuleKindFromSCIPKind:
    """Test that SCIP converter uses SymbolInformation.kind field."""

    def test_all_modules_have_module_kind(self, typescript_index):
        """Every module should have a module_kind field."""
        for module_name, module_data in typescript_index["modules"].items():
            assert "module_kind" in module_data, f"{module_name} missing module_kind"
            assert module_data["module_kind"] in (
                "class",
                "type_alias",
                "interface",
                "module",
                "struct",
                "enum",
                "trait",
                "unknown",
            ), f"{module_name} has invalid module_kind: {module_data['module_kind']}"

    def test_file_module_has_module_kind_module(self, typescript_index):
        """File-level modules should have module_kind='module'."""
        modules = typescript_index["modules"]

        # File modules have type="module" (not "class")
        file_module = next(
            (m for m in modules.values() if m.get("type") == "module"),
            None,
        )

        if file_module is None:
            pytest.skip("No file-level module found in fixture")

        assert file_module.get("module_kind") == "module"

    def test_class_modules_have_class_kind(self, typescript_index):
        """Class modules should have appropriate module_kind."""
        modules = typescript_index["modules"]

        # Find modules with type="class"
        class_modules = [m for m in modules.values() if m.get("type") == "class"]

        if not class_modules:
            pytest.skip("No class modules found in fixture")

        # Each class module should have a valid module_kind
        for module in class_modules:
            kind = module.get("module_kind")
            # Classes in SCIP can be: class, interface, type_alias, struct, etc.
            assert kind in (
                "class",
                "interface",
                "type_alias",
                "struct",
                "enum",
                "trait",
                "unknown",
            ), f"Unexpected module_kind: {kind}"


class TestSCIPKindMapping:
    """Test the _scip_kind_to_module_kind mapping."""

    def test_scip_class_kind(self):
        """SCIP Class kind (7) should map to 'class'."""
        from cicada.languages.scip.converter import SCIPConverter

        converter = SCIPConverter()
        # SCIP Kind.Class = 7
        assert converter._scip_kind_to_module_kind(7) == "class"

    def test_scip_interface_kind(self):
        """SCIP Interface kind (21) should map to 'interface'."""
        from cicada.languages.scip.converter import SCIPConverter

        converter = SCIPConverter()
        # SCIP Kind.Interface = 21
        assert converter._scip_kind_to_module_kind(21) == "interface"

    def test_scip_type_alias_kind(self):
        """SCIP TypeAlias kind (55) should map to 'type_alias'."""
        from cicada.languages.scip.converter import SCIPConverter

        converter = SCIPConverter()
        # SCIP Kind.TypeAlias = 55
        assert converter._scip_kind_to_module_kind(55) == "type_alias"

    def test_scip_type_kind(self):
        """SCIP Type kind (54) should map to 'type_alias'."""
        from cicada.languages.scip.converter import SCIPConverter

        converter = SCIPConverter()
        # SCIP Kind.Type = 54 (generic type definition)
        assert converter._scip_kind_to_module_kind(54) == "type_alias"

    def test_scip_module_kind(self):
        """SCIP Module kind (29) should map to 'module'."""
        from cicada.languages.scip.converter import SCIPConverter

        converter = SCIPConverter()
        # SCIP Kind.Module = 29
        assert converter._scip_kind_to_module_kind(29) == "module"

    def test_scip_struct_kind(self):
        """SCIP Struct kind (49) should map to 'struct'."""
        from cicada.languages.scip.converter import SCIPConverter

        converter = SCIPConverter()
        # SCIP Kind.Struct = 49
        assert converter._scip_kind_to_module_kind(49) == "struct"

    def test_scip_enum_kind(self):
        """SCIP Enum kind (11) should map to 'enum'."""
        from cicada.languages.scip.converter import SCIPConverter

        converter = SCIPConverter()
        # SCIP Kind.Enum = 11
        assert converter._scip_kind_to_module_kind(11) == "enum"

    def test_scip_trait_kind(self):
        """SCIP Trait kind (53) should map to 'trait'."""
        from cicada.languages.scip.converter import SCIPConverter

        converter = SCIPConverter()
        # SCIP Kind.Trait = 53
        assert converter._scip_kind_to_module_kind(53) == "trait"

    def test_scip_unspecified_kind(self):
        """SCIP UnspecifiedKind (0) should map to 'unknown'."""
        from cicada.languages.scip.converter import SCIPConverter

        converter = SCIPConverter()
        # SCIP Kind.UnspecifiedKind = 0
        assert converter._scip_kind_to_module_kind(0) == "unknown"

    def test_unknown_kind_value(self):
        """Unknown SCIP kind values should map to 'unknown'."""
        from cicada.languages.scip.converter import SCIPConverter

        converter = SCIPConverter()
        # Some unknown value
        assert converter._scip_kind_to_module_kind(9999) == "unknown"


class TestModuledocFallback:
    """Test that moduledoc parsing works as fallback when SCIP kind is unspecified."""

    def test_interface_from_moduledoc(self):
        """Interface detected from moduledoc code fence."""
        from cicada.languages.scip.converter import SCIPConverter

        converter = SCIPConverter()
        moduledoc = "```ts\ninterface StoreApi\n```"
        assert converter._extract_module_kind_from_moduledoc(moduledoc) == "interface"

    def test_type_alias_from_moduledoc(self):
        """Type alias detected from moduledoc code fence."""
        from cicada.languages.scip.converter import SCIPConverter

        converter = SCIPConverter()
        moduledoc = "```ts\ntype SetStateInternal\n```"
        assert converter._extract_module_kind_from_moduledoc(moduledoc) == "type_alias"

    def test_class_from_moduledoc(self):
        """Class detected from moduledoc code fence."""
        from cicada.languages.scip.converter import SCIPConverter

        converter = SCIPConverter()
        moduledoc = "```ts\nclass Calculator\n```"
        assert converter._extract_module_kind_from_moduledoc(moduledoc) == "class"

    def test_enum_from_moduledoc(self):
        """Enum detected from moduledoc code fence."""
        from cicada.languages.scip.converter import SCIPConverter

        converter = SCIPConverter()
        moduledoc = "```ts\nenum Status\n```"
        assert converter._extract_module_kind_from_moduledoc(moduledoc) == "enum"

    def test_typescript_long_form(self):
        """TypeScript long form (```typescript) also works."""
        from cicada.languages.scip.converter import SCIPConverter

        converter = SCIPConverter()
        moduledoc = "```typescript\ninterface Props\n```"
        assert converter._extract_module_kind_from_moduledoc(moduledoc) == "interface"

    def test_empty_moduledoc_returns_unknown(self):
        """Empty moduledoc returns unknown."""
        from cicada.languages.scip.converter import SCIPConverter

        converter = SCIPConverter()
        assert converter._extract_module_kind_from_moduledoc("") == "unknown"
        assert converter._extract_module_kind_from_moduledoc(None) == "unknown"

    def test_unrecognized_pattern_returns_unknown(self):
        """Unrecognized patterns return unknown."""
        from cicada.languages.scip.converter import SCIPConverter

        converter = SCIPConverter()
        moduledoc = "```ts\nfunction foo()\n```"
        assert converter._extract_module_kind_from_moduledoc(moduledoc) == "unknown"
