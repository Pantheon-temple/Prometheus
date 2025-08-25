import logging
import threading

import neo4j
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.errors import GraphRecursionError

from prometheus.git.git_repository import GitRepository
from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.lang_graph.graphs.issue_state import IssueState
from prometheus.lang_graph.subgraphs.issue_question_subgraph import IssueQuestionSubgraph


class IssueQuestionSubgraphNode:
    """
    A LangGraph node that handles the issue question subgraph, which is responsible for answering question in a GitHub issue.
    """

    def __init__(
        self,
        advanced_model: BaseChatModel,
        base_model: BaseChatModel,
        kg: KnowledgeGraph,
        git_repo: GitRepository,
        neo4j_driver: neo4j.Driver,
        max_token_per_neo4j_result: int,
    ):
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.issue_question_subgraph_node"
        )
        self.issue_question_subgraph = IssueQuestionSubgraph(
            advanced_model=advanced_model,
            base_model=base_model,
            kg=kg,
            git_repo=git_repo,
            neo4j_driver=neo4j_driver,
            max_token_per_neo4j_result=max_token_per_neo4j_result,
        )

    def __call__(self, state: IssueState):
        # Logging entry into the node
        self._logger.info("Enter IssueQuestionSubgraphNode")

        try:
            output_state = self.issue_question_subgraph.invoke(
                issue_title=state["issue_title"],
                issue_body=state["issue_body"],
                issue_comments=state["issue_comments"],
            )
        except GraphRecursionError:
            # Handle recursion error gracefully
            self._logger.critical("Please increase the recursion limit of IssueQuestionSubgraph")
            return {
                "edit_patch": None,
                "passed_reproducing_test": False,
                "passed_build": False,
                "passed_regression_test": False,
                "passed_existing_test": False,
                "issue_response": None,
            }

        # Logging the issue response for debugging
        self._logger.info(f"issue_response:\n{output_state['issue_response']}")
        return {
            "edit_patch": output_state["edit_patch"],
            "passed_reproducing_test": output_state["passed_reproducing_test"],
            "passed_build": output_state["passed_build"],
            "passed_regression_test": output_state["passed_regression_test"],
            "passed_existing_test": output_state["passed_existing_test"],
            "issue_response": output_state["issue_response"],
        }
