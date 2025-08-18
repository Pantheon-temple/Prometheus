import functools
from typing import Mapping, Optional, Sequence

import neo4j
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from prometheus.docker.base_container import BaseContainer
from prometheus.git.git_repository import GitRepository
from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.lang_graph.nodes.bug_reproducing_execute_node import BugReproducingExecuteNode
from prometheus.lang_graph.nodes.bug_reproducing_file_node import BugReproducingFileNode
from prometheus.lang_graph.nodes.bug_reproducing_structured_node import BugReproducingStructuredNode
from prometheus.lang_graph.nodes.bug_reproducing_write_message_node import (
    BugReproducingWriteMessageNode,
)
from prometheus.lang_graph.nodes.bug_reproducing_write_node import BugReproducingWriteNode
from prometheus.lang_graph.nodes.context_retrieval_subgraph_node import ContextRetrievalSubgraphNode
from prometheus.lang_graph.nodes.git_diff_node import GitDiffNode
from prometheus.lang_graph.nodes.git_reset_node import GitResetNode
from prometheus.lang_graph.nodes.issue_bug_reproduction_context_message_node import (
    IssueBugReproductionContextMessageNode,
)
from prometheus.lang_graph.nodes.reset_messages_node import ResetMessagesNode
from prometheus.lang_graph.nodes.update_container_node import UpdateContainerNode
from prometheus.lang_graph.subgraphs.bug_reproduction_state import BugReproductionState


