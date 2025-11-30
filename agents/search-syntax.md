# Search Query Syntax

Cicada's search system supports both keyword-based and pattern-based queries with automatic query type detection.

## Query Types

### 1. Keyword Search (Default)

String queries are automatically tokenized by whitespace into individual keywords:

```python
# Single keyword
"authentication"  # Searches for "authentication"

# Multiple keywords (tokenized automatically)
"agent execution"  # Searches for BOTH "agent" AND "execution"

# Quoted phrases (exact match)
'"agent execution" context'  # Exact phrase + keyword
```

**Key Features:**
- String queries automatically split by whitespace
- Each word becomes a separate keyword
- Use quotes to keep phrases together
- Case-insensitive matching

**Important:** String queries containing pattern syntax (`|`, `*`, `/`, module qualifiers) are NOT tokenized to preserve the pattern structure.

### 2. Pattern Search (Automatic Detection)

Patterns are automatically detected when queries contain:
- Wildcards (`*`, `|`)
- Module qualifiers (Capital.Name)
- Arity specifications (`/N`)
- File path prefixes (`.ex:`)

```python
# Wildcard patterns
"create*"                    # Functions starting with "create"
"*user*"                     # Functions containing "user"
"create*|update*"            # Functions matching either pattern

# Module qualification
"MyApp.User.create*"         # Functions in MyApp.User module
"User.create*"               # Auto-expands to *.User.create*

# Arity specification
"create_user/1"              # create_user with arity 1

# File paths
"lib/auth.ex:verify*"        # Functions in specific file
```

## Wildcard Pattern Matching

The `*` wildcard supports flexible matching with special handling for module names:

```python
# *.Something matches:
"Something"                  # Exact match
"MyApp.Something"            # Suffix match (has prefix)
"Something.Other"            # Prefix match (has suffix)
"MyApp.Something.Other"      # Component match (in the middle)
```

**Pattern Parsing Rules:**

1. **Auto-prefix for module patterns:**
   - `User.create*` becomes `*.User` (module) + `create*` (function)

2. **Dot as separator:**
   - Patterns are split by the LAST dot to separate module from function

3. **Wildcard suffix handling:**
   - Pattern `*.Prefix*` applies fnmatch to all possible tails

## Search Filters

```python
# Filter by type
filter_type="modules"        # Only modules
filter_type="functions"      # Only functions

# Filter by scope
scope="public"               # Public functions only
scope="private"              # Private functions only

# Filter by source
match_source="docs"          # Match in documentation only
match_source="strings"       # Match in string literals only
match_source="all"           # Match in both (default)

# Filter by path
path_pattern="lib/**"        # Only files in lib/
path_pattern="!**/test/**"   # Exclude test files

# Filter by recency
recent=true                  # Last 14 days only

# Filter by arity
arity=2                      # Functions with arity 2 only
```

## Usage Examples

### Keyword Search
```python
# Bug report mentions "agent execution context"
query="agent execution context"

# Search for exact error message
query='"invalid credentials" authentication'
```

### Pattern Search
```python
# Find all agent-related modules
query="ThenvoiCom.Agent*.*"
filter_type="modules"

# Find create functions in User modules
query="User.create*"
```

### Mixed Queries
```python
# Combine keywords and patterns
query=["authentication", "verify", "MyApp.Auth.*"]

# Search with multiple filters
query="agent execution"
filter_type="functions"
scope="public"
match_source="docs"
```

## Output Control Options

### Compact Output (Default)

By default, search results are compact to minimize token usage:
- Function signatures and documentation hidden
- Only essential info shown (name, location, call sites)

### Verbose Output

Use these options to include additional details:

```python
# query tool
verbose=True               # Enable full keyword sources and confidence

# search_module tool
include_moduledoc=True     # Show module documentation
include_docs=True          # Show function documentation
include_specs=True         # Show type specifications
verbose=True               # Enable all above options

# search_function tool
include_docs=True          # Show function documentation
include_specs=True         # Show type specifications
verbose=True               # Enable all above options

# git_history tool
include_pr_description=True    # Show PR descriptions
include_review_comments=True   # Show review comments
verbose=True                   # Enable all above options
```

### expand_result Tool

The `expand_result` tool automatically enables verbose output since its purpose is to show complete details.

## Common Pitfalls

### ❌ Don't: Use string query for patterns

```python
# ❌ Wrong: Auto-tokenization breaks the pattern
query="ThenvoiCom.Agent*"

# ✓ Correct: Use array to prevent tokenization
query=["ThenvoiCom.Agent*"]
```

### ❌ Don't: Forget the trailing wildcard for module children

```python
# ❌ Wrong: Only matches exact module
query="ThenvoiCom.Agents"

# ✓ Correct: Matches all modules starting with prefix
query="ThenvoiCom.Agents.*"
```

**Implementation:** `cicada/query/orchestrator.py`, `cicada/mcp/pattern_utils.py`, `cicada/keyword_search.py`
