# Template Development Guide

This guide explains how to create and maintain language-specific templates for Cicada's code formatting system.

## Overview

Cicada uses a template-based system to format code elements (function signatures, module headers, etc.) in a language-appropriate way. Templates are simple text files with variable placeholders that get substituted at runtime.

## Quick Start

### Creating Templates for a New Language

1. **Create the language directory:**
   ```bash
   mkdir -p cicada/format/templates/typescript
   ```

2. **Create the required template files:**
   - `signature.txt` - Function signature format
   - `module_header.txt` - Module information header
   - `function_entry.txt` - Function entry display

3. **Test your templates:**
   ```bash
   uv run pytest tests/format/test_language_formatting.py -v
   ```

## Template Files

### 1. `signature.txt` - Function Signature Format

Formats how function signatures appear in search results and module listings.

**Template Variables:**
- `$func_name` - The function name
- `$args` - Comma-separated arguments with types (e.g., `x: int, y: str`)
- `$return_annotation` - Return type annotation (pre-formatted for the language)

**Examples:**

**Elixir:**
```
$func_name($args)$return_annotation
```
Output: `create_user(attrs: map, opts: keyword) :: {:ok, User.t()}`

**Python:**
```
def $func_name($args)$return_annotation
```
Output: `def create_user(attrs: dict, opts: dict) -> User:`

**TypeScript:**
```
function $func_name($args)$return_annotation
```
Output: `function createUser(attrs: Attrs, opts: Opts): Result<User>`

**Rust:**
```
fn $func_name($args)$return_annotation
```
Output: `fn create_user(attrs: Map, opts: Keyword) -> Result<User, Error>`

### 2. `module_header.txt` - Module Header Format

Formats the header section when displaying module information.

**Template Variables:**
- `$module_name` - Full module name (e.g., `MyApp.User` or `my_app.user`)
- `$file` - File path relative to project root
- `$line` - Line number where module is defined
- `$public_count` - Number of public functions
- `$private_count` - Number of private functions

**Examples:**

**Elixir:**
```
$module_name

$file:$line • $public_count public • $private_count private
```
Output:
```
MyApp.User

lib/my_app/user.ex:1 • 5 public • 3 private
```

**Python:**
```
$module_name

$file:$line • $public_count public • $private_count private
```
Output:
```
my_app.user

my_app/user.py:1 • 5 public • 2 private
```

**Java:**
```
$module_name

$file:$line • $public_count public • $private_count package/private
```

### 3. `function_entry.txt` - Function Entry Display

Formats how individual functions appear in detailed search results.

**Template Variables:**
- `$file_path` - Full file path
- `$line` - Line number where function is defined
- `$module_name` - Module name
- `$func_name` - Function name
- `$arity` - Function arity (for languages that use it, like Elixir)
- `$signature` - Complete function signature

**Examples:**

**Elixir:**
```
$file_path:$line
$module_name.$func_name/$arity
Type: $signature
```
Output:
```
lib/my_app/user.ex:42
MyApp.User.create/2
Type: create(attrs: map, opts: keyword) :: {:ok, User.t()}
```

**Python:**
```
$file_path:$line
$module_name.$func_name
Type: $signature
```
Output:
```
my_app/user.py:42
my_app.user.create
Type: def create(attrs: dict, opts: dict) -> User:
```

## Variable Preparation in Code

Templates receive pre-formatted variables. The business logic handles the complexity:

### Return Annotations

The `return_annotation` variable is prepared differently for each language:

```python
# In SignatureBuilder.build()
if "return_type" in func and func["return_type"]:
    if language == "python":
        return_annotation = f" -> {func['return_type']}:"
    elif language == "rust":
        return_annotation = f" -> {func['return_type']}"
    else:  # Elixir and others
        return_annotation = f" :: {func['return_type']}"
elif language == "python":
    # Python always needs a colon
    return_annotation = ":"
else:
    return_annotation = ""
```

This keeps templates simple while allowing language-specific formatting.

## Testing Your Templates

### Unit Tests

Create tests in `tests/format/test_template_renderer.py`:

```python
def test_render_signature_typescript(self):
    """Test rendering TypeScript function signature."""
    renderer = TemplateRenderer("typescript")
    result = renderer.render(
        "signature",
        func_name="createUser",
        args="attrs: Attrs, opts: Opts",
        return_annotation=": Result<User>"
    )
    assert result == "function createUser(attrs: Attrs, opts: Opts): Result<User>"
```

### Integration Tests

Add tests in `tests/format/test_language_formatting.py`:

```python
def test_typescript_signature_with_return_type(self):
    """Test TypeScript signature with return type."""
    func = {
        "name": "createUser",
        "arity": 2,
        "args_with_types": [
            {"name": "attrs", "type": "Attrs"},
            {"name": "opts", "type": "Opts"}
        ],
        "return_type": "Result<User>"
    }

    sig = SignatureBuilder.build(func, language="typescript")
    assert sig == "function createUser(attrs: Attrs, opts: Opts): Result<User>"
```

### Manual Testing

Test your templates interactively:

