from typing import Optional, Sequence

import neo4j
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.errors import GraphRecursionError

from prometheus.docker.base_container import BaseContainer
from prometheus.git.git_repository import GitRepository
from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.lang_graph.subgraphs.bug_reproduction_subgraph import BugReproductionSubgraph
from prometheus.lang_graph.subgraphs.issue_bug_state import IssueBugState
from prometheus.utils.logger_manager import get_logger


class BugReproductionSubgraphNode:
    def __init__(
        self,
        advanced_model: BaseChatModel,
        base_model: BaseChatModel,
        container: BaseContainer,
        kg: KnowledgeGraph,
        git_repo: GitRepository,
        neo4j_driver: neo4j.Driver,
        max_token_per_neo4j_result: int,
        test_commands: Optional[Sequence[str]],
    ):
        self._logger = get_logger(__name__)
        self.git_repo = git_repo
        self.bug_reproduction_subgraph = BugReproductionSubgraph(
            advanced_model=advanced_model,
            base_model=base_model,
            container=container,
            kg=kg,
            git_repo=git_repo,
            neo4j_driver=neo4j_driver,
            max_token_per_neo4j_result=max_token_per_neo4j_result,
            test_commands=test_commands,
        )

    def __call__(self, state: IssueBugState):
        self._logger.info("Enter bug_reproduction_subgraph")

        try:
            output_state = self.bug_reproduction_subgraph.invoke(
                state["issue_title"],
                state["issue_body"],
                state["issue_comments"],
            )
        except GraphRecursionError:
            self._logger.info("Recursion limit reached, returning reproduced_bug=False")
            self.git_repo.reset_repository()
            return {"reproduced_bug": False}

        self._logger.info(f"reproduced_bug: {output_state['reproduced_bug']}")
        self._logger.info(f"reproduced_bug_file: {output_state['reproduced_bug_file']}")
        self._logger.info(f"reproduced_bug_commands: {output_state['reproduced_bug_commands']}")
        return {
            "reproduced_bug": output_state["reproduced_bug"],
            "reproduced_bug_file": output_state["reproduced_bug_file"],
            "reproduced_bug_commands": output_state["reproduced_bug_commands"],
        }
