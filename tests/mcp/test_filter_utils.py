"""
Comprehensive edge case tests for cicada/mcp/filter_utils.py

Tests cover all edge cases for filtering utilities including:
- Test file detection with various path formats
- Usage type classification
- File type filtering with different parameters
"""

import pytest

from cicada.mcp.filter_utils import (
    classify_usage_type,
    filter_by_file_type,
    is_test_file,
)


class TestIsTestFile:
    """Tests for is_test_file function"""

    def test_detects_test_directory_unix(self):
        """Should detect files in test/ directory on Unix paths"""
        assert is_test_file("lib/test/my_test.ex")
        assert is_test_file("myapp/test/unit/foo.ex")  # /test/ in path
        assert is_test_file("/absolute/path/test/file.ex")

    def test_detects_test_directory_windows(self):
        r"""Should detect files in test\ directory on Windows paths"""
        assert is_test_file("lib\\test\\my_test.ex")
        assert is_test_file("myapp\\test\\unit\\foo.ex")  # \test\ in path
        assert is_test_file("C:\\absolute\\path\\test\\file.ex")

    def test_detects_test_prefix(self):
        """Should detect files starting with test_"""
        assert is_test_file("lib/test_my_module.ex")
        assert is_test_file("test_foo.ex")
        assert is_test_file("/path/to/test_bar.exs")

    def test_detects_test_suffix_ex(self):
        """Should detect files ending with _test.ex"""
        assert is_test_file("lib/my_module_test.ex")
        assert is_test_file("foo_test.ex")
        assert is_test_file("/path/to/bar_test.ex")

    def test_detects_test_suffix_exs(self):
        """Should detect files ending with _test.exs"""
        assert is_test_file("lib/my_module_test.exs")
        assert is_test_file("foo_test.exs")
        assert is_test_file("/path/to/bar_test.exs")

    def test_case_insensitive_matching(self):
        """Should match test patterns case-insensitively"""
        assert is_test_file("lib/TEST/my_test.ex")
        assert is_test_file("lib/Test/foo.ex")
        assert is_test_file("TEST_foo.ex")
        assert is_test_file("foo_TEST.ex")
        assert is_test_file("FOO_test.EX")

    def test_rejects_non_test_files(self):
        """Should return False for non-test files"""
        assert not is_test_file("lib/my_module.ex")
        assert not is_test_file("src/foo.ex")
        assert not is_test_file("/absolute/path/bar.ex")

    def test_handles_empty_string(self):
        """Should handle empty string gracefully"""
        assert not is_test_file("")

    def test_handles_relative_paths(self):
        """Should handle relative paths correctly"""
        assert is_test_file("./test/foo.ex")
        assert is_test_file("../test/bar.ex")
        assert is_test_file("../../test_baz.ex")

    def test_mixed_path_separators(self):
        """Should handle mixed path separators (edge case)"""
        # While unusual, some systems might have mixed separators
        # This won't match because it needs /test/ or \test\ (both separators on each side)
        assert not is_test_file("lib/test\\my_file.ex")

    def test_test_in_filename_but_not_pattern(self):
        """Should not match if 'test' appears but not in recognized patterns"""
        # These should NOT match because 'test' is not in the right context
        assert not is_test_file("lib/attest.ex")  # 'test' is part of word
        assert not is_test_file("lib/contest.ex")  # 'test' is part of word
        assert not is_test_file("lib/my_attestation.ex")  # 'test' is part of word

    def test_multiple_test_patterns(self):
        """Should match files with multiple test indicators"""
        assert is_test_file("test/test_foo.ex")
        assert is_test_file("test/my_module_test.ex")
        assert is_test_file("test_dir/test_file_test.ex")

    def test_uppercase_extensions(self):
        """Should match test files with uppercase extensions"""
        assert is_test_file("test/foo_test.EX")
        assert is_test_file("test/bar_test.EXS")

    def test_nested_test_directories(self):
        """Should match files in deeply nested test directories"""
        assert is_test_file("lib/test/unit/integration/my_test.ex")
        assert is_test_file("a/b/c/d/test/e/f/g.ex")

    def test_test_as_subdirectory(self):
        """Should match when test is a subdirectory at any level"""
        assert is_test_file("myapp/test/foo.ex")
        assert is_test_file("apps/myapp/test/bar.ex")


