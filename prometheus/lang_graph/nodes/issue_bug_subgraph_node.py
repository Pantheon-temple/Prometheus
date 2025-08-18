import logging
import threading
from typing import Optional, Sequence

import neo4j
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.errors import GraphRecursionError

from prometheus.docker.base_container import BaseContainer
from prometheus.git.git_repository import GitRepository
from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.lang_graph.graphs.issue_state import IssueState
from prometheus.lang_graph.subgraphs.issue_bug_subgraph import IssueBugSubgraph


class IssueBugSubgraphNode:
    """
    A LangGraph node that handles the issue bug subgraph, which is responsible for solving bugs in a GitHub issue.
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
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.issue_bug_subgraph_node"
        )
        self.container = container
        self.issue_bug_subgraph = IssueBugSubgraph(
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

    def __call__(self, state: IssueState):
        # Ensure the container is built and started
        self.container.build_docker_image()
        self.container.start_container()

        self._logger.info("Enter IssueBugSubgraphNode")

        try:
            output_state = self.issue_bug_subgraph.invoke(
                issue_title=state["issue_title"],
                issue_body=state["issue_body"],
                issue_comments=state["issue_comments"],
                run_build=state["run_build"],
                run_existing_test=state["run_existing_test"],
                run_regression_test=state["run_regression_test"],
                run_reproduce_test=state["run_reproduce_test"],
                number_of_candidate_patch=state["number_of_candidate_patch"],
            )

            self._logger.info(f"Generated patch:\n{output_state['edit_patch']}")
            self._logger.info(f"passed_reproducing_test: {output_state['passed_reproducing_test']}")
            self._logger.info(f"passed_build: {output_state['passed_build']}")
            self._logger.info(f"passed_regression_test: {output_state['passed_regression_test']}")
            self._logger.info(f"passed_existing_test: {output_state['passed_existing_test']}")
            self._logger.info(f"issue_response:\n{output_state['issue_response']}")
            return {
                "edit_patch": output_state["edit_patch"],
                "passed_reproducing_test": output_state["passed_reproducing_test"],
                "passed_build": output_state["passed_build"],
                "passed_regression_test": output_state["passed_regression_test"],
                "passed_existing_test": output_state["passed_existing_test"],
                "issue_response": output_state["issue_response"],
            }
        except GraphRecursionError:
            self._logger.critical("Please increase the recursion limit of IssueBugSubgraph")
            return {
                "edit_patch": None,
                "passed_reproducing_test": False,
                "passed_build": False,
                "passed_regression_test": False,
                "passed_existing_test": False,
                "issue_response": None,
            }
        finally:
            self.container.cleanup()
