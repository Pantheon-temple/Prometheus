from typing import Optional, Sequence

import neo4j
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.errors import GraphRecursionError

from prometheus.docker.base_container import BaseContainer
from prometheus.git.git_repository import GitRepository
from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.lang_graph.graphs.issue_state import IssueState
from prometheus.lang_graph.subgraphs.issue_bug_subgraph import IssueBugSubgraph
from prometheus.utils.logger_manager import get_logger


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
        self._logger = get_logger(__name__)
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
                number_of_candidate_patch=state["number_of_candidate_patch"],
            )

            self._logger.info(f"Generated patch:\n{output_state['edit_patch']}")
            self._logger.info(f"passed_reproducing_test: {output_state['passed_reproducing_test']}")
            self._logger.info(f"passed_build: {output_state['passed_build']}")
            self._logger.info(f"passed_existing_test: {output_state['passed_existing_test']}")
            self._logger.info(f"issue_response:\n{output_state['issue_response']}")
            return {
                "edit_patch": output_state["edit_patch"],
                "passed_reproducing_test": output_state["passed_reproducing_test"],
                "passed_build": output_state["passed_build"],
                "passed_existing_test": output_state["passed_existing_test"],
                "issue_response": output_state["issue_response"],
            }
        except GraphRecursionError:
            self._logger.critical("Please increase the recursion limit of IssueBugSubgraph")
            return {
                "edit_patch": None,
                "passed_reproducing_test": False,
                "passed_build": False,
                "passed_existing_test": False,
                "issue_response": None,
            }
        finally:
            self.container.cleanup()