class TestClassifyUsageType:
    """Tests for classify_usage_type function"""

    def test_empty_usage_sites(self):
        """Should handle empty list"""
        result = classify_usage_type([])
        assert result == {"test": [], "production": []}

    def test_all_test_files(self):
        """Should classify all sites as test when all are test files"""
        sites = [
            {"file": "myapp/test/foo.ex", "line": 10},
            {"file": "lib/test/bar.ex", "line": 20},
            {"file": "test_baz.ex", "line": 30},
        ]
        result = classify_usage_type(sites)
        assert len(result["test"]) == 3
        assert len(result["production"]) == 0
        assert result["test"] == sites

    def test_all_production_files(self):
        """Should classify all sites as production when none are test files"""
        sites = [
            {"file": "lib/foo.ex", "line": 10},
            {"file": "src/bar.ex", "line": 20},
            {"file": "app/baz.ex", "line": 30},
        ]
        result = classify_usage_type(sites)
        assert len(result["test"]) == 0
        assert len(result["production"]) == 3
        assert result["production"] == sites

    def test_mixed_test_and_production(self):
        """Should correctly split test and production files"""
        sites = [
            {"file": "lib/foo.ex", "line": 10},  # production
            {"file": "myapp/test/bar.ex", "line": 20},  # test
            {"file": "src/baz.ex", "line": 30},  # production
            {"file": "test_qux.ex", "line": 40},  # test
        ]
        result = classify_usage_type(sites)
        assert len(result["test"]) == 2
        assert len(result["production"]) == 2
        assert result["test"][0]["file"] == "myapp/test/bar.ex"
        assert result["test"][1]["file"] == "test_qux.ex"
        assert result["production"][0]["file"] == "lib/foo.ex"
        assert result["production"][1]["file"] == "src/baz.ex"

    def test_missing_file_field(self):
        """Should handle sites without 'file' field gracefully"""
        sites = [
            {"line": 10},  # no file field
            {"file": "myapp/test/foo.ex", "line": 20},
            {"other": "data"},  # no file field
        ]
        result = classify_usage_type(sites)
        # Sites without file field should be treated as production (empty string not in test patterns)
        assert len(result["production"]) == 2
        assert len(result["test"]) == 1

    def test_preserves_site_data(self):
        """Should preserve all data in site dictionaries"""
        sites = [
            {
                "file": "myapp/test/foo.ex",
                "line": 10,
                "column": 5,
                "context": "def test",
                "extra": "data",
            },
            {
                "file": "lib/bar.ex",
                "line": 20,
                "function": "my_func",
                "module": "MyModule",
            },
        ]
        result = classify_usage_type(sites)
        test_site = result["test"][0]
        prod_site = result["production"][0]

        assert test_site["column"] == 5
        assert test_site["context"] == "def test"
        assert test_site["extra"] == "data"
        assert prod_site["function"] == "my_func"
        assert prod_site["module"] == "MyModule"

    def test_order_preservation(self):
        """Should preserve the order of sites within each category"""
        sites = [
            {"file": "myapp/test/a.ex", "line": 1},
            {"file": "myapp/test/b.ex", "line": 2},
            {"file": "lib/c.ex", "line": 3},
            {"file": "lib/d.ex", "line": 4},
            {"file": "myapp/test/e.ex", "line": 5},
        ]
        result = classify_usage_type(sites)
        # Check test files maintain order
        assert result["test"][0]["line"] == 1
        assert result["test"][1]["line"] == 2
        assert result["test"][2]["line"] == 5
        # Check production files maintain order
        assert result["production"][0]["line"] == 3
        assert result["production"][1]["line"] == 4


