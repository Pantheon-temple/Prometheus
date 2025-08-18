import logging
import threading
from typing import Optional, Sequence

import neo4j
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.errors import GraphRecursionError

from prometheus.docker.base_container import BaseContainer
from prometheus.git.git_repository import GitRepository
from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.lang_graph.subgraphs.issue_bug_state import IssueBugState
from prometheus.lang_graph.subgraphs.issue_verified_bug_subgraph import IssueVerifiedBugSubgraph


class IssueVerifiedBugSubgraphNode:
    """
    A LangGraph node that handles the verified issue bug, which is responsible for solving bugs.
    """

    def __init__(
        self,
        advanced_model: BaseChatModel,
        base_model: BaseChatModel,
        container: BaseContainer,
        kg: KnowledgeGraph,
        git_repo: GitRepository,
        neo4j_driver: neo4j.Driver,
        max_token_per_neo4j_result: int,
        build_commands: Optional[Sequence[str]] = None,
        test_commands: Optional[Sequence[str]] = None,
    ):
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.issue_verified_bug_subgraph_node"
        )
        self.git_repo = git_repo
        self.issue_reproduced_bug_subgraph = IssueVerifiedBugSubgraph(
            advanced_model=advanced_model,
            base_model=base_model,
            container=container,
            kg=kg,
            git_repo=git_repo,
            neo4j_driver=neo4j_driver,
            max_token_per_neo4j_result=max_token_per_neo4j_result,
            build_commands=build_commands,
            test_commands=test_commands,
        )

    def __call__(self, state: IssueBugState):
        self._logger.info("Enter IssueVerifiedBugSubgraphNode")
        try:
            output_state = self.issue_reproduced_bug_subgraph.invoke(
                issue_title=state["issue_title"],
                issue_body=state["issue_body"],
                issue_comments=state["issue_comments"],
                run_build=state["run_build"],
                run_regression_test=state["run_regression_test"],
                run_existing_test=state["run_existing_test"],
                reproduced_bug_file=state["reproduced_bug_file"],
                reproduced_bug_commands=state["reproduced_bug_commands"],
                reproduced_bug_patch=state["reproduced_bug_patch"],
                selected_regression_tests=state["selected_regression_tests"],
            )
        except GraphRecursionError:
            self._logger.info("Recursion limit reached")
            self.git_repo.reset_repository()
            return {
                "edit_patch": None,
                "passed_reproducing_test": False,
                "passed_build": False,
                "passed_existing_test": False,
            }
        # if all the tests passed
        passed_reproducing_test = not bool(output_state["reproducing_test_fail_log"])
        # if the build passed
        passed_build = state["run_build"] and not output_state["build_fail_log"]
        # if the existing tests passed
        passed_existing_test = (
            state["run_existing_test"] and not output_state["existing_test_fail_log"]
        )
        self._logger.info(f"edit_patch: {output_state['edit_patch']}")
        self._logger.info(f"passed_reproducing_test: {passed_reproducing_test}")
        self._logger.info(f"passed_build: {passed_build}")
        self._logger.info(f"passed_existing_test: {passed_existing_test}")
        return {
            "edit_patch": output_state["edit_patch"],
            "passed_reproducing_test": passed_reproducing_test,
            "passed_build": passed_build,
            "passed_existing_test": passed_existing_test,
        }
