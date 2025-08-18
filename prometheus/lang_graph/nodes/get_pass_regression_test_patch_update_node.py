import logging
import threading

from prometheus.git.git_repository import GitRepository
from prometheus.lang_graph.subgraphs.get_pass_regression_test_patch_state import (
    GetPassRegressionTestPatchState,
)


class GetPassRegressionTestPatchUpdateNode:
    """
    Reset the Git repository and apply the first untested patch to the Git repository.
    """

    def __init__(
        self,
        git_repo: GitRepository,
    ):
        self.git_repo = git_repo
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.get_pass_regression_test_patch_update_node"
        )

    def __call__(self, state: GetPassRegressionTestPatchState):
        """
        Reset the Git repository and apply the first untested patch to the Git repository.

        Args:
          state: Current state containing untested patches.
        """
        if not state["untested_patches"]:
            self._logger.warning("No untested patches available to apply.")
            return state

        patch = state["untested_patches"][0]
        self._logger.info(f"Applying patch: {patch}")

        # Reset the Git repository to a clean state
        self.git_repo.reset_repository()

        # Apply the patch
        self.git_repo.apply_patch(patch)

        return {
            "untested_patches": state["untested_patches"][1:],  # Remove the applied patch
            "current_patch": patch,  # Store the current patch
        }
