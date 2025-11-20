"""
PR Indexer - Indexes pull requests and their commits for fast offline lookup.

Fetches all PRs from a GitHub repository and builds an index mapping commits to PRs.
"""

from pathlib import Path
from typing import Any

from cicada.utils import is_git_repository

from .github_api_client import GitHubAPIClient
from .line_mapper import LineMapper
from .pr_index_builder import PRIndexBuilder


class PRIndexer:
    """
    Indexes GitHub pull requests for fast offline lookup.

    This class orchestrates the indexing process, delegating to specialized
    components for API interaction, index building, and line mapping.
    """

    def __init__(self, repo_path: str = "."):
        """
        Initialize the PR indexer.

        Args:
            repo_path: Path to the git repository (defaults to current directory)
        """
        self.repo_path = Path(repo_path).resolve()
        self._validate_git_repo()

        # Initialize API client and get repo info
        temp_client = GitHubAPIClient(self.repo_path, "", "")
        temp_client.validate_gh_cli()
        self.repo_owner, self.repo_name = temp_client.get_repo_info()

        # Initialize components
        self.api_client = GitHubAPIClient(self.repo_path, self.repo_owner, self.repo_name)
        self.index_builder = PRIndexBuilder(self.repo_owner, self.repo_name)
        self.line_mapper = LineMapper(self.repo_path)

    def _validate_git_repo(self):
        """Validate that the path is a git repository."""
        if not is_git_repository(self.repo_path):
            raise ValueError(f"Not a git repository: {self.repo_path}")

    def _handle_fetch_error(
        self,
        detailed_prs: list[dict[str, Any]],
        total_to_fetch: int,
        exception: Exception | None,
        newer_pr_numbers: list[int] | None = None,
        newer_prs_completed: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Handle errors during PR fetching with gap prevention.

        Args:
            detailed_prs: PRs fetched so far
            total_to_fetch: Total number of PRs being fetched
            exception: The exception that occurred (None for KeyboardInterrupt)
            newer_pr_numbers: List of newer PRs being fetched (None if not applicable)
            newer_prs_completed: Whether newer PRs section completed

        Returns:
            Partial results if safe to save

        Raises:
            Original exception if not safe to save
        """
        # Check gap prevention: can't save partial newer PRs
        if newer_pr_numbers and not newer_prs_completed:
            # Partial newer PRs create a gap - can't save safely
            error_type = "Interrupted" if exception is None else "Error"
            print(
                f"\n\nWARNING: {error_type} during newer PRs fetch. "
                "Cannot save partial results (would create gaps in index)."
            )
            print(f"Fetched {len(detailed_prs)}/{len(newer_pr_numbers)} newer PRs.")
            if exception:
                print(f"Error: {exception}")
            print("Run 'cicada index-pr' again to retry.\n")

            # Re-raise to prevent saving
            if exception is None:
                raise KeyboardInterrupt
            else:
                raise exception

        # Safe to save
        if detailed_prs:
            action = "Interrupted by user" if exception is None else "Error occurred"
            print(f"\n\nWARNING: {action}. Fetched {len(detailed_prs)}/{total_to_fetch} PRs.")
            if exception:
                print(f"Error: {exception}")
            print("Saving partial index to preserve progress...")
            if exception:
                print("Run 'cicada index-pr' again to resume from where it failed.\n")
            return detailed_prs
        else:
            # No progress made, re-raise
            if exception is None:
                raise KeyboardInterrupt
            else:
                raise RuntimeError(f"Failed to fetch PRs: {exception}") from exception

    def fetch_all_prs(self, state: str = "all") -> list[dict[str, Any]]:
        """
        Fetch all pull requests from GitHub using GraphQL for efficiency.

        Args:
            state: PR state filter ('all', 'open', 'closed', 'merged')

        Returns:
            List of PR dictionaries with full details
        """
        print(f"Fetching PRs from {self.repo_owner}/{self.repo_name}...")

        try:
            # Get list of PR numbers
            # Use a very high limit to ensure we don't miss PRs in large repos
            pr_numbers = self.api_client.fetch_pr_list(state=state, limit=100000)
            print(f"Found {len(pr_numbers)} pull requests")

            # Fetch detailed PR info in batches
            detailed_prs = []
            batch_size = 10
            total_batches = (len(pr_numbers) + batch_size - 1) // batch_size

            try:
                for i in range(0, len(pr_numbers), batch_size):
                    batch = pr_numbers[i : i + batch_size]
                    print(
                        f"  Fetching batch {i//batch_size + 1}/{total_batches} "
                        f"({len(batch)} PRs)..."
                    )

                    batch_prs = self.api_client.fetch_prs_batch_graphql(batch)
                    detailed_prs.extend(batch_prs)

            except KeyboardInterrupt:
                return self._handle_fetch_error(detailed_prs, len(pr_numbers), None)

            except (RuntimeError, Exception) as e:
                return self._handle_fetch_error(detailed_prs, len(pr_numbers), e)

            return detailed_prs

        except RuntimeError as e:
            raise RuntimeError(f"Failed to fetch PRs: {e}") from e

    def incremental_update(self, existing_index: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Fetch PRs bidirectionally: newer (above max) and older (below min).

        Args:
            existing_index: The existing index dictionary

        Returns:
            List of new PRs
        """
        # Get min and max PR numbers currently in the index
        existing_pr_numbers = [int(num) for num in existing_index.get("prs", {})]

        if not existing_pr_numbers:
            print("Empty index, performing full fetch...")
            return self.fetch_all_prs()

        min_pr = min(existing_pr_numbers)
        max_pr = max(existing_pr_numbers)
        total_prs_in_repo = self.api_client.get_total_pr_count()

        print(
            f"Performing incremental update (index range: #{min_pr}-#{max_pr}, "
            f"repo has {total_prs_in_repo} PRs)..."
        )

        # Fetch newer PRs (> max_pr)
        newer_pr_numbers = self._fetch_newer_prs(max_pr)

        # Fetch older PRs (< min_pr)
        older_pr_numbers = self._fetch_older_prs(min_pr)

        all_to_fetch = newer_pr_numbers + older_pr_numbers

        if not all_to_fetch:
            print("Index is complete (no newer or older PRs to fetch)")
            return []

        print(f"Found {len(newer_pr_numbers)} newer PRs", end="")
        if older_pr_numbers:
            print(
                f" and {len(older_pr_numbers)} older PRs to fetch "
                f"(going downward from #{min_pr})"
            )
        else:
            print()

        # Fetch detailed info for all PRs
        detailed_prs = self._fetch_prs_in_batches(newer_pr_numbers, older_pr_numbers, min_pr)

        return detailed_prs

    def _fetch_newer_prs(self, max_pr: int) -> list[int]:
        """Fetch PR numbers newer than max_pr."""
        pr_numbers = self.api_client.fetch_pr_list(state="all", limit=1000)

        # PRs are returned newest-first, so stop when we hit max_pr
        newer = []
        for pr_num in pr_numbers:
            if pr_num <= max_pr:
                break
            newer.append(pr_num)

        return newer

    def _fetch_older_prs(self, min_pr: int) -> list[int]:
        """Fetch PR numbers older than min_pr."""
        if min_pr <= 1:
            return []

        try:
            # Fetch all PRs and filter for ones < min_pr
            # Use a very high limit to ensure we don't miss older PRs in large repos
            all_prs = self.api_client.fetch_pr_list(state="all", limit=100000)
            older = sorted(
                [pr_num for pr_num in all_prs if pr_num < min_pr],
                reverse=True,  # Descending order
            )
            return older

        except RuntimeError as e:
            print(f"Warning: Could not fetch older PRs: {e}")
            return []

    def _fetch_prs_in_batches(
        self, newer_pr_numbers: list[int], older_pr_numbers: list[int], min_pr: int
    ) -> list[dict[str, Any]]:
        """
        Fetch PRs in batches, showing progress.

        IMPORTANT: Partial results are only safe for older PRs.
        If newer PRs fail partially, we MUST NOT save because it creates a gap
        in the index (the max_pr would skip unfetched IDs).
        """
        detailed_prs = []
        batch_size = 10
        total_to_fetch = len(newer_pr_numbers) + len(older_pr_numbers)
        newer_prs_completed = False  # Track if we finished newer PRs section

        try:
            # Fetch newer PRs first
            if newer_pr_numbers:
                newer_batches = (len(newer_pr_numbers) + batch_size - 1) // batch_size
                print(f"\n⬆️  Fetching {len(newer_pr_numbers)} newer PRs...")
                for i in range(0, len(newer_pr_numbers), batch_size):
                    batch = newer_pr_numbers[i : i + batch_size]
                    print(f"  Batch {i//batch_size + 1}/{newer_batches} ({len(batch)} PRs)...")
                    batch_prs = self.api_client.fetch_prs_batch_graphql(batch)
                    detailed_prs.extend(batch_prs)

            # Mark newer PRs as completed
            newer_prs_completed = True

            # Then fetch older PRs
            if older_pr_numbers:
                older_batches = (len(older_pr_numbers) + batch_size - 1) // batch_size
                print(
                    f"\n⬇️  Fetching {len(older_pr_numbers)} older PRs "
                    f"(going downward from #{min_pr})..."
                )
                for i in range(0, len(older_pr_numbers), batch_size):
                    batch = older_pr_numbers[i : i + batch_size]
                    print(f"  Batch {i//batch_size + 1}/{older_batches} ({len(batch)} PRs)...")
                    batch_prs = self.api_client.fetch_prs_batch_graphql(batch)
                    detailed_prs.extend(batch_prs)

        except KeyboardInterrupt:
            return self._handle_fetch_error(
                detailed_prs, total_to_fetch, None, newer_pr_numbers, newer_prs_completed
            )

        except (RuntimeError, Exception) as e:
            return self._handle_fetch_error(
                detailed_prs, total_to_fetch, e, newer_pr_numbers, newer_prs_completed
            )

        return detailed_prs

    def index_repository(self, output_path: str, incremental: bool = False):
        """
        Index the repository's PRs and save to file.

        Args:
            output_path: Path where the index will be saved
            incremental: If True, only fetch new PRs since last index
        """
        # Load existing index to preserve last_pr_number if clean build is interrupted
        existing_index = self.index_builder.load_existing_index(output_path)

        if incremental:
            if existing_index:
                # Fetch only new PRs
                new_prs = self.incremental_update(existing_index)

                if not new_prs:
                    print("No new PRs found. Index is up to date.")
                    return existing_index

                # Map comment lines
                self.line_mapper.map_all_comment_lines(new_prs)

                # Merge new PRs into existing index
                index = self.index_builder.merge_indexes(existing_index, new_prs)
            else:
                print("No existing index found. Performing full index...")
                index = self._perform_full_index(existing_index)
        else:
            # Full index (--clean)
            index = self._perform_full_index(existing_index)

        # Save index
        self.index_builder.save_index(index, output_path)
        return index

    def _perform_full_index(self, existing_index: dict[str, Any] | None) -> dict[str, Any]:
        """Perform a full index build."""
        total_prs_in_repo = self.api_client.get_total_pr_count()
        print(f"Starting clean rebuild ({total_prs_in_repo} PRs in repository)...")

        prs = self.fetch_all_prs()

        # Map comment lines
        self.line_mapper.map_all_comment_lines(prs)

        # Check if this is a partial/interrupted fetch
        is_partial = len(prs) < total_prs_in_repo

        if is_partial:
            print(f"WARNING: Partial fetch: got {len(prs)}/{total_prs_in_repo} PRs.")
            print("   Setting last_pr_number=0 to allow incremental resume...")

            if existing_index:
                # Merge with existing index to preserve PR data
                print("   Merging with existing index to preserve PR data...")
                new_index = self.index_builder.build_index(prs, preserve_last_pr=0)
                return self.index_builder.merge_partial_clean(existing_index, new_index)
            else:
                # No existing index - build new one with last_pr_number=0
                return self.index_builder.build_index(prs, preserve_last_pr=0)
        else:
            # Complete fetch
            return self.index_builder.build_index(prs)
