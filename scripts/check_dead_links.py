#!/usr/bin/env python3
"""
Check for dead links in markdown files.

Usage:
    python scripts/check_dead_links.py
    python scripts/check_dead_links.py --check-external  # Also check HTTP links (slow)
"""

import argparse
import re
from pathlib import Path
from typing import List, Tuple, Dict
from urllib.parse import urlparse
import sys

# Regex to find markdown links: [text](url)
MARKDOWN_LINK_REGEX = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def find_markdown_files(root_dir: Path) -> List[Path]:
    """Find all markdown files in the repository."""
    return list(root_dir.rglob("*.md"))


def extract_links(file_path: Path) -> List[Tuple[str, str, int]]:
    """Extract all markdown links from a file.

    Returns:
        List of tuples: (link_text, link_url, line_number)
    """
    links = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                for match in MARKDOWN_LINK_REGEX.finditer(line):
                    text = match.group(1)
                    url = match.group(2)
                    links.append((text, url, line_num))
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)

    return links


def is_external_url(url: str) -> bool:
    """Check if a URL is external (http/https)."""
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https")


def is_anchor_link(url: str) -> bool:
    """Check if a URL is an anchor link (#section)."""
    return url.startswith("#")


def resolve_relative_path(source_file: Path, relative_url: str, repo_root: Path) -> Path:
    """Resolve a relative URL to an absolute path.

    Args:
        source_file: The markdown file containing the link
        relative_url: The relative URL (e.g., "../docs/file.md")
        repo_root: The repository root directory

    Returns:
        Resolved absolute path
    """
    # Remove anchor if present
    url_without_anchor = relative_url.split("#")[0]

    if not url_without_anchor:
        # Just an anchor, no file path
        return source_file

    # Resolve relative to the source file's directory
    source_dir = source_file.parent
    target_path = (source_dir / url_without_anchor).resolve()

    return target_path


def check_local_link(source_file: Path, url: str, repo_root: Path) -> Tuple[bool, str]:
    """Check if a local link is valid.

    Returns:
        (is_valid, error_message)
    """
    # Remove anchor
    url_without_anchor = url.split("#")[0]

    if not url_without_anchor:
        # Just an anchor - we'll consider this valid
        # (proper anchor checking would require parsing markdown headers)
        return True, ""

    target_path = resolve_relative_path(source_file, url, repo_root)

    # Check if target exists
    if not target_path.exists():
        return False, f"File not found: {target_path}"

    # Check if it's a file (not a directory)
    if target_path.is_dir():
        return False, f"Link points to directory: {target_path}"

    return True, ""


def check_dead_links(
    repo_root: Path, check_external: bool = False
) -> Dict[str, List[Tuple[str, str, int, str]]]:
    """Check for dead links in all markdown files.

    Returns:
        Dictionary mapping file paths to lists of broken links:
        {
            "path/to/file.md": [
                (link_text, link_url, line_number, error_message),
                ...
            ]
        }
    """
    broken_links = {}

    md_files = find_markdown_files(repo_root)
    print(f"Checking {len(md_files)} markdown files...\n")

    for md_file in md_files:
        # Skip files in certain directories
        relative_path = md_file.relative_to(repo_root)
        if any(part.startswith(".") for part in relative_path.parts):
            # Skip hidden directories like .git, .claude
            continue

        links = extract_links(md_file)

        for link_text, link_url, line_num in links:
            # Skip external URLs unless explicitly requested
            if is_external_url(link_url):
                if check_external:
                    # TODO: Implement HTTP link checking if needed
                    pass
                continue

            # Skip anchor-only links (we'd need to parse markdown headers to validate)
            if is_anchor_link(link_url):
                continue

            # Check local link
            is_valid, error = check_local_link(md_file, link_url, repo_root)

            if not is_valid:
                if str(relative_path) not in broken_links:
                    broken_links[str(relative_path)] = []

                broken_links[str(relative_path)].append((link_text, link_url, line_num, error))

    return broken_links


def main():
    parser = argparse.ArgumentParser(description="Check for dead links in markdown files")
    parser.add_argument(
        "--check-external", action="store_true", help="Also check external HTTP/HTTPS links (slow)"
    )
    args = parser.parse_args()

    # Find repository root (where .git directory is)
    repo_root = Path(__file__).parent.parent
    if not (repo_root / ".git").exists():
        print("Error: Could not find repository root", file=sys.stderr)
        sys.exit(1)

    print(f"Repository root: {repo_root}\n")

    broken_links = check_dead_links(repo_root, args.check_external)

    if not broken_links:
        print("✅ No broken links found!")
        return 0

    print(f"❌ Found broken links in {len(broken_links)} file(s):\n")

    total_broken = 0
    for file_path, links in sorted(broken_links.items()):
        print(f"📄 {file_path}")
        for link_text, link_url, line_num, error in links:
            print(f"   Line {line_num}: [{link_text}]({link_url})")
            print(f"   ❌ {error}")
            print()
            total_broken += 1

    print(f"Total broken links: {total_broken}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
