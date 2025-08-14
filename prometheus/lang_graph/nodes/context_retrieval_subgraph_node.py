from typing import Dict, Sequence

import neo4j
from langchain_core.language_models.chat_models import BaseChatModel

from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.lang_graph.subgraphs.context_retrieval_subgraph import ContextRetrievalSubgraph
from prometheus.models.context import Context
from prometheus.utils.logger_manager import get_logger


class ContextRetrievalSubgraphNode:
    def __init__(
        self,
        model: BaseChatModel,
        kg: KnowledgeGraph,
        neo4j_driver: neo4j.Driver,
        max_token_per_neo4j_result: int,
        query_key_name: str,
        context_key_name: str,
    ):
        self._logger = get_logger(__name__)
        self.context_retrieval_subgraph = ContextRetrievalSubgraph(
            model=model,
            kg=kg,
            neo4j_driver=neo4j_driver,
            max_token_per_neo4j_result=max_token_per_neo4j_result,
        )
        self.query_key_name = query_key_name
        self.context_key_name = context_key_name

    def __call__(self, state: Dict) -> Dict[str, Sequence[Context]]:
        self._logger.info("Enter context retrieval subgraph")
        output_state = self.context_retrieval_subgraph.invoke(
            state[self.query_key_name], state["max_refined_query_loop"]
        )
        self._logger.info(f"Context retrieved: {output_state['context']}")
        return {self.context_key_name: output_state["context"]}
