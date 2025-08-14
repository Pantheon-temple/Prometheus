
import neo4j
from langchain_core.language_models.chat_models import BaseChatModel

from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.lang_graph.graphs.issue_state import IssueState
from prometheus.lang_graph.subgraphs.issue_classification_subgraph import (
    IssueClassificationSubgraph,
)
from prometheus.utils.logger_manager import get_logger


class IssueClassificationSubgraphNode:
    def __init__(
        self,
        model: BaseChatModel,
        kg: KnowledgeGraph,
        neo4j_driver: neo4j.Driver,
        max_token_per_neo4j_result: int,
    ):
        self._logger = get_logger(__name__)
        self.issue_classification_subgraph = IssueClassificationSubgraph(
            model=model,
            kg=kg,
            neo4j_driver=neo4j_driver,
            max_token_per_neo4j_result=max_token_per_neo4j_result,
        )

    def __call__(self, state: IssueState):
        self._logger.info("Enter IssueClassificationSubgraphNode")
        issue_type = self.issue_classification_subgraph.invoke(
            state["issue_title"], state["issue_body"], state["issue_comments"]
        )
        self._logger.info(f"issue_type: {issue_type}")
        return {"issue_type": issue_type}
