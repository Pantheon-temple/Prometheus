import logging
import threading
from typing import Dict

import neo4j
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.errors import GraphRecursionError

from prometheus.docker.base_container import BaseContainer
from prometheus.git.git_repository import GitRepository
from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.lang_graph.subgraphs.issue_not_verified_bug_subgraph import (
    IssueNotVerifiedBugSubgraph,
)


class IssueNotVerifiedBugSubgraphNode:
    def __init__(
        self,
        advanced_model: BaseChatModel,
        base_model: BaseChatModel,
        kg: KnowledgeGraph,
        git_repo: GitRepository,
        container: BaseContainer,
        neo4j_driver: neo4j.Driver,
        max_token_per_neo4j_result: int,
    ):
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.issue_not_verified_bug_subgraph_node"
        )
        self.issue_not_verified_bug_subgraph = IssueNotVerifiedBugSubgraph(
            advanced_model=advanced_model,
            base_model=base_model,
            kg=kg,
            git_repo=git_repo,
            container=container,
            neo4j_driver=neo4j_driver,
            max_token_per_neo4j_result=max_token_per_neo4j_result,
        )
        self.git_repo = git_repo

    def __call__(self, state: Dict):
        self._logger.info("Enter IssueNotVerifiedBugSubgraphNode")

        try:
            output_state = self.issue_not_verified_bug_subgraph.invoke(
                issue_title=state["issue_title"],
                issue_body=state["issue_body"],
                issue_comments=state["issue_comments"],
                number_of_candidate_patch=state["number_of_candidate_patch"],
                run_regression_test=state["run_regression_test"],
                selected_regression_tests=state["selected_regression_tests"],
            )
        except GraphRecursionError:
            self._logger.debug("GraphRecursionError encountered, returning empty patch")
            self.git_repo.reset_repository()
            return {
                "edit_patch": None,
                "passed_reproducing_test": False,
                "passed_build": False,
                "passed_existing_test": False,
            }

        self._logger.info(f"final_patch:\n{output_state['final_patch']}")

        return {
            "edit_patch": output_state["final_patch"],
            "passed_reproducing_test": False,
            "passed_build": False,
            "passed_existing_test": False,
        }
