# TypeScript Formatter Tests - TDD Summary

## Test File Created
`tests/languages/scip/test_typescript_formatter.py` - 378 lines

## Test Results
**24 failed, 1 passed** (as expected - TypeScriptFormatter doesn't exist yet)

The one passing test verifies TypeScript language detection in the index, which doesn't require the formatter.

## Test Coverage

### 1. TypeScriptFormatter Class (9 tests) ❌
- `test_typescript_formatter_exists` - Class can be imported
- `test_format_typescript_function` - Uses `()` not `/arity`
- `test_format_zero_arity_typescript` - Zero-arity functions
- `test_format_multiple_arity_typescript` - All arities use same notation
- `test_format_static_method` - Static method formatting
- `test_format_async_function` - Async function formatting
- `test_format_arrow_function` - Arrow function formatting
- `test_format_constructor` - Constructor formatting
- `test_format_generic_function` - Generic function formatting

### 2. Formatter Registry Integration (4 tests) ❌
- `test_get_typescript_formatter` - Registry returns TypeScriptFormatter
- `test_typescript_formatter_not_elixir` - Doesn't fall back to Elixir
- `test_typescript_vs_python_formatter_same_notation` - Same as Python `()`
- `test_typescript_vs_elixir_formatter_different` - Different from Elixir `/arity`

### 3. TypeScript Index Formatting (3 tests)
- `test_module_formatter_uses_typescript_notation` - ModuleFormatter integration ✅
- `test_language_detection_triggers_typescript_formatter` - Language detection ❌
- `test_format_all_function_types` - All TypeScript function types ❌

### 4. Edge Cases (5 tests) ❌
- `test_format_with_special_characters` - Underscores, special chars
- `test_format_with_long_names` - Very long function names
- `test_format_with_numbers` - Function names with numbers
- `test_format_interface_method` - Interface method formatting
- `test_format_type_alias` - Type alias formatting

### 5. Implementation Details (4 tests) ❌
- `test_implements_base_formatter_interface` - Inherits from BaseLanguageFormatter
- `test_method_signature_matches_interface` - Correct method signature
- `test_returns_string` - Returns string type
- `test_consistent_output_format` - Consistent `Module.function()` pattern

## Key Test Assertions

### TypeScript Notation
```python
# TypeScript should use parentheses, NOT arity
assert result == "Container.add()"
assert "/1" not in result  # Must NOT use Elixir notation
```

### Arity Invariance
```python
# All arities should produce the same notation
formatter.format_function_identifier("MyClass", "method", 0)  # → "MyClass.method()"
formatter.format_function_identifier("MyClass", "method", 2)  # → "MyClass.method()"
formatter.format_function_identifier("MyClass", "method", 5)  # → "MyClass.method()"
```

### Same as Python, Not Elixir
```python
# TypeScript should match Python
ts_result = ts_formatter.format_function_identifier("MyClass", "method", 2)
py_result = py_formatter.format_function_identifier("MyClass", "method", 2)
assert ts_result == py_result  # Both: "MyClass.method()"

# TypeScript should NOT match Elixir
ex_result = ex_formatter.format_function_identifier("MyModule", "func", 2)
assert ts_result != ex_result  # Elixir: "MyModule.func/2"
```

## What Needs Implementation

### 1. Create TypeScriptFormatter class
**File**: `cicada/languages/scip/formatter.py`

Add alongside PythonFormatter:
```python
class TypeScriptFormatter(BaseLanguageFormatter):
    """Formatter for TypeScript language conventions."""

    def format_function_identifier(self, module_name: str, func_name: str, arity: int) -> str:
        """
        Format a function identifier using TypeScript's () notation.

        Note: TypeScript doesn't use arity in function identifiers - all functions
        use parentheses regardless of parameter count.

        Args:
            module_name: The class or module name
            func_name: The function or method name
            arity: The number of parameters (not used in TypeScript notation)

        Returns:
            Formatted identifier like "MyClass.my_method()"

        Examples:
            >>> formatter = TypeScriptFormatter()
            >>> formatter.format_function_identifier("Container", "add", 1)
            'Container.add()'
            >>> formatter.format_function_identifier("AsyncHandler", "save", 2)
            'AsyncHandler.save()'
        """
        return f"{module_name}.{func_name}()"
```

### 2. Register TypeScriptFormatter
**File**: `cicada/languages/formatter_registry.py`

Update the formatters dict:
```python
from cicada.languages.scip.formatter import PythonFormatter, TypeScriptFormatter

formatters = {
    "elixir": ElixirFormatter(),
    "python": PythonFormatter(),
    "typescript": TypeScriptFormatter(),  # ADD THIS
}
```

## Implementation Estimate

- **TypeScriptFormatter class**: ~30 lines (same as PythonFormatter)
- **Registry update**: 1 import, 1 line
- **Total new production code**: ~35 lines

## Expected Result After Implementation

```bash
$ uv run pytest tests/languages/scip/test_typescript_formatter.py -v
========================= 25 passed in 0.43s =========================
```

All 25 tests should pass once TypeScriptFormatter is implemented and registered.

## Why This Matters

Currently, TypeScript code is formatted incorrectly:
- **Current (wrong)**: `Container.add/1` (using Elixir formatter)
- **Expected (correct)**: `Container.add()` (using TypeScript formatter)

This affects:
- MCP tool outputs (`search_module`, `search_function`)
- Query results display
- User-facing documentation
- IDE integration clarity

## Next Steps

1. ✅ Write comprehensive tests (24 failing, 1 passing)
2. ⏭️ Implement TypeScriptFormatter class (~30 lines)
3. ⏭️ Register in formatter registry (2 lines)
4. ⏭️ Run tests and verify all 25 pass
5. ⏭️ Update documentation
6. ⏭️ Commit changes

---

**Test File**: `tests/languages/scip/test_typescript_formatter.py`
**Production Files to Modify**:
- `cicada/languages/scip/formatter.py` (add TypeScriptFormatter)
- `cicada/languages/formatter_registry.py` (register formatter)
