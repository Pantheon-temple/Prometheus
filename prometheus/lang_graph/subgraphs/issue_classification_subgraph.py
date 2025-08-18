from typing import Mapping, Sequence

import neo4j
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, StateGraph

from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.lang_graph.nodes.context_retrieval_subgraph_node import ContextRetrievalSubgraphNode
from prometheus.lang_graph.nodes.issue_classification_context_message_node import (
    IssueClassificationContextMessageNode,
)
from prometheus.lang_graph.nodes.issue_classifier_node import IssueClassifierNode
from prometheus.lang_graph.subgraphs.issue_classification_state import IssueClassificationState


class IssueClassificationSubgraph:
    def __init__(
        self,
        model: BaseChatModel,
        kg: KnowledgeGraph,
        local_path: str,
        neo4j_driver: neo4j.Driver,
        max_token_per_neo4j_result: int,
    ):
        issue_classification_context_message_node = IssueClassificationContextMessageNode()
        context_retrieval_subgraph_node = ContextRetrievalSubgraphNode(
            model=model,
            kg=kg,
            local_path=local_path,
            neo4j_driver=neo4j_driver,
            max_token_per_neo4j_result=max_token_per_neo4j_result,
            query_key_name="issue_classification_query",
            context_key_name="issue_classification_context",
        )
        issue_classifier_node = IssueClassifierNode(model)

        workflow = StateGraph(IssueClassificationState)
        workflow.add_node(
            "issue_classification_context_message_node", issue_classification_context_message_node
        )
        workflow.add_node("context_retrieval_subgraph_node", context_retrieval_subgraph_node)
        workflow.add_node("issue_classifier_node", issue_classifier_node)

        workflow.set_entry_point("issue_classification_context_message_node")
        workflow.add_edge(
            "issue_classification_context_message_node", "context_retrieval_subgraph_node"
        )
        workflow.add_edge("context_retrieval_subgraph_node", "issue_classifier_node")
        workflow.add_edge("issue_classifier_node", END)

        self.subgraph = workflow.compile()

    def invoke(
        self,
        issue_title: str,
        issue_body: str,
        issue_comments: Sequence[Mapping[str, str]],
    ) -> str:
        config = None

        input_state = {
            "issue_title": issue_title,
            "issue_body": issue_body,
            "issue_comments": issue_comments,
            "max_refined_query_loop": 3,
        }

        output_state = self.subgraph.invoke(
            input_state,
            config,
        )
        return output_state["issue_type"]
