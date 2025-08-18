import functools
from typing import Dict, Sequence

import neo4j
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.lang_graph.nodes.context_extraction_node import ContextExtractionNode
from prometheus.lang_graph.nodes.context_provider_node import ContextProviderNode
from prometheus.lang_graph.nodes.context_query_message_node import ContextQueryMessageNode
from prometheus.lang_graph.nodes.context_refine_node import ContextRefineNode
from prometheus.lang_graph.nodes.reset_messages_node import ResetMessagesNode
from prometheus.lang_graph.subgraphs.context_retrieval_state import ContextRetrievalState
from prometheus.models.context import Context


class ContextRetrievalSubgraph:
    """
    A LangGraph-based subgraph for retrieving relevant contextual information
    (e.g., code, documentation, definitions) from a knowledge graph based on a query.

    This subgraph performs an iterative retrieval process:
    1. Constructs a context query message from the user prompt
    2. Uses tool-based retrieval (Neo4j-backed) to gather candidate context snippets
    3. Selects relevant context with LLM assistance
    4. Optionally refines the query and retries if necessary
    5. Outputs the final selected context

    Nodes:
        - ContextQueryMessageNode: Converts user query to internal query prompt
        - ContextProviderNode: Queries knowledge graph using structured tools
        - ToolNode: Dynamically invokes retrieval tools based on tool condition
        - ContextSelectionNode: Uses LLM to select useful context snippets
        - ResetMessagesNode: Clears previous context messages
        - ContextRefineNode: Decides whether to refine the query and retry
    """

    def __init__(
        self,
        model: BaseChatModel,
        kg: KnowledgeGraph,
        local_path: str,
        neo4j_driver: neo4j.Driver,
        max_token_per_neo4j_result: int,
    ):
        """
        Initializes the context retrieval subgraph.

        Args:
            model (BaseChatModel): The LLM used for context selection and refinement.
            local_path (str): Local path to the codebase for context extraction.
            neo4j_driver (neo4j.Driver): Driver for executing Cypher queries in Neo4j.
            max_token_per_neo4j_result (int): Token limit for responses from graph tools.
        """
        # Step 1: Generate an initial query from the user's input
        context_query_message_node = ContextQueryMessageNode()

        # Step 2: Provide candidate context snippets using knowledge graph tools
        context_provider_node = ContextProviderNode(
            model, kg, neo4j_driver, max_token_per_neo4j_result
        )

        # Step 3: Add tool node to handle tool-based retrieval invocation dynamically
        # The tool message will be added to the end of the context provider messages
        context_provider_tools = ToolNode(
            tools=context_provider_node.tools,
            name="context_provider_tools",
            messages_key="context_provider_messages",
        )

        # Step 4: Extract the Context
        context_extraction_node = ContextExtractionNode(model, local_path)

        # Step 5: Reset tool messages to prepare for the next iteration (if needed)
        reset_context_provider_messages_node = ResetMessagesNode("context_provider_messages")

        # Step 6: Refine the query if needed and loop back
        context_refine_node = ContextRefineNode(model, kg)

        # Construct the LangGraph workflow
        workflow = StateGraph(ContextRetrievalState)

        # Add all nodes to the graph
        workflow.add_node("context_query_message_node", context_query_message_node)
        workflow.add_node("context_provider_node", context_provider_node)
        workflow.add_node("context_provider_tools", context_provider_tools)
        workflow.add_node("context_extraction_node", context_extraction_node)
        workflow.add_node(
            "reset_context_provider_messages_node", reset_context_provider_messages_node
        )
        workflow.add_node("context_refine_node", context_refine_node)

        # Set the entry point for the workflow
        workflow.set_entry_point("context_query_message_node")
        # Define edges between nodes
        workflow.add_edge("context_query_message_node", "context_provider_node")

        # Conditional: Use tool node if tools_condition is satisfied
        workflow.add_conditional_edges(
            "context_provider_node",
            functools.partial(tools_condition, messages_key="context_provider_messages"),
            {"tools": "context_provider_tools", END: "context_extraction_node"},
        )
        workflow.add_edge("context_provider_tools", "context_provider_node")
        workflow.add_edge("context_extraction_node", "reset_context_provider_messages_node")
        workflow.add_edge("reset_context_provider_messages_node", "context_refine_node")

        # If refined_query is non-empty, loop back to provider; else terminate
        workflow.add_conditional_edges(
            "context_refine_node",
            lambda state: bool(state["refined_query"]),
            {True: "context_provider_node", False: END},
        )

        # Compile and store the subgraph
        self.subgraph = workflow.compile()

    def invoke(self, query: str, max_refined_query_loop: int) -> Dict[str, Sequence[Context]]:
        """
        Executes the context retrieval subgraph given an initial query.

        Args:
            query (str): The natural language query representing the information need.
            max_refined_query_loop (int): Maximum number of times the system can refine and retry the query.

        Returns:
            Dict with a single key:
                - "context" (Sequence[Context]): A list of selected context snippets relevant to the query.
        """
        # Set the recursion limit based on the maximum number of refined query loops
        config = {"recursion_limit": max_refined_query_loop * 40}

        input_state = {
            "query": query,
            "max_refined_query_loop": max_refined_query_loop,
        }

        output_state = self.subgraph.invoke(input_state, config)

        return {"context": output_state["context"]}
