"""
PR Index Builder.

This module handles building and merging PR index structures,
separating index construction logic from API and mapping concerns.
"""

from datetime import datetime
from typing import Any

from cicada.utils import load_index as load_index_util
from cicada.utils import save_index as save_index_util


class PRIndexBuilder:
    """
    Builds and manages PR index structures.

    This class handles creating, merging, and saving PR indexes,
    keeping index manipulation separate from data fetching.
    """

    def __init__(self, repo_owner: str, repo_name: str):
        """
        Initialize the index builder.

        Args:
            repo_owner: GitHub repository owner
            repo_name: GitHub repository name
        """
        self.repo_owner = repo_owner
        self.repo_name = repo_name

    def build_index(
        self, prs: list[dict[str, Any]], preserve_last_pr: int | None = None
    ) -> dict[str, Any]:
        """
        Build the index structure from PR data.

        Args:
            prs: List of PR dictionaries
            preserve_last_pr: If set, use this as last_pr_number instead of calculating.
                             Used when building partial indexes from interrupted fetches.

        Returns:
            Index dictionary with metadata, prs, commit_to_pr mapping, and file_to_prs mapping
        """
        print("Building index...")

        # Build commit -> PR mapping
        commit_to_pr = self._build_commit_mapping(prs)

        # Build file -> PRs mapping
        file_to_prs = self._build_file_mapping(prs)

        # Count total comments
        total_comments = sum(len(pr.get("comments", [])) for pr in prs)

        # Build index structure
        metadata: dict[str, Any] = {
            "repo_owner": self.repo_owner,
            "repo_name": self.repo_name,
            "last_indexed_at": datetime.now().isoformat(),
            "total_prs": len(prs),
            "total_commits_mapped": len(commit_to_pr),
            "total_comments": total_comments,
            "total_files": len(file_to_prs),
        }
        index: dict[str, Any] = {
            "metadata": metadata,
            "prs": {str(pr["number"]): pr for pr in prs},
            "commit_to_pr": commit_to_pr,
            "file_to_prs": file_to_prs,
        }

        # Track last PR number for incremental updates
        if preserve_last_pr is not None:
            # Use preserved value (for partial/interrupted fetches)
            index["metadata"]["last_pr_number"] = preserve_last_pr
        elif prs:
            # Calculate from PRs (for complete fetches)
            index["metadata"]["last_pr_number"] = max(pr["number"] for pr in prs)

        print(
            f"Index built: {len(prs)} PRs, {len(commit_to_pr)} commits, "
            f"{len(file_to_prs)} files, {total_comments} comments"
        )
        return index

    def _build_commit_mapping(self, prs: list[dict[str, Any]]) -> dict[str, int]:
        """
        Build commit SHA -> PR number mapping.

        Args:
            prs: List of PR dictionaries

        Returns:
            Dictionary mapping commit SHAs to PR numbers
        """
        commit_to_pr = {}
        for pr in prs:
            pr_number = pr["number"]
            for commit in pr["commits"]:
                commit_to_pr[commit] = pr_number
        return commit_to_pr

    def _build_file_mapping(self, prs: list[dict[str, Any]]) -> dict[str, list[int]]:
        """
        Build file path -> PR numbers mapping.

        Args:
            prs: List of PR dictionaries

        Returns:
            Dictionary mapping file paths to lists of PR numbers (sorted newest first)
        """
        file_to_prs = {}
        for pr in prs:
            pr_number = pr["number"]
            for file_path in pr.get("files_changed", []):
                if file_path not in file_to_prs:
                    file_to_prs[file_path] = []
                file_to_prs[file_path].append(pr_number)

        # Sort PR numbers for each file (newest first)
        for file_path in file_to_prs:
            file_to_prs[file_path].sort(reverse=True)

        return file_to_prs

    def merge_indexes(
        self, existing_index: dict[str, Any], new_prs: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Merge new PRs into existing index.

        Args:
            existing_index: The existing index
            new_prs: List of new PR dictionaries

        Returns:
            Updated index dictionary
        """
        print("Merging new PRs into existing index...")

        # Update PR data
        for pr in new_prs:
            existing_index["prs"][str(pr["number"])] = pr

            # Update commit -> PR mapping
            for commit in pr["commits"]:
                existing_index["commit_to_pr"][commit] = pr["number"]

        # Rebuild file -> PRs mapping from scratch (most reliable)
        file_to_prs = self._build_file_mapping(list(existing_index["prs"].values()))
        existing_index["file_to_prs"] = file_to_prs

        # Count total comments
        total_comments = sum(len(pr.get("comments", [])) for pr in existing_index["prs"].values())

        # Update metadata
        existing_index["metadata"]["last_indexed_at"] = datetime.now().isoformat()
        existing_index["metadata"]["total_prs"] = len(existing_index["prs"])
        existing_index["metadata"]["total_commits_mapped"] = len(existing_index["commit_to_pr"])
        existing_index["metadata"]["total_comments"] = total_comments
        existing_index["metadata"]["total_files"] = len(file_to_prs)

        # Update last_pr_number to the highest PR we have in the index
        if existing_index["prs"]:
            all_pr_numbers = [int(num) for num in existing_index["prs"]]
            existing_index["metadata"]["last_pr_number"] = max(all_pr_numbers)

        return existing_index

    def merge_partial_clean(
        self, existing_index: dict[str, Any], partial_index: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Merge a partial clean build with an existing index.

        This is used when a --clean rebuild is interrupted. We want to keep both:
        - PRs from the existing index (old data)
        - PRs from the partial new index (newly fetched data)

        Args:
            existing_index: The old complete/partial index
            partial_index: The new partial index from interrupted --clean

        Returns:
            Merged index with all PRs from both indexes
        """
        print("Merging partial index with existing index...")

        # Start with existing index structure
        merged = existing_index.copy()

        # Update PRs: add/replace with new PRs from partial index
        for pr_num_str, pr_data in partial_index["prs"].items():
            merged["prs"][pr_num_str] = pr_data

        # Rebuild commit -> PR mapping from scratch
        merged["commit_to_pr"] = self._build_commit_mapping(list(merged["prs"].values()))

        # Rebuild file -> PRs mapping from scratch
        merged["file_to_prs"] = self._build_file_mapping(list(merged["prs"].values()))

        # Count total comments
        total_comments = sum(len(pr.get("comments", [])) for pr in merged["prs"].values())

        # Update metadata (use partial_index's last_pr_number which was preserved)
        merged["metadata"]["last_indexed_at"] = datetime.now().isoformat()
        merged["metadata"]["total_prs"] = len(merged["prs"])
        merged["metadata"]["total_commits_mapped"] = len(merged["commit_to_pr"])
        merged["metadata"]["total_comments"] = total_comments
        merged["metadata"]["total_files"] = len(merged["file_to_prs"])
        merged["metadata"]["last_pr_number"] = partial_index["metadata"].get("last_pr_number", 0)

        print(f"Merged: {len(merged['prs'])} total PRs ({len(partial_index['prs'])} new/updated)")
        return merged

    def load_existing_index(self, index_path: str) -> dict[str, Any] | None:
        """
        Load existing index file if it exists.

        Args:
            index_path: Path to the index file

        Returns:
            Existing index dictionary or None if file doesn't exist
        """
        return load_index_util(index_path, verbose=True, raise_on_error=False)

    def save_index(self, index: dict[str, Any], output_path: str) -> None:
        """
        Save index to file.

        Args:
            index: Index dictionary to save
            output_path: Path where the index will be saved
        """
        save_index_util(index, output_path, create_dirs=True, verbose=True)
