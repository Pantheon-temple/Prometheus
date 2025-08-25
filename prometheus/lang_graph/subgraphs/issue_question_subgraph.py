from typing import Mapping, Sequence

import neo4j
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.constants import END
from langgraph.graph import StateGraph

from prometheus.git.git_repository import GitRepository
from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.lang_graph.nodes.context_retrieval_subgraph_node import ContextRetrievalSubgraphNode
from prometheus.lang_graph.nodes.issue_question_analyzer_node import IssueQuestionAnalyzerNode
from prometheus.lang_graph.nodes.issue_question_context_message_node import (
    IssueQuestionContextMessageNode,
)
from prometheus.lang_graph.subgraphs.issue_question_state import IssueQuestionState


class IssueQuestionSubgraph:
    """
    A LangGraph-based subgraph to analyze and answer questions related to GitHub issues.
    This subgraph processes issue details, retrieves relevant context, and generates a comprehensive response.
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
        # Step 1: Retrieve relevant context based on the issue details
        issue_question_context_message_node = IssueQuestionContextMessageNode()
        context_retrieval_subgraph_node = ContextRetrievalSubgraphNode(
            model=base_model,
            kg=kg,
            local_path=git_repo.playground_path,
            neo4j_driver=neo4j_driver,
            max_token_per_neo4j_result=max_token_per_neo4j_result,
            query_key_name="question_query",
            context_key_name="question_context",
        )

        # Step 2: Analyze the issue and retrieved context to generate a response
        issue_question_analyzer_node = IssueQuestionAnalyzerNode(model=advanced_model)

        # Define the subgraph structure
        workflow = StateGraph(IssueQuestionState)
        workflow.add_node(
            "issue_question_context_message_node", issue_question_context_message_node
        )
        workflow.add_node("context_retrieval_subgraph_node", context_retrieval_subgraph_node)
        workflow.add_node("issue_question_analyzer_node", issue_question_analyzer_node)

        # Define the entry point
        workflow.set_entry_point("issue_question_context_message_node")

        # Define the workflow transitions
        workflow.add_edge("issue_question_context_message_node", "context_retrieval_subgraph_node")
        workflow.add_edge("context_retrieval_subgraph_node", "issue_question_analyzer_node")
        workflow.add_edge("issue_question_analyzer_node", END)

        # Compile the workflow into an executable subgraph
        self.subgraph = workflow.compile()

    def invoke(
        self,
        issue_title: str,
        issue_body: str,
        issue_comments: Sequence[Mapping[str, str]],
        recursion_limit: int = 30,
    ):
        config = {"recursion_limit": recursion_limit}

        input_state = {
            "issue_title": issue_title,
            "issue_body": issue_body,
            "issue_comments": issue_comments,
            "max_refined_query_loop": 3,
        }

        output_state = self.subgraph.invoke(input_state, config)
        return {
            "edit_patch": None,
            "passed_reproducing_test": False,
            "passed_build": False,
            "passed_existing_test": False,
            "passed_regression_test": False,
            "issue_response": output_state["question_response"],
        }
