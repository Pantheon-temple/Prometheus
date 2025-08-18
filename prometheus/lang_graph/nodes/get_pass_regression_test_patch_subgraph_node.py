import logging
import threading
from typing import Dict

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.errors import GraphRecursionError

from prometheus.docker.base_container import BaseContainer
from prometheus.git.git_repository import GitRepository
from prometheus.lang_graph.subgraphs.get_pass_regression_test_patch_subgraph import (
    GetPassRegressionTestPatchSubgraph,
)
from prometheus.models.test_patch_result import TestedPatchResult


class GetPassRegressionTestPatchSubgraphNode:
    def __init__(
        self,
        model: BaseChatModel,
        container: BaseContainer,
        git_repo: GitRepository,
        testing_patch_key: str,
        is_testing_patch_list: bool,
    ):
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.get_pass_regression_test_patch_subgraph_node"
        )
        self.subgraph = GetPassRegressionTestPatchSubgraph(
            base_model=model,
            container=container,
            git_repo=git_repo,
        )
        self.git_repo = git_repo
        self.testing_patch_key = testing_patch_key
        self.is_testing_patch_list = is_testing_patch_list

    def __call__(self, state: Dict):
        self._logger.info("Enter get_pass_regression_test_patch_subgraph_node")
        self._logger.debug(f"selected_regression_tests: {state['selected_regression_tests']}")

        try:
            output_state = self.subgraph.invoke(
                selected_regression_tests=state["selected_regression_tests"],
                patches=state[self.testing_patch_key]
                if self.is_testing_patch_list
                else [state[self.testing_patch_key]],
            )
        except GraphRecursionError:
            # If the recursion limit is reached, return a failure result for each patch
            self._logger.info("Recursion limit reached")
            return {
                "tested_patch_result": [
                    TestedPatchResult(
                        patch=patch,
                        passed=False,
                        regression_test_failure_log="Fail to get regression test result. Please try again!",
                    )
                    for patch in state[self.testing_patch_key]
                ]
            }
        finally:
            # Reset the git repository to its original state
            self.git_repo.reset_repository()

        self._logger.debug(f"tested_patch_result: {output_state['tested_patch_result']}")

        return {
            "tested_patch_result": output_state["tested_patch_result"],
        }