class BugReproductionSubgraph:
    """
    This class defines a LangGraph-based state machine that performs automatic bug reproduction
    for GitHub issues. It orchestrates context retrieval, patch writing, file editing,
    container execution, and feedback-based retry loops to reproduce bugs in codebases.
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
        test_commands: Optional[Sequence[str]] = None,
    ):
        """
        Initialize the bug reproduction pipeline with all necessary parts.

        Args:
            advanced_model: More powerful LLM for structured reasoning and synthesis.
            base_model: Lighter LLM for simpler tasks (e.g., file selection).
            container: Docker-based sandbox for running code.
            kg: Codebase knowledge graph used for context retrieval.
            git_repo: Git repository interface for codebase manipulation.
            neo4j_driver: Neo4j driver used for graph traversal.
            max_token_per_neo4j_result: Truncation budget per retrieved context chunk.
            test_commands: Optional list of test commands to verify reproduction success.
        """
        self.git_repo = git_repo

        # Step 1: Generate initial system messages based on issue data
        issue_bug_reproduction_context_message_node = IssueBugReproductionContextMessageNode()

        # Step 2: Retrieve relevant code/documentation context from the knowledge graph
        context_retrieval_subgraph_node = ContextRetrievalSubgraphNode(
            base_model,
            kg,
            git_repo.playground_path,
            neo4j_driver,
            max_token_per_neo4j_result,
            "bug_reproducing_query",
            "bug_reproducing_context",
        )

        # Step 3: Write a patch to reproduce the bug
        bug_reproducing_write_message_node = BugReproducingWriteMessageNode()
        bug_reproducing_write_node = BugReproducingWriteNode(
            advanced_model, git_repo.playground_path
        )
        bug_reproducing_write_tools = ToolNode(
            tools=bug_reproducing_write_node.tools,
            name="bug_reproducing_write_tools",
            messages_key="bug_reproducing_write_messages",
        )

        # Step 4: Edit files if necessary (based on tool calls)
        bug_reproducing_file_node = BugReproducingFileNode(base_model, kg, git_repo.playground_path)
        bug_reproducing_file_tools = ToolNode(
            tools=bug_reproducing_file_node.tools,
            name="bug_reproducing_file_tools",
            messages_key="bug_reproducing_file_messages",
        )

        # Step 5: Create a Git diff from modified files
        git_diff_node = GitDiffNode(git_repo, "bug_reproducing_patch")

        # Step 6: Update container with modified code
        update_container_node = UpdateContainerNode(container, git_repo)

        # Step 7: Run test commands to verify bug reproduction
        bug_reproducing_execute_node = BugReproducingExecuteNode(
            base_model, container, test_commands
        )
        bug_reproducing_execute_tools = ToolNode(
            tools=bug_reproducing_execute_node.tools,
            name="bug_reproducing_execute_tools",
            messages_key="bug_reproducing_execute_messages",
        )

        # Step 8: Decide whether the bug is reproduced or not
        bug_reproducing_structured_node = BugReproducingStructuredNode(advanced_model)

        # Step 9: Reset state if bug reproduction fails, for retry
        reset_bug_reproducing_file_messages_node = ResetMessagesNode(
            "bug_reproducing_file_messages"
        )
        reset_bug_reproducing_execute_messages_node = ResetMessagesNode(
            "bug_reproducing_execute_messages"
        )

        # Step 10: Git reset to revert changes
        git_reset_node = GitResetNode(git_repo)

        # Define the state machine
        workflow = StateGraph(BugReproductionState)

        # Add nodes to the state machine
        workflow.add_node(
            "issue_bug_reproduction_context_message_node",
            issue_bug_reproduction_context_message_node,
        )
        workflow.add_node("context_retrieval_subgraph_node", context_retrieval_subgraph_node)
        workflow.add_node("bug_reproducing_write_message_node", bug_reproducing_write_message_node)
        workflow.add_node("bug_reproducing_write_node", bug_reproducing_write_node)
        workflow.add_node("bug_reproducing_write_tools", bug_reproducing_write_tools)
        workflow.add_node("bug_reproducing_file_node", bug_reproducing_file_node)
        workflow.add_node("bug_reproducing_file_tools", bug_reproducing_file_tools)
        workflow.add_node("git_diff_node", git_diff_node)
        workflow.add_node("update_container_node", update_container_node)
        workflow.add_node("bug_reproducing_execute_node", bug_reproducing_execute_node)
        workflow.add_node("bug_reproducing_execute_tools", bug_reproducing_execute_tools)
        workflow.add_node("bug_reproducing_structured_node", bug_reproducing_structured_node)
        workflow.add_node(
            "reset_bug_reproducing_file_messages_node", reset_bug_reproducing_file_messages_node
        )
        workflow.add_node(
            "reset_bug_reproducing_execute_messages_node",
            reset_bug_reproducing_execute_messages_node,
        )
        workflow.add_node("git_reset_node", git_reset_node)

        # Define transitions between nodes
        workflow.set_entry_point("issue_bug_reproduction_context_message_node")
        workflow.add_edge(
            "issue_bug_reproduction_context_message_node", "context_retrieval_subgraph_node"
        )
        workflow.add_edge("context_retrieval_subgraph_node", "bug_reproducing_write_message_node")
        workflow.add_edge("bug_reproducing_write_message_node", "bug_reproducing_write_node")

        # Handle patch-writing tool usage or fallback
        workflow.add_conditional_edges(
            "bug_reproducing_write_node",
            functools.partial(tools_condition, messages_key="bug_reproducing_write_messages"),
            {
                "tools": "bug_reproducing_write_tools",
                END: "bug_reproducing_file_node",
            },
        )
        workflow.add_edge("bug_reproducing_write_tools", "bug_reproducing_write_node")

        # Handle file-editing tool usage or fallback
        workflow.add_conditional_edges(
            "bug_reproducing_file_node",
            functools.partial(tools_condition, messages_key="bug_reproducing_file_messages"),
            {
                "tools": "bug_reproducing_file_tools",
                END: "git_diff_node",
            },
        )
        workflow.add_edge("bug_reproducing_file_tools", "bug_reproducing_file_node")

        # Proceed to execution after code is updated
        workflow.add_conditional_edges(
            "git_diff_node",
            lambda state: bool(state["bug_reproducing_patch"]),
            {True: "update_container_node", False: "bug_reproducing_write_message_node"},
        )
        workflow.add_edge("update_container_node", "bug_reproducing_execute_node")

        # Handle command execution tool usage
        workflow.add_conditional_edges(
            "bug_reproducing_execute_node",
            functools.partial(tools_condition, messages_key="bug_reproducing_execute_messages"),
            {
                "tools": "bug_reproducing_execute_tools",
                END: "bug_reproducing_structured_node",
            },
        )
        workflow.add_edge("bug_reproducing_execute_tools", "bug_reproducing_execute_node")

        # Decide whether to stop or retry if bug not reproduced
        workflow.add_conditional_edges(
            "bug_reproducing_structured_node",
            lambda state: state["reproduced_bug"],
            {True: END, False: "reset_bug_reproducing_file_messages_node"},
        )

        # Retry loop: reset messages, revert repo, then go back to rewriting
        workflow.add_edge(
            "reset_bug_reproducing_file_messages_node",
            "reset_bug_reproducing_execute_messages_node",
        )
        workflow.add_edge("reset_bug_reproducing_execute_messages_node", "git_reset_node")
        workflow.add_edge("git_reset_node", "bug_reproducing_write_message_node")

        # Compile the full LangGraph subgraph
        self.subgraph = workflow.compile()

    def invoke(
        self,
        issue_title: str,
        issue_body: str,
        issue_comments: Sequence[Mapping[str, str]],
        recursion_limit: int = 150,
    ):
        """
        Run the bug reproduction subgraph.

        Args:
            issue_title: Title of the GitHub issue.
            issue_body: Main body text describing the bug.
            issue_comments: List of user/system comments for context.
            recursion_limit: Max steps before triggering recovery fallback.

        Returns:
            Dict with bug reproduction result, modified file (if any), and commands.
        """
        config = {"recursion_limit": recursion_limit}

        input_state = {
            "issue_title": issue_title,
            "issue_body": issue_body,
            "issue_comments": issue_comments,
            "max_refined_query_loop": 3,
        }

        output_state = self.subgraph.invoke(input_state, config)
        return {
            "reproduced_bug": output_state["reproduced_bug"],
            "reproduced_bug_file": output_state["reproduced_bug_file"],
            "reproduced_bug_commands": output_state["reproduced_bug_commands"],
            "reproduced_bug_patch": output_state["bug_reproducing_patch"],
        }
