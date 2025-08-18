import logging
import threading
from typing import Dict

from prometheus.git.git_repository import GitRepository


class GitApplyPatchNode:
    """Git Apply Patch Node.
    This node applies a given patch to a Git repository.
    """

    def __init__(self, git_repo: GitRepository, state_patch_name: str):
        self.git_repo = git_repo
        self.state_patch_name = state_patch_name
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.git_apply_patch_node"
        )

    def __call__(self, state: Dict):
        """
        Git Apply Patch Node.
        This method applies a patch to the Git repository specified in the state.
        """
        if self.state_patch_name in state and state[self.state_patch_name]:
            patch = state[self.state_patch_name]
            self._logger.info(f"Applying patch: {patch}")
            self.git_repo.apply_patch(patch)
            self._logger.info("Patch applied successfully.")
        else:
            self._logger.warning(f"No patch applied for key: {self.state_patch_name}")
