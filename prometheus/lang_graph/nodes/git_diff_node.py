"""Git diff generation for project changes.

This module provides functionality to generate Git diffs for changes made to a project,
typically used to track modifications made during automated issue resolution or code
fixes. It uses the GitRepository class to access Git operations and generate patch
output.
"""

import logging
import threading
from typing import Dict, Optional

from prometheus.git.git_repository import GitRepository


class GitDiffNode:
    """Generates Git diffs for project modifications.

    This class handles the generation of Git diffs to track changes made to a project.
    It works with a GitRepository instance to access the project's Git operations
    and create patch output. The node is typically used as part of an automated
    workflow to capture code modifications made during issue resolution.
    """

    def __init__(
        self,
        git_repo: GitRepository,
        state_patch_name: str,
        state_excluded_files_key: Optional[str] = None,
        return_list: bool = False,
    ):
        self.git_repo = git_repo
        self.state_patch_name = state_patch_name
        self.state_excluded_files_key = state_excluded_files_key
        self.return_list = return_list
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.git_diff_node"
        )

    def __call__(self, state: Dict):
        """Generates a Git diff for the current project state.

        Creates a Git repository instance for the project path specified in the
        state and generates a diff of any uncommitted changes.

        Args:
          state: Current state containing project information, including the
            project_path key specifying the Git repository location.

        Returns:
          Dictionary that updates the state containing:
          - patch: String containing the Git diff output showing all changes made to the project.
        """
        excluded_files = None
        if (
            self.state_excluded_files_key
            and self.state_excluded_files_key in state
            and state[self.state_excluded_files_key]
        ):
            excluded_files = state[self.state_excluded_files_key]
            if isinstance(excluded_files, str):
                excluded_files = [excluded_files]
            self._logger.debug(
                f"Excluding the following files when generating the patch: {excluded_files}"
            )
        patch = self.git_repo.get_diff(excluded_files)
        if patch:
            self._logger.info(f"Generated patch:\n{patch}")
            result = [patch] if self.return_list else patch
        else:
            self._logger.info("No changes detected, no patch generated.")
            result = [] if self.return_list else ""

        return {self.state_patch_name: result}
