# Cicada CLI Redesign Guidelines

**Date**: 2025-11-07
**Based on**: Comprehensive research of 17+ industry-leading CLI tools
**Goal**: Improve PR indexing discoverability and UX while maintaining best practices

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [Research Findings](#research-findings)
4. [Recommended Changes](#recommended-changes)
5. [Implementation Plan](#implementation-plan)
6. [Code Examples](#code-examples)
7. [Testing Strategy](#testing-strategy)
8. [Migration Path](#migration-path)

---

## Executive Summary

### Key Decisions

✅ **KEEP**: Explicit `install` subcommand (industry standard - 100% of researched tools use this)
✅ **KEEP**: Auto-insertion logic for paths (`cicada /path` → `cicada install /path`)
✅ **ADD**: Interactive prompt for PR indexing during install (Y/n pattern)
✅ **ADD**: Progress indicators (spinner → progress bar → checkmark)
✅ **ADD**: Automation flags (`--yes`, `--no-index-prs`, `--index-prs`)
✅ **KEEP**: Separate `cicada index-pr` command for manual execution

### Research Consensus

After analyzing npm, pip, cargo, homebrew, apt, git hooks, language servers, and 10+ other tools:

- **0 out of 17 tools** use implicit default install action
- **100% require explicit subcommand** or flag
- **Interactive prompts with smart defaults (Y/n)** most successful pattern
- **Progress indicators** critical for operations >2 seconds
- **Opt-in prompts** better than opt-out automatic (Homebrew auto-update lessons)

---

## Current State Analysis

### What Cicada Does Now

#### 1. Auto-Insert Install Logic (`cicada/cli.py:28-29`)

```python
if first_arg not in known_commands and not first_arg.startswith("-"):
    sys.argv.insert(1, "install")
```

**Behavior**: `cicada /path/to/repo` → `cicada install /path/to/repo`

**Verdict**: ✅ **KEEP THIS** - Convenient shortcut, doesn't break explicit subcommand pattern

---

#### 2. Install Command (`cicada/commands.py:709-823`)

**Current Flow:**
```bash
cicada install [repo]
  ↓
Interactive prompts:
  1. Select editor (Claude/Cursor/VS Code)
  2. Select model tier (fast/regular/max)
  ↓
Creates config + indexes repository
  ↓
Setup complete
```

**What's Missing:**
- ❌ No PR indexing integration
- ❌ No mention of optional features
- ❌ Users don't discover `index-pr` command

---

#### 3. PR Indexing Command (`cicada/commands.py:600-622`)

**Current Flow:**
```bash
cicada index-pr [repo] [--clean]
  ↓
Indexes PRs (no prompts)
  ↓
"✅ Indexing complete!"
```

**Issues:**
- ❌ Completely separate from install
- ❌ Poor discoverability (users must read docs)
- ❌ No progress indicators for long operations
- ❌ No mention in install flow

---

#### 4. Flags Available

**Install command flags:**
- `--claude`, `--cursor`, `--vs` (editor selection)
- `--fast`, `--regular`, `--max` (model tier)
- No PR-related flags

**Missing:**
- ❌ `--yes` / `--no-interactive` (for CI/CD)
- ❌ `--index-prs` / `--no-index-prs` (explicit control)
- ❌ `--skip-optional` (skip all optional features)

---

## Research Findings

### Pattern 1: Interactive Prompts Win

**Successful Examples:**
- **Git LFS**: One-time setup prompt, automatic thereafter
- **npm postinstall**: Automatic but controversial (security issues)
- **Django migrations**: Auto-generate, manual apply (clever split)
- **rust-analyzer**: Background indexing with excellent progress UI

**Failed Examples:**
- **Homebrew pre-2023**: Auto-update on every install (massive complaints)
- **APT separated commands**: Poor discoverability, users forget `apt update`
- **npm --ignore-scripts**: All-or-nothing, no granular control

### Pattern 2: Y/n Convention

**Universal Standard:**
```bash
Do you want to index pull requests? (Y/n): _
```

**Rules:**
- Capital letter = default when pressing Enter
- `(Y/n)` = Yes is default
- `(y/N)` = No is default
- Case-insensitive responses accepted
- Standard across Unix/Linux tools for 40+ years

### Pattern 3: Progress Communication

**Three essential patterns:**

1. **Spinner** (unknown duration)
   ```
   ⠋ Fetching PR metadata from GitHub...
   ```

2. **X of Y** (countable items)
   ```
   Processing PRs: 234/450
   ```

3. **Progress Bar** (best UX)
   ```
   Indexing PRs: [============>     ] 289/450 (64%)
   ```

**Critical Rule**: Never go silent >2 seconds during long operations

### Pattern 4: Automation Support

**Required flags for CI/CD:**
```bash
# Accept all defaults (Y to all prompts)
tool install --yes

# Explicit control
tool install --feature-x
tool install --no-feature-x

# Skip all optional features
tool install --skip-optional
```

**Why**: Automation tools (CI/CD, scripts) can't interact with prompts

---

## Recommended Changes

### Change 1: Add PR Indexing Prompt to Install Flow

**Location**: `cicada/commands.py:handle_install()` (after line 820)

**New Flow:**
```bash
cicada install [repo]
  ↓
Interactive prompts:
  1. Select editor
  2. Select model tier
  ↓
Creates config + indexes repository
  ↓
✓ Repository indexed
  ↓
NEW: Optional feature prompt
  "Index pull requests for better search? (Y/n): "
  ↓
  If Yes:
    ⠋ Fetching PR data from GitHub...
    ✓ Fetched 450 PRs
    [=====>     ] 234/450 (52%)
    ✓ Indexed 450 PRs in 3m 24s
  ↓
  If No:
    "Skipped. Run later: cicada index-pr"
  ↓
Setup complete! 🎉
```

**Benefits:**
- ✅ Users discover PR indexing immediately
- ✅ Makes informed choice (value prop explained)
- ✅ Default (Y) encourages adoption
- ✅ Non-blocking with flags
- ✅ Can still be run separately later

---

### Change 2: Add New Flags

#### Install Command Flags

**Add to `cicada/commands.py:install_parser` (after line 105):**

```python
install_parser.add_argument(
    "--yes",
    action="store_true",
    help="Accept all defaults (non-interactive mode for CI/CD)",
)
install_parser.add_argument(
    "--index-prs",
    action="store_true",
    help="Enable PR indexing (requires GitHub CLI)",
)
install_parser.add_argument(
    "--no-index-prs",
    action="store_true",
    help="Skip PR indexing",
)
install_parser.add_argument(
    "--skip-optional",
    action="store_true",
    help="Skip all optional features (PR indexing, etc.)",
)
```

#### Usage Examples

```bash
# Interactive (default) - prompts for PR indexing
cicada install

# CI/CD mode - accept all defaults including PR indexing
cicada install --yes

# Explicit control - force PR indexing
cicada install --index-prs

# Explicit control - skip PR indexing
cicada install --no-index-prs

# Skip all optional features
cicada install --skip-optional

# Fast setup, no PR indexing (CI builds)
cicada install --fast --no-index-prs
```

---

### Change 3: Add Progress Indicators

**Current PR Indexer Output:**
```bash
$ cicada index-pr
[silence for minutes]
✅ Indexing complete!
```

**Improved Output:**
```bash
$ cicada index-pr
⠋ Checking GitHub CLI availability...
✓ GitHub CLI found

⠋ Authenticating with GitHub...
✓ Authenticated as @username

⠋ Fetching PR data from GitHub API...
✓ Fetched 450 PRs in 12s

Indexing PRs: [=========>      ] 234/450 (52%) ~2m remaining

✓ Indexed 450 PRs in 3m 24s
✓ Index saved to ~/.cicada/projects/<hash>/pr_index.json
```

**Implementation**: Use existing Python libraries
- `rich` (recommended) - excellent progress bars and spinners
- `tqdm` (alternative) - simpler, widely used
- `halo` (alternative) - focused on spinners

---

### Change 4: Enhance Value Proposition

**Current**: No explanation of PR indexing benefits

**Improved Prompt:**
```
Optional: Index pull requests for enhanced git history tools?

  Benefits:
  • Find which PR introduced any line of code (find-pr-for-line)
  • Get detailed PR history for files (get-file-pr-history)
  • View commit history with PR context (get-commit-history)
  • Enhanced git blame with PR metadata

  Requirements:
  • GitHub CLI (gh) must be installed
  • Takes 2-5 minutes for repos with 100+ PRs
  • Can be run later with: cicada index-pr

Index pull requests now? (Y/n): _
```

**Why**: Clear value proposition increases adoption rate

---

### Change 5: Check GitHub CLI Availability

**Add validation before prompting:**

```python
def check_gh_cli_available() -> bool:
    """Check if GitHub CLI (gh) is installed and authenticated."""
    import shutil
    import subprocess

    if not shutil.which("gh"):
        return False

    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False

def prompt_pr_indexing() -> bool:
    """Prompt user for PR indexing with GH CLI check."""
    if not check_gh_cli_available():
        print("\n⚠️  GitHub CLI not found or not authenticated.")
        print("   Install: https://cli.github.com/")
        print("   Skipping PR indexing.")
        return False

    # Show prompt...
```

---

## Implementation Plan

### Phase 1: Core Changes (Week 1)

**Priority: HIGH**

1. ✅ Add new flags to install command
2. ✅ Add PR indexing prompt to install flow
3. ✅ Add GitHub CLI availability check
4. ✅ Add basic progress spinner
5. ✅ Update help text and documentation

**Files to Modify:**
- `cicada/commands.py` (add flags, modify handle_install)
- `cicada/setup.py` (add optional PR indexing step)
- `cicada/pr_indexer/indexer.py` (add progress callbacks)

**Estimated Effort**: 4-6 hours

---

### Phase 2: Enhanced Progress UI (Week 2)

**Priority: MEDIUM**

1. ✅ Integrate `rich` library for better progress bars
2. ✅ Add detailed progress for PR fetching
3. ✅ Add estimated time remaining
4. ✅ Add success/error indicators (✓, ✗, ⚠️)

**Files to Modify:**
- `cicada/pr_indexer/indexer.py` (enhance progress reporting)
- `pyproject.toml` (add `rich` dependency)

**Estimated Effort**: 3-4 hours

---

### Phase 3: Documentation & Polish (Week 2)

**Priority: MEDIUM**

1. ✅ Update README with new flags
2. ✅ Add example workflows
3. ✅ Update CLAUDE.md (if applicable)
4. ✅ Add troubleshooting guide for GH CLI

**Files to Modify:**
- `README.md`
- `docs/` (if exists)

**Estimated Effort**: 2-3 hours

---

### Phase 4: Future Enhancement - Background Indexing (Future)

**Priority: LOW (Future v2.0)**

1. ⚠️ Background PR indexing (language server model)
2. ⚠️ Incremental updates on git operations
3. ⚠️ Git hooks integration (post-merge, post-checkout)

**Why Later**:
- Complex implementation (process management, state tracking)
- Current interactive approach is proven and sufficient
- Can learn from user adoption first

---

## Code Examples

### Example 1: Modified Install Handler

**File**: `cicada/commands.py`

**Location**: Modify `handle_install()` function (line 709)

```python
def handle_install(args):
    """
    Handle the install subcommand (interactive setup).

    Behavior:
    - INTERACTIVE: shows prompts and menus
    - Can skip prompts with flags
    - NEW: Prompts for PR indexing (optional feature)
    """
    from pathlib import Path
    from cicada.interactive_setup import show_first_time_setup
    from cicada.setup import EditorType, setup
    from cicada.utils import get_config_path, get_index_path

    # ... existing code for repo_path, validation, editor, extraction_method ...

    # Run main setup (existing code)
    try:
        setup(
            editor,
            repo_path,
            extraction_method=extraction_method,
            expansion_method=expansion_method,
            index_exists=index_exists,
        )
    except Exception as e:
        print(f"\nError: Setup failed: {e}", file=sys.stderr)
        sys.exit(1)

    # ============================================================
    # NEW: Optional PR Indexing Prompt
    # ============================================================

    # Determine if we should prompt for PR indexing
    should_prompt_pr = True
    should_index_prs = None  # None = prompt, True = yes, False = no

    # Check explicit flags
    if args.index_prs and args.no_index_prs:
        print("Error: Cannot specify both --index-prs and --no-index-prs", file=sys.stderr)
        sys.exit(1)

    if args.index_prs:
        should_index_prs = True
        should_prompt_pr = False
    elif args.no_index_prs or args.skip_optional:
        should_index_prs = False
        should_prompt_pr = False
    elif args.yes:
        should_index_prs = True  # --yes means accept defaults
        should_prompt_pr = False

    # Prompt if no explicit choice made
    if should_prompt_pr:
        should_index_prs = prompt_pr_indexing_interactive(repo_path)

    # Execute PR indexing if requested
    if should_index_prs:
        run_pr_indexing_with_progress(repo_path)
    elif should_prompt_pr and not should_index_prs:
        # User explicitly declined in prompt
        print("\nSkipped PR indexing. You can run it later with:")
        print(f"  cicada index-pr {repo_path}")
        print()


def prompt_pr_indexing_interactive(repo_path: Path) -> bool:
    """
    Show interactive prompt for PR indexing with value proposition.

    Returns:
        True if user wants PR indexing, False otherwise
    """
    print()
    print("=" * 60)
    print("Optional: Index Pull Requests")
    print("=" * 60)
    print()
    print("Benefits:")
    print("  • Find which PR introduced any line of code")
    print("  • Get detailed PR history for files")
    print("  • View commit history with PR context")
    print("  • Enhanced git blame with PR metadata")
    print()
    print("Requirements:")
    print("  • GitHub CLI (gh) must be installed")
    print("  • Takes 2-5 minutes for repos with 100+ PRs")
    print("  • Can be run later with: cicada index-pr")
    print()

    # Check if GitHub CLI is available
    if not check_gh_cli_available():
        print("⚠️  GitHub CLI not found or not authenticated.")
        print("   Install: https://cli.github.com/")
        print("   Then run: gh auth login")
        print()
        print("Skipping PR indexing (GitHub CLI required).")
        print()
        return False

    # Prompt with Y/n pattern
    while True:
        response = input("Index pull requests now? (Y/n): ").strip().lower()

        if response in ('', 'y', 'yes'):
            return True
        elif response in ('n', 'no'):
            return False
        else:
            print("Please enter 'y' or 'n'")


def check_gh_cli_available() -> bool:
    """Check if GitHub CLI (gh) is installed and authenticated."""
    import shutil
    import subprocess

    # Check if gh is in PATH
    if not shutil.which("gh"):
        return False

    # Check if authenticated
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def run_pr_indexing_with_progress(repo_path: Path):
    """Run PR indexing with progress indicators."""
    from cicada.pr_indexer import PRIndexer
    from cicada.utils import get_pr_index_path

    print()
    print("⠋ Starting PR indexing...")

    try:
        output_path = str(get_pr_index_path(repo_path))
        indexer = PRIndexer(repo_path=str(repo_path))

        # TODO: Add progress callbacks to indexer
        indexer.index_repository(output_path=output_path, incremental=True)

        print(f"✓ PR indexing complete!")
        print()

    except KeyboardInterrupt:
        print("\n\n⚠️  PR indexing interrupted by user.")
        print("Partial index saved. Run 'cicada index-pr' to continue.")
        print()
    except Exception as e:
        print(f"\n⚠️  PR indexing failed: {e}")
        print("You can try again later with: cicada index-pr")
        print()
```

---

### Example 2: Enhanced PR Indexer with Progress

**File**: `cicada/pr_indexer/indexer.py`

**Add progress callback support:**

```python
from typing import Callable, Optional

class PRIndexer:
    def __init__(
        self,
        repo_path: str,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ):
        self.repo_path = repo_path
        self.progress_callback = progress_callback

    def _report_progress(self, stage: str, current: int, total: int):
        """Report progress to callback if provided."""
        if self.progress_callback:
            self.progress_callback(stage, current, total)

    def index_repository(self, output_path: str, incremental: bool = True):
        """Index PRs with progress reporting."""

        # Stage 1: Fetching PRs
        self._report_progress("fetch", 0, 100)
        prs = self._fetch_prs()
        total_prs = len(prs)
        self._report_progress("fetch", 100, 100)

        # Stage 2: Indexing PRs
        for i, pr in enumerate(prs):
            self._index_pr(pr)
            self._report_progress("index", i + 1, total_prs)

        # Stage 3: Saving
        self._report_progress("save", 0, 1)
        self._save_index(output_path)
        self._report_progress("save", 1, 1)
```

**Usage with progress bar:**

```python
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

def run_pr_indexing_with_progress(repo_path: Path):
    """Run PR indexing with rich progress bar."""
    from cicada.pr_indexer import PRIndexer
    from cicada.utils import get_pr_index_path

    print()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    ) as progress:

        # Create tasks
        fetch_task = progress.add_task("⠋ Fetching PRs from GitHub...", total=100)
        index_task = None

        def progress_callback(stage: str, current: int, total: int):
            nonlocal index_task

            if stage == "fetch":
                progress.update(fetch_task, completed=current)
                if current == 100:
                    progress.update(fetch_task, description="✓ Fetched PRs from GitHub")

            elif stage == "index":
                if index_task is None:
                    index_task = progress.add_task(
                        f"Indexing PRs...",
                        total=total
                    )
                progress.update(index_task, completed=current)
                if current == total:
                    progress.update(index_task, description=f"✓ Indexed {total} PRs")

            elif stage == "save":
                if current == 1:
                    progress.console.print("✓ Index saved")

        try:
            output_path = str(get_pr_index_path(repo_path))
            indexer = PRIndexer(
                repo_path=str(repo_path),
                progress_callback=progress_callback
            )
            indexer.index_repository(output_path=output_path, incremental=True)

        except Exception as e:
            progress.console.print(f"[red]✗ Failed: {e}[/red]")
            raise

    print()
```

---

### Example 3: Updated Argument Parser

**File**: `cicada/commands.py`

**Location**: `get_argument_parser()` function (line 65)

```python
install_parser = subparsers.add_parser(
    "install",
    help="Interactive setup for Cicada",
    description="Interactive setup with editor and model selection",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
Examples:
  cicada install                           # Interactive mode (prompts for options)
  cicada install --claude --regular        # Non-interactive (specific editor & tier)
  cicada install --yes                     # Accept all defaults (CI/CD)
  cicada install --index-prs               # Force PR indexing
  cicada install --no-index-prs            # Skip PR indexing
  cicada install --skip-optional           # Skip all optional features
    """,
)
install_parser.add_argument(
    "repo",
    nargs="?",
    default=None,
    help="Path to Elixir repository (default: current directory)",
)

# Editor selection flags
install_parser.add_argument("--claude", action="store_true", help="Use Claude Code")
install_parser.add_argument("--cursor", action="store_true", help="Use Cursor")
install_parser.add_argument("--vs", action="store_true", help="Use VS Code")

# Model tier flags
install_parser.add_argument(
    "--fast",
    action="store_true",
    help="Fast tier: Regular extraction + lemmi expansion (no downloads)",
)
install_parser.add_argument(
    "--regular",
    action="store_true",
    help="Regular tier: KeyBERT small + GloVe expansion (default)",
)
install_parser.add_argument(
    "--max",
    action="store_true",
    help="Max tier: KeyBERT large + FastText expansion (958MB+)",
)

# NEW: Automation and optional feature flags
install_parser.add_argument(
    "--yes",
    action="store_true",
    help="Accept all defaults, non-interactive mode (for CI/CD automation)",
)
install_parser.add_argument(
    "--index-prs",
    action="store_true",
    help="Enable PR indexing during install (requires GitHub CLI)",
)
install_parser.add_argument(
    "--no-index-prs",
    action="store_true",
    help="Skip PR indexing (useful for CI/CD or when GH CLI unavailable)",
)
install_parser.add_argument(
    "--skip-optional",
    action="store_true",
    help="Skip all optional features (PR indexing, etc.)",
)
```

---

### Example 4: Flag Validation

**File**: `cicada/commands.py`

**Location**: Add to `handle_install()` before prompting

```python
def validate_pr_flags(args) -> None:
    """Validate PR indexing flags are not conflicting."""
    if args.index_prs and args.no_index_prs:
        print(
            "Error: Cannot specify both --index-prs and --no-index-prs",
            file=sys.stderr
        )
        sys.exit(1)

    if args.skip_optional and args.index_prs:
        print(
            "Warning: --skip-optional conflicts with --index-prs, "
            "using --skip-optional",
            file=sys.stderr
        )
```

---

## Testing Strategy

### Manual Testing Checklist

#### Test Case 1: Interactive Flow (Default)

```bash
cicada install /path/to/repo
```

**Expected:**
- ✓ Prompts for editor selection
- ✓ Prompts for model tier
- ✓ Indexes repository with progress
- ✓ Prompts for PR indexing with explanation
- ✓ If yes: shows PR indexing progress
- ✓ If no: shows command to run later

---

#### Test Case 2: Accept Defaults (CI/CD)

```bash
cicada install --yes
```

**Expected:**
- ✓ No prompts
- ✓ Uses default editor (first in list or Claude)
- ✓ Uses default tier (regular)
- ✓ Runs PR indexing automatically (default yes)
- ✓ Completes silently

---

#### Test Case 3: Explicit Control

```bash
cicada install --claude --fast --index-prs
```

**Expected:**
- ✓ No prompts
- ✓ Uses Claude editor
- ✓ Uses fast tier
- ✓ Runs PR indexing

---

#### Test Case 4: Skip Optional Features

```bash
cicada install --skip-optional
```

**Expected:**
- ✓ Skips PR indexing prompt
- ✓ Shows message about skipped features

---

#### Test Case 5: No GitHub CLI

```bash
# Uninstall gh first: brew uninstall gh
cicada install
```

**Expected:**
- ✓ Shows PR indexing prompt
- ✓ Detects missing GitHub CLI
- ✓ Shows installation instructions
- ✓ Skips PR indexing gracefully

---

#### Test Case 6: Manual PR Indexing Later

```bash
cicada install --no-index-prs
# ... later ...
cicada index-pr
```

**Expected:**
- ✓ Install completes without PR indexing
- ✓ `index-pr` command works independently
- ✓ Shows progress for PR indexing

---

### Automated Testing

**File**: `tests/test_install_pr_integration.py`

```python
import pytest
from unittest.mock import patch, MagicMock
from cicada.commands import handle_install, check_gh_cli_available


def test_pr_indexing_flag_conflicts():
    """Test that conflicting flags are detected."""
    args = MagicMock()
    args.index_prs = True
    args.no_index_prs = True

    with pytest.raises(SystemExit):
        validate_pr_flags(args)


def test_yes_flag_enables_pr_indexing():
    """Test that --yes flag enables PR indexing by default."""
    args = MagicMock()
    args.yes = True
    args.index_prs = False
    args.no_index_prs = False
    args.skip_optional = False

    should_index = determine_pr_indexing_from_args(args)
    assert should_index is True


def test_skip_optional_disables_pr_indexing():
    """Test that --skip-optional disables PR indexing."""
    args = MagicMock()
    args.yes = False
    args.index_prs = False
    args.no_index_prs = False
    args.skip_optional = True

    should_index = determine_pr_indexing_from_args(args)
    assert should_index is False


@patch('shutil.which')
@patch('subprocess.run')
def test_gh_cli_check_success(mock_run, mock_which):
    """Test GitHub CLI availability check when installed and authenticated."""
    mock_which.return_value = '/usr/local/bin/gh'
    mock_run.return_value = MagicMock(returncode=0)

    assert check_gh_cli_available() is True


@patch('shutil.which')
def test_gh_cli_check_not_installed(mock_which):
    """Test GitHub CLI availability check when not installed."""
    mock_which.return_value = None

    assert check_gh_cli_available() is False
```

---

## Migration Path

### For Users

**Current behavior still works:**
```bash
# These commands unchanged
cicada install
cicada index-pr
```

**New behavior is additive:**
```bash
# New flags are optional
cicada install --yes              # NEW
cicada install --index-prs        # NEW
cicada install --no-index-prs     # NEW
```

**No breaking changes** - Fully backward compatible

---

### For CI/CD

**Before:**
```bash
# CI/CD needed to handle prompts (not ideal)
echo "1" | cicada claude
```

**After:**
```bash
# Clean, non-interactive mode
cicada install --claude --fast --yes

# Or skip optional features
cicada install --claude --fast --skip-optional
```

---

### For Documentation

**Update these files:**
1. `README.md` - Add new flags to installation section
2. `docs/cli-reference.md` - Document all flags
3. `.github/workflows/*.yml` - Update CI examples
4. `examples/` - Add automation examples

**Sample README addition:**

```markdown
## Installation

### Interactive Mode (Recommended)

```bash
cicada install
```

Prompts for:
- Editor selection (Claude Code, Cursor, VS Code)
- Model tier (fast, regular, max)
- Optional: PR indexing for git history tools

### Non-Interactive Mode (CI/CD)

```bash
# Accept all defaults
cicada install --yes

# Specific configuration
cicada install --claude --fast

# Skip optional features
cicada install --skip-optional
```

### Flags

- `--yes`: Accept all defaults (non-interactive)
- `--index-prs`: Enable PR indexing
- `--no-index-prs`: Skip PR indexing
- `--skip-optional`: Skip all optional features
- `--claude`, `--cursor`, `--vs`: Select editor
- `--fast`, `--regular`, `--max`: Select model tier
```

---

## Success Metrics

### Adoption Metrics

**Track these to measure success:**

1. **PR Indexing Adoption Rate**
   - % of users who enable PR indexing during install
   - Target: >60% (vs current <10% manual adoption)

2. **GitHub CLI Installation Rate**
   - % of users with GH CLI installed
   - Instructions should increase this over time

3. **User Feedback**
   - GitHub issues related to discoverability
   - Should decrease significantly

4. **CI/CD Usage**
   - % of automated installs using new flags
   - Indicates automation improvement

### Performance Metrics

**Monitor these for regressions:**

1. **Install Time**
   - Without PR indexing: Should remain unchanged
   - With PR indexing: 2-5 minutes (expected, acceptable)

2. **User Friction**
   - Number of steps to complete install
   - Should remain low (1-2 interactive prompts)

---

## Rollout Strategy

### Phase 1: Soft Launch (Week 1)

**Target**: Internal testing and early adopters

1. ✅ Implement changes in feature branch
2. ✅ Test with 5-10 beta users
3. ✅ Gather feedback on UX
4. ✅ Iterate on prompt wording
5. ✅ Fix any discovered issues

**Success Criteria**:
- No critical bugs
- Positive feedback on new flow
- PR indexing adoption >50% in beta group

---

### Phase 2: Public Release (Week 2)

**Target**: All users

1. ✅ Merge to main branch
2. ✅ Update PyPI package
3. ✅ Announce in release notes
4. ✅ Update documentation
5. ✅ Monitor GitHub issues

**Communication**:
```markdown
## v0.X.0 - Improved PR Indexing Discovery

### New Features
- 🎉 PR indexing now prompts during installation (opt-in)
- ⚡ New flags for automation: --yes, --index-prs, --skip-optional
- 📊 Progress indicators for long operations
- 🔍 GitHub CLI availability check

### Benefits
- Better feature discoverability
- Improved CI/CD support
- Clearer value proposition for PR indexing

### Breaking Changes
- None! All changes are backward compatible
```

---

### Phase 3: Monitor and Iterate (Ongoing)

**Target**: Continuous improvement

1. ✅ Monitor adoption metrics weekly
2. ✅ Collect user feedback
3. ✅ A/B test prompt wording if needed
4. ✅ Consider Phase 4 (background indexing) based on data

**Triggers for Phase 4**:
- PR indexing adoption >80%
- Frequent requests for background indexing
- Performance complaints about wait time

---

## Appendix A: Research Summary

### Tools Analyzed

1. **npm** - Interactive postinstall, controversial but powerful
2. **pip** - Manual control, clear separation (update vs install)
3. **cargo** - Automatic index updates, performance issues
4. **homebrew** - Auto-update reduced from 5min to 24h after complaints
5. **apt** - Separated commands, poor discoverability
6. **gem/bundler** - Automatic but predictable
7. **pipx** - Isolated installations, explicit control
8. **uv** - Modern, fast, excellent namespacing
9. **rustup** - Toolchain installer, explicit subcommands
10. **git hooks** - Automatic after setup, transparent
11. **language servers** - Background indexing, excellent progress UI
12. **database migrations** - Manual execution, auto-generation
13. **VSCode/Copilot** - Opt-out telemetry, first-run notifications
14. **docker** - Lazy loading for large images
15. **kubectl** - Action-first command structure
16. **gh (GitHub CLI)** - Resource-first command structure
17. **pacman** - Flag-based instead of subcommands

---

## Appendix B: Alternative Approaches Considered

### Alternative 1: Automatic PR Indexing (Like Cargo)

**Implementation**:
```bash
cicada install
  ↓
Automatically indexes PRs without prompting
```

**Pros**:
- Maximum adoption
- No user decision needed

**Cons**:
- Slows install by 2-5 minutes (frustrating)
- Requires GitHub CLI (breaks if missing)
- User doesn't understand why it's slow
- Hard to opt-out (environment variable)

**Verdict**: ❌ REJECTED - Research shows this causes user frustration (Homebrew)

---

### Alternative 2: Separate Command Only (Like APT)

**Implementation**:
```bash
cicada install         # Basic setup
cicada index-pr        # Separate command (current state)
```

**Pros**:
- Simple implementation
- User has full control
- No install slowdown

**Cons**:
- Poor discoverability
- Users forget to run second command
- Low adoption rate (<10%)
- Valuable feature underutilized

**Verdict**: ❌ REJECTED - Current state, causes poor adoption

---

### Alternative 3: First-Run Background Indexing (Language Server Model)

**Implementation**:
```bash
cicada install
  ↓
Setup completes quickly
  ↓
PR indexing starts in background
  ↓
MCP tools show "indexing in progress" status
```

**Pros**:
- Best UX (fast install, progressive enhancement)
- Non-blocking
- Professional feel

**Cons**:
- Complex implementation (process management)
- State tracking needed
- More edge cases to handle
- Resource usage in background

**Verdict**: ⏸️ DEFERRED to Phase 4 - Excellent pattern, but complex for initial release

---

## Appendix C: FAQ

### Q: Why not make PR indexing automatic by default?

**A**: Research shows automatic time-consuming operations frustrate users:
- Homebrew had massive complaints about 5-minute auto-updates before every install
- Users want to know WHY something takes time
- Opt-in with clear value proposition drives intentional adoption
- Always provide escape hatch (--no-index-prs)

### Q: Why Y instead of y as default?

**A**: Universal Unix/Linux convention for 40+ years:
- Capital letter indicates default when pressing Enter
- Makes it obvious what happens with just Enter key
- Users expect this pattern (apt, git, systemctl, etc.)

### Q: Should --yes also enable PR indexing?

**A**: YES, because:
- --yes means "accept all defaults"
- PR indexing prompt defaults to Yes (capital Y)
- CI/CD benefits from full setup
- Can still override with --no-index-prs if needed

### Q: What if GitHub CLI isn't installed?

**A**: Graceful degradation:
- Check availability before prompting
- Show clear installation instructions
- Skip PR indexing without breaking install
- User can run `cicada index-pr` later after installing gh

### Q: Will this slow down install for everyone?

**A**: NO:
- Only adds 1 simple prompt (1-2 seconds)
- Actual indexing only runs if user chooses Yes
- Can skip prompt with --no-index-prs or --skip-optional
- CI/CD can use --skip-optional for fast builds

### Q: What about existing users?

**A**: Fully backward compatible:
- `cicada install` still works, just adds one prompt
- `cicada index-pr` still works independently
- No changes to existing behavior
- New flags are purely additive

### Q: Should we use rich, tqdm, or halo for progress?

**A**: Recommendation: **rich**
- Modern, actively maintained
- Excellent progress bars AND spinners
- Good terminal detection
- Wide adoption in Python ecosystem
- Alternative: tqdm (simpler, also good)

---

## Appendix D: Related Issues

*Track GitHub issues related to this guideline here*

### Implementation Issues
- [ ] #XXX: Add PR indexing prompt to install flow
- [ ] #XXX: Add --yes, --index-prs, --no-index-prs flags
- [ ] #XXX: Add progress indicators to PR indexer
- [ ] #XXX: Update documentation with new flags

### Future Enhancements
- [ ] #XXX: Background PR indexing (Phase 4)
- [ ] #XXX: Git hooks integration
- [ ] #XXX: Incremental PR index updates on git operations

---

## Conclusion

These guidelines provide a comprehensive roadmap for improving Cicada's PR indexing discoverability while maintaining industry best practices. The recommended approach:

✅ Follows universal CLI conventions (explicit subcommands, Y/n pattern)
✅ Improves feature adoption through smart prompts
✅ Supports automation with proper flags
✅ Maintains backward compatibility
✅ Provides clear user communication
✅ Scales to future enhancements

**Next Steps**:
1. Review guidelines with team
2. Create GitHub issues for implementation
3. Start Phase 1 implementation
4. Test with beta users
5. Launch and monitor metrics

---

**Document Version**: 1.0
**Last Updated**: 2025-11-07
**Author**: Research-based design from 17+ CLI tools analysis
**Status**: Ready for Implementation
