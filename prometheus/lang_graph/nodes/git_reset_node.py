import logging
from typing import Dict, Sequence

from prometheus.git.git_repository import GitRepository


class GitResetNode:
    def __init__(self, git_repo: GitRepository, exclude_files_key: str = None):
        self.git_repo = git_repo
        self._logger = logging.getLogger("prometheus.lang_graph.nodes.git_reset_node")
        self.exclude_files_key = exclude_files_key

    def __call__(self, state: Dict):
        self._logger.debug("Resetting the git repository")
        excluded_files = []
        if (
            self.exclude_files_key
            and self.exclude_files_key in state
            and state[self.exclude_files_key]
        ):
            excluded_files = state[self.exclude_files_key]
            if not isinstance(excluded_files, Sequence):
                excluded_files = [excluded_files]
            excluded_files = [str(f) for f in excluded_files]
            self._logger.debug(
                f"Excluding the following files when resetting the repository: {excluded_files}"
            )
        self.git_repo.reset_repository(excluded_files)
