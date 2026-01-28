#!/usr/bin/env python3
"""
Fix broken links in codebook/tasks/ and codebook/RandD/ files.

These files reference feature documentation in codebook/ using simple names
like KEYWORD_SEARCH.md, but they need to use ../KEYWORD_SEARCH.md instead.
"""

import re
from pathlib import Path
import sys

# Map of simple names to actual files in codebook/
CODEBOOK_FILES = {
    "AST_INDEXING.md": "../AST_INDEXING.md",
    "INCREMENTAL_INDEXING.md": "../INCREMENTAL_INDEXING.md",
    "AUTOMATIC_LANGUAGE_DETECTION.md": "../AUTOMATIC_LANGUAGE_DETECTION.md",
    "STRING_INDEXING.md": "../STRING_INDEXING.md",
    "KEYWORD_SEARCH.md": "../KEYWORD_SEARCH.md",
    "KEYWORD_INDEXING.md": "../KEYWORD_INDEXING.md",
    "LANGUAGE_SUPPORT.md": "../LANGUAGE_SUPPORT.md",
    "CODE_ANALYSIS.md": "../CODE_ANALYSIS.md",
    "GIT_HISTORY.md": "../GIT_HISTORY.md",
    "MCP_TOOLS.md": "../MCP_TOOLS.md",
    "CLI_TOOLS.md": "../CLI_TOOLS.md",
    "AI_AGENTS.md": "../AI_AGENTS.md",
    "WORKFLOWS.md": "../WORKFLOWS.md",
    "INSTALLATION.md": "../INSTALLATION.md",
    "ARCHITECTURE.md": "../ARCHITECTURE.md",
    "PERFORMANCE.md": "../PERFORMANCE.md",
    "MCP-Tools-Reference.md": "../MCP_TOOLS.md",  # Rename
    "PR_INDEXING.md": "202511192143-PR_INDEXING.md",  # It's in the same dir
    "EXTENDED_GIT_HISTORY.md": "202511052055-EXTENDED_GIT_HISTORY.md",  # It's in the same dir
}


def fix_links_in_file(file_path: Path) -> int:
    """Fix broken links in a single file.

    Returns:
        Number of fixes made
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return 0

    original_content = content
    fixes = 0

    for simple_name, correct_path in CODEBOOK_FILES.items():
        # Match [text](SIMPLE_NAME) or [text](SIMPLE_NAME#anchor)
        pattern = rf"\]\(({re.escape(simple_name)}(?:#[^)]*)?)\)"

        def replace_func(match):
            nonlocal fixes
            url = match.group(1)
            # Preserve anchor if present
            if "#" in url:
                anchor = url.split("#", 1)[1]
                new_url = f"{correct_path}#{anchor}"
            else:
                new_url = correct_path
            fixes += 1
            return f"]({new_url})"

        content = re.sub(pattern, replace_func, content)

    if content != original_content:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Fixed {fixes} link(s) in {file_path}")
            return fixes
        except Exception as e:
            print(f"Error writing {file_path}: {e}", file=sys.stderr)
            return 0

    return 0


def main():
    repo_root = Path(__file__).parent.parent
    codebook_dir = repo_root / "codebook"

    total_fixes = 0

    # Fix links in tasks/
    tasks_dir = codebook_dir / "tasks"
    if tasks_dir.exists():
        for file_path in tasks_dir.glob("*.md"):
            total_fixes += fix_links_in_file(file_path)

    # Fix links in RandD/
    randd_dir = codebook_dir / "RandD"
    if randd_dir.exists():
        for file_path in randd_dir.glob("*.md"):
            total_fixes += fix_links_in_file(file_path)

    # Also fix the placeholder link in CICADA_AGENT
    cicada_agent_file = codebook_dir / "tasks" / "202512242110-CICADA_AGENT.md"
    if cicada_agent_file.exists():
        try:
            with open(cicada_agent_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Fix placeholder link [Link to full PR](url)
            if "](url)" in content:
                content = content.replace("](url)", "](https://github.com/wende/cicada/pull/XXX)")
                with open(cicada_agent_file, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"Fixed placeholder link in {cicada_agent_file}")
                total_fixes += 1
        except Exception as e:
            print(f"Error fixing placeholder link: {e}", file=sys.stderr)

    print(f"\nTotal fixes: {total_fixes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
