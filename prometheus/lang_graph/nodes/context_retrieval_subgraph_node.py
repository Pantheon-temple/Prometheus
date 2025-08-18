import logging
import threading
from typing import Dict, Sequence

import neo4j
from langchain_core.language_models.chat_models import BaseChatModel

from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.lang_graph.subgraphs.context_retrieval_subgraph import ContextRetrievalSubgraph
from prometheus.models.context import Context


class ContextRetrievalSubgraphNode:
    def __init__(
        self,
        model: BaseChatModel,
        kg: KnowledgeGraph,
        local_path: str,
        neo4j_driver: neo4j.Driver,
        max_token_per_neo4j_result: int,
        query_key_name: str,
        context_key_name: str,
    ):
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.context_retrieval_subgraph_node"
        )
        self.context_retrieval_subgraph = ContextRetrievalSubgraph(
            model=model,
            kg=kg,
            local_path=local_path,
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
