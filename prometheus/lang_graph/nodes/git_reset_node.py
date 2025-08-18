import logging
import threading

from prometheus.git.git_repository import GitRepository


class GitResetNode:
    def __init__(
        self,
        git_repo: GitRepository,
    ):
        self.git_repo = git_repo
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.git_reset_node"
        )

    def __call__(self, _):
        self._logger.debug("Resetting the git repository")
        self.git_repo.reset_repository()
