import logging
import threading

import neo4j
from langchain_core.language_models.chat_models import BaseChatModel

from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.lang_graph.graphs.issue_state import IssueState
from prometheus.lang_graph.subgraphs.issue_classification_subgraph import (
    IssueClassificationSubgraph,
)


class IssueClassificationSubgraphNode:
    def __init__(
        self,
        model: BaseChatModel,
        kg: KnowledgeGraph,
        local_path: str,
        neo4j_driver: neo4j.Driver,
        max_token_per_neo4j_result: int,
    ):
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.issue_classification_subgraph_node"
        )
        self.issue_classification_subgraph = IssueClassificationSubgraph(
            model=model,
            kg=kg,
            local_path=local_path,
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
