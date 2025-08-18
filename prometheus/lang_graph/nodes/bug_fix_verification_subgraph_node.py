import logging
import threading

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.errors import GraphRecursionError

from prometheus.docker.base_container import BaseContainer
from prometheus.git.git_repository import GitRepository
from prometheus.lang_graph.subgraphs.bug_fix_verification_subgraph import BugFixVerificationSubgraph
from prometheus.lang_graph.subgraphs.issue_verified_bug_state import IssueVerifiedBugState


class BugFixVerificationSubgraphNode:
    def __init__(
        self,
        model: BaseChatModel,
        container: BaseContainer,
        git_repo: GitRepository,
    ):
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.bug_fix_verification_subgraph_node"
        )
        self.git_repo = git_repo
        self.subgraph = BugFixVerificationSubgraph(
            model=model,
            container=container,
            git_repo=self.git_repo,
        )

    def __call__(self, state: IssueVerifiedBugState):
        self._logger.info("Enter bug_fix_verification_subgraph_node")
        self._logger.debug(f"reproduced_bug_file: {state['reproduced_bug_file']}")
        self._logger.debug(f"reproduced_bug_commands: {state['reproduced_bug_commands']}")
        self._logger.debug(f"reproduced_bug_patch: {state['reproduced_bug_patch']}")
        self._logger.debug(f"edit_patch: {state['edit_patch']}")
        try:
            output_state = self.subgraph.invoke(
                reproduced_bug_file=state["reproduced_bug_file"],
                reproduced_bug_commands=state["reproduced_bug_commands"],
                reproduced_bug_patch=state["reproduced_bug_patch"],
                edit_patch=state["edit_patch"],
            )
        except GraphRecursionError:
            self._logger.info("Recursion limit reached, returning empty output state")
            return {
                "reproducing_test_fail_log": "Recursion limit reached during bug fix verification.",
            }
        finally:
            self.git_repo.reset_repository()

        self._logger.info(
            f"Passing bug reproducing test: {not bool(output_state['reproducing_test_fail_log'])}"
        )
        self._logger.debug(
            f"reproducing_test_fail_log: {output_state['reproducing_test_fail_log']}"
        )

        return {
            "reproducing_test_fail_log": output_state["reproducing_test_fail_log"],
        }