class TestFilterByFileType:
    """Tests for filter_by_file_type function"""

    @pytest.fixture
    def mixed_sites(self):
        """Fixture providing mixed test and production sites"""
        return [
            {"file": "lib/foo.ex", "line": 10},
            {"file": "myapp/test/bar.ex", "line": 20},
            {"file": "src/baz.ex", "line": 30},
            {"file": "test_qux.ex", "line": 40},
        ]

    def test_filter_all_returns_everything(self, mixed_sites):
        """Should return all sites when usage_type is 'all'"""
        result = filter_by_file_type(mixed_sites, "all")
        assert len(result) == 4
        assert result == mixed_sites

    def test_filter_tests(self, mixed_sites):
        """Should return only test sites when usage_type is 'tests'"""
        result = filter_by_file_type(mixed_sites, "tests")
        assert len(result) == 2
        assert all(is_test_file(site["file"]) for site in result)

    def test_filter_test_only_backward_compat(self, mixed_sites):
        """Should support 'test_only' for backward compatibility"""
        result = filter_by_file_type(mixed_sites, "test_only")
        assert len(result) == 2
        assert all(is_test_file(site["file"]) for site in result)

    def test_filter_source(self, mixed_sites):
        """Should return only production sites when usage_type is 'source'"""
        result = filter_by_file_type(mixed_sites, "source")
        assert len(result) == 2
        assert all(not is_test_file(site["file"]) for site in result)

    def test_filter_production_only_backward_compat(self, mixed_sites):
        """Should support 'production_only' for backward compatibility"""
        result = filter_by_file_type(mixed_sites, "production_only")
        assert len(result) == 2
        assert all(not is_test_file(site["file"]) for site in result)

    def test_invalid_type_defaults_to_production(self, mixed_sites):
        """Should default to production sites for invalid usage_type"""
        result = filter_by_file_type(mixed_sites, "invalid_type")
        assert len(result) == 2
        assert all(not is_test_file(site["file"]) for site in result)

    def test_empty_list_returns_empty(self):
        """Should handle empty list for any filter type"""
        assert filter_by_file_type([], "all") == []
        assert filter_by_file_type([], "tests") == []
        assert filter_by_file_type([], "source") == []

    def test_all_test_sites(self):
        """Should return all sites when all are tests and filter is 'tests'"""
        sites = [
            {"file": "myapp/test/a.ex", "line": 1},
            {"file": "myapp/test/b.ex", "line": 2},
        ]
        result = filter_by_file_type(sites, "tests")
        assert len(result) == 2

    def test_all_test_sites_with_source_filter(self):
        """Should return empty when all are tests but filter is 'source'"""
        sites = [
            {"file": "myapp/test/a.ex", "line": 1},
            {"file": "myapp/test/b.ex", "line": 2},
        ]
        result = filter_by_file_type(sites, "source")
        assert len(result) == 0

    def test_all_production_sites_with_test_filter(self):
        """Should return empty when all are production but filter is 'tests'"""
        sites = [
            {"file": "lib/a.ex", "line": 1},
            {"file": "src/b.ex", "line": 2},
        ]
        result = filter_by_file_type(sites, "tests")
        assert len(result) == 0

    def test_preserves_filtering_with_complex_data(self):
        """Should preserve all site data when filtering"""
        sites = [
            {
                "file": "myapp/test/foo.ex",
                "line": 10,
                "extra": "test_data",
                "nested": {"key": "value"},
            },
            {"file": "lib/bar.ex", "line": 20, "extra": "prod_data", "count": 5},
        ]

        test_result = filter_by_file_type(sites, "tests")
        assert len(test_result) == 1
        assert test_result[0]["extra"] == "test_data"
        assert test_result[0]["nested"]["key"] == "value"

        source_result = filter_by_file_type(sites, "source")
        assert len(source_result) == 1
        assert source_result[0]["extra"] == "prod_data"
        assert source_result[0]["count"] == 5

    def test_case_sensitivity_of_filter_type(self):
        """Filter type parameter should be case-sensitive"""
        sites = [{"file": "myapp/test/a.ex", "line": 1}]
        # Lowercase should work
        assert len(filter_by_file_type(sites, "tests")) == 1
        # Uppercase should default to production (invalid type)
        assert len(filter_by_file_type(sites, "TESTS")) == 0


class TestEdgeCases:
    """Edge case tests for filter utilities"""

    def test_is_test_file_with_none_input(self):
        """Should handle None input gracefully (if possible)"""
        # This might raise an error, which is acceptable
        with pytest.raises((TypeError, AttributeError)):
            is_test_file(None)  # type: ignore[arg-type]

    def test_classify_usage_type_with_none_file(self):
        """Should handle sites with None file field"""
        sites = [{"file": None, "line": 10}]
        # This will likely raise an error since None.lower() will fail
        # But if it doesn't, None won't match any test patterns
        try:
            result = classify_usage_type(sites)
            # If no error, should be treated as production
            assert len(result["production"]) == 1
        except AttributeError:
            # Expected if None.lower() is called
            pass

    def test_filter_with_single_site(self):
        """Should handle single-element lists correctly"""
        test_site = [{"file": "myapp/test/foo.ex", "line": 1}]
        prod_site = [{"file": "lib/foo.ex", "line": 1}]

        assert len(filter_by_file_type(test_site, "tests")) == 1
        assert len(filter_by_file_type(test_site, "source")) == 0
        assert len(filter_by_file_type(prod_site, "tests")) == 0
        assert len(filter_by_file_type(prod_site, "source")) == 1

    def test_is_test_file_with_special_characters(self):
        """Should handle paths with special characters"""
        assert is_test_file("lib/test/foo-bar.ex")
        assert is_test_file("myapp/test/foo_bar@123.ex")
        assert is_test_file("myapp/test/foo.bar.ex")
        assert not is_test_file("lib/foo-bar.ex")

    def test_is_test_file_with_unicode(self):
        """Should handle unicode characters in paths"""
        assert is_test_file("myapp/test/файл.ex")  # Russian - has /test/ pattern
        assert is_test_file("测试/test/foo.ex")  # Chinese - has /test/ pattern
        assert is_test_file("test_file.ex")  # Has test_ prefix

    def test_classify_preserves_exact_references(self):
        """Should preserve exact object references, not create copies"""
        site = {"file": "myapp/test/foo.ex", "line": 1, "mutable": []}
        sites = [site]
        result = classify_usage_type(sites)

        # Modify the original site's mutable field
        site["mutable"].append("item")

        # The classified site should reflect the change (same reference)
        assert result["test"][0]["mutable"] == ["item"]
        assert result["test"][0] is site

    def test_filter_by_file_type_preserves_references(self):
        """Should preserve exact object references when filtering"""
        site = {"file": "myapp/test/foo.ex", "line": 1, "data": {"key": "value"}}
        sites = [site]
        result = filter_by_file_type(sites, "tests")

        # Should be the same object, not a copy
        assert result[0] is site
