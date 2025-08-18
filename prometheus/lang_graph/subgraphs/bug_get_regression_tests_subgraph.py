from typing import Mapping, Sequence

import neo4j
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.constants import END
from langgraph.graph import StateGraph

from prometheus.docker.base_container import BaseContainer
from prometheus.git.git_repository import GitRepository
from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.lang_graph.nodes.bug_get_regression_context_message_node import (
    BugGetRegressionContextMessageNode,
)
from prometheus.lang_graph.nodes.bug_get_regression_tests_selection_node import (
    BugGetRegressionTestsSelectionNode,
)
from prometheus.lang_graph.nodes.context_retrieval_subgraph_node import ContextRetrievalSubgraphNode
from prometheus.lang_graph.nodes.run_regression_tests_subgraph_node import (
    RunRegressionTestsSubgraphNode,
)
from prometheus.lang_graph.subgraphs.bug_get_regression_tests_state import (
    BugGetRegressionTestsState,
)


class BugGetRegressionTestsSubgraph:
    """
    This class defines a LangGraph-based state machine that automatically selects and runs regression tests
    for GitHub issues. It orchestrates context retrieval, tests selection, test execution, and feedback loops.
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
    ):
        """
        Initialize the run regression tests pipeline with all necessary parts.

        Args:
            advanced_model: More powerful LLM for structured reasoning and synthesis.
            base_model: Lighter LLM for simpler tasks (e.g., file selection).
            container: Docker-based sandbox for running code.
            kg: Codebase knowledge graph used for context retrieval.
            git_repo: Git repository interface for codebase manipulation.
            neo4j_driver: Neo4j driver used for graph traversal.
            max_token_per_neo4j_result: Truncation budget per retrieved context chunk.
        """

        # Step 1: Generate initial system messages based on issue data
        bug_get_regression_context_message_node = BugGetRegressionContextMessageNode()

        # Step 2: Retrieve relevant code/documentation context from the knowledge graph
        context_retrieval_subgraph_node = ContextRetrievalSubgraphNode(
            base_model,
            kg,
            git_repo.playground_path,
            neo4j_driver,
            max_token_per_neo4j_result,
            "select_regression_query",
            "select_regression_context",
        )
        # Step 3: Select relevant regression tests based on the issue and retrieved context
        bug_get_regression_tests_selection_node = BugGetRegressionTestsSelectionNode(
            model=advanced_model
        )
        # Step 4: Run the selected regression tests before the fix and store results
        run_regression_tests_subgraph_node = RunRegressionTestsSubgraphNode(
            model=base_model,
            container=container,
            passed_regression_tests_key="selected_regression_tests",
        )

        # Define the state machine
        workflow = StateGraph(BugGetRegressionTestsState)

        # Add nodes to the state machine
        workflow.add_node(
            "bug_get_regression_context_message_node",
            bug_get_regression_context_message_node,
        )
        workflow.add_node("context_retrieval_subgraph_node", context_retrieval_subgraph_node)
        workflow.add_node(
            "bug_get_regression_tests_selection_node", bug_get_regression_tests_selection_node
        )
        workflow.add_node("run_regression_tests_subgraph_node", run_regression_tests_subgraph_node)

        # Define transitions between nodes
        workflow.set_entry_point("bug_get_regression_context_message_node")
        workflow.add_edge(
            "bug_get_regression_context_message_node", "context_retrieval_subgraph_node"
        )
        workflow.add_edge(
            "context_retrieval_subgraph_node", "bug_get_regression_tests_selection_node"
        )
        workflow.add_edge(
            "bug_get_regression_tests_selection_node", "run_regression_tests_subgraph_node"
        )
        workflow.add_edge("run_regression_tests_subgraph_node", END)

        # Compile the full LangGraph subgraph
        self.subgraph = workflow.compile()

    def invoke(
        self,
        issue_title: str,
        issue_body: str,
        issue_comments: Sequence[Mapping[str, str]],
        number_of_selected_regression_tests: int = 5,
        recursion_limit: int = 150,
    ):
        """
        Run the bug regression subgraph.

        Args:
            issue_title: Title of the GitHub issue.
            issue_body: Main body text describing the bug.
            issue_comments: List of user/system comments for context.
            number_of_selected_regression_tests: Number of regression tests to select.
            recursion_limit: Max steps before triggering recovery fallback.
        Returns:
            The result of the bug regression process
        """
        config = {"recursion_limit": recursion_limit}

        input_state = {
            "issue_title": issue_title,
            "issue_body": issue_body,
            "issue_comments": issue_comments,
            "max_refined_query_loop": 3,
            "number_of_selected_regression_tests": number_of_selected_regression_tests,
        }

        output_state = self.subgraph.invoke(input_state, config)
        # return the regression failure log for debugging
        return {"regression_tests": output_state["selected_regression_tests"]}