```python
from cicada.format.template_renderer import TemplateRenderer

renderer = TemplateRenderer("typescript")

# Test signature
sig = renderer.render(
    "signature",
    func_name="test",
    args="x: number, y: string",
    return_annotation=": boolean"
)
print(sig)

# Test module header
header = renderer.render(
    "module_header",
    module_name="app.user",
    file="src/app/user.ts",
    line=1,
    public_count=5,
    private_count=2
)
print(header)
```

## Template Development Best Practices

### 1. Keep Templates Simple

✅ **Good:**
```
def $func_name($args)$return_annotation
```

❌ **Bad:**
```
${if_public}def${else}private def${endif} $func_name($args)$return_annotation
```

**Why:** Complex logic belongs in the formatter code, not templates. Templates should only handle string substitution.

### 2. Use Consistent Variable Names

Use the same variable names across all language templates for the same concept:
- `$func_name` (not `$function_name`, `$name`, etc.)
- `$module_name` (not `$mod`, `$namespace`, etc.)
- `$return_annotation` (not `$return_type`, `$ret`, etc.)

### 3. Handle Edge Cases in Code

Prepare template variables to handle edge cases before rendering:

```python
# Prepare arguments - handle empty case
args_str = ""
if "args_with_types" in func and func["args_with_types"]:
    args_str = format_args_with_types(func["args_with_types"])
elif "args" in func and func["args"]:
    args_str = ", ".join(func["args"])

# Template receives pre-formatted args_str
renderer.render("signature", func_name="test", args=args_str, ...)
```

### 4. Test with Real Data

Use actual function signatures from the target language when testing:

```python
# Real Rust signature
func = {
    "name": "read_file",
    "args_with_types": [
        {"name": "path", "type": "&Path"}
    ],
    "return_type": "Result<String, std::io::Error>"
}
```

### 5. Document Template Variables

Add comments to your templates explaining what each variable represents:

```
# TypeScript function signature template
# $func_name: The function name (e.g., "createUser")
# $args: Typed arguments (e.g., "x: number, y: string")
# $return_annotation: Return type with colon (e.g., ": Promise<User>")
function $func_name($args)$return_annotation
```

## Troubleshooting

### Template Not Found

**Error:** `FileNotFoundError: Template 'signature' not found for language 'typescript'`

**Solution:**
1. Verify the template file exists: `cicada/format/templates/typescript/signature.txt`
2. Check file permissions (must be readable)
3. Ensure filename is exactly `signature.txt` (not `Signature.txt` or `signature.txt.template`)

### Missing Variables

**Error:** `ValueError: Template 'signature' requires variable 'func_name' which was not provided`

**Solution:**
1. Check that all required variables are passed to `renderer.render()`
2. Ensure variable names match exactly (case-sensitive)
3. Use `safe_render()` during development to see which variables are missing

### Wrong Output Format

**Problem:** Template output doesn't match expected language syntax

**Solution:**
1. Review example outputs in this guide
2. Check that `return_annotation` is pre-formatted correctly in code
3. Test with the `TemplateRenderer` directly to isolate the issue
4. Compare with working templates from similar languages

### Fallback to Elixir

**Warning:** `Template 'signature' not found for language 'rust'. Falling back to Elixir template.`

**This is expected behavior when:**
- Language is under development
- Template hasn't been created yet
- Testing with a new language

**To fix:** Create the missing template file.

## Advanced Topics

### Custom Template Variables

If you need additional variables for a specific language, add them in the formatter:

```python
# In formatter.py
extra_vars = {}
if language == "rust":
    extra_vars["lifetime"] = func.get("lifetime", "")

renderer.render(
    "signature",
    func_name=func_name,
    args=args_str,
    return_annotation=return_annotation,
    **extra_vars
)
```

Then use in template:
```
fn $func_name$lifetime($args)$return_annotation
```

### Template Inheritance

The system automatically falls back to Elixir templates. To create a variant:

1. Copy Elixir template as starting point
2. Modify for your language
3. Test that changes work correctly

### Multiple Template Formats

You can create additional template files beyond the core three:

- `signature_compact.txt` - Shorter signature format
- `module_header_verbose.txt` - More detailed header
- `call_site.txt` - How call sites are displayed

Reference them by name: `renderer.render("signature_compact", ...)`

## Contributing Templates

When adding templates for a new language:

1. **Create all three core templates**
2. **Write comprehensive tests** (unit + integration)
3. **Test with real codebases** in that language
4. **Document language-specific conventions**
5. **Add examples to this guide**
6. **Submit PR with before/after examples**

## Reference

### Template Renderer API

```python
class TemplateRenderer:
    def __init__(self, language: str)
    def render(self, template_name: str, **variables) -> str
    def safe_render(self, template_name: str, **variables) -> str
    def template_exists(self, template_name: str) -> bool
    def get_available_templates(self) -> list[str]
    def clear_cache(self)
```

### Example: Complete TypeScript Templates

**signature.txt:**
```
function $func_name($args)$return_annotation
```

**module_header.txt:**
```
$module_name

$file:$line • $public_count exports • $private_count internal
```

**function_entry.txt:**
```
$file_path:$line
$module_name.$func_name
Type: $signature
```

## Questions?

- Check existing templates in `cicada/format/templates/`
- Review tests in `tests/format/test_template_renderer.py`
- See CLAUDE.md for architecture overview
