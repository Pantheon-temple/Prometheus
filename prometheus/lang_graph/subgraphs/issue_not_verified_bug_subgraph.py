import functools
from typing import Mapping, Sequence

import neo4j
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from prometheus.git.git_repository import GitRepository
from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.lang_graph.nodes.context_retrieval_subgraph_node import ContextRetrievalSubgraphNode
from prometheus.lang_graph.nodes.edit_message_node import EditMessageNode
from prometheus.lang_graph.nodes.edit_node import EditNode
from prometheus.lang_graph.nodes.final_patch_selection_node import FinalPatchSelectionNode
from prometheus.lang_graph.nodes.git_diff_node import GitDiffNode
from prometheus.lang_graph.nodes.git_reset_node import GitResetNode
from prometheus.lang_graph.nodes.issue_bug_analyzer_message_node import IssueBugAnalyzerMessageNode
from prometheus.lang_graph.nodes.issue_bug_analyzer_node import IssueBugAnalyzerNode
from prometheus.lang_graph.nodes.issue_bug_context_message_node import IssueBugContextMessageNode
from prometheus.lang_graph.nodes.reset_messages_node import ResetMessagesNode
from prometheus.lang_graph.subgraphs.issue_not_verified_bug_state import IssueNotVerifiedBugState


class IssueNotVerifiedBugSubgraph:
    """
    This class defines a LangGraph-based subgraph to address GitHub issues that are suspected bugs
    but have not yet been verified. It performs the following high-level steps:

    1. Retrieves context from the knowledge graph based on the issue description.
    2. Uses an LLM to analyze the issue and generate possible fix strategies.
    3. Applies edits iteratively to the codebase using tool-enabled LLM actions.
    4. Creates Git diffs and evaluates patches.
    5. Selects a final patch based on quality and completeness.
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
        # Step 1: Prepare the issue-related context
        issue_bug_context_message_node = IssueBugContextMessageNode()
        context_retrieval_subgraph_node = ContextRetrievalSubgraphNode(
            model=base_model,
            kg=kg,
            neo4j_driver=neo4j_driver,
            max_token_per_neo4j_result=max_token_per_neo4j_result,
            query_key_name="bug_fix_query",
            context_key_name="bug_fix_context",
        )

        # Step 2: Analyze the issue to identify potential bug-fix strategies
        issue_bug_analyzer_message_node = IssueBugAnalyzerMessageNode()
        issue_bug_analyzer_node = IssueBugAnalyzerNode(advanced_model)

        # Step 3: Generate and apply candidate patches
        edit_message_node = EditMessageNode()
        edit_node = EditNode(advanced_model, kg)
        edit_tools = ToolNode(
            tools=edit_node.tools,
            name="edit_tools",
            messages_key="edit_messages",
        )

        # Step 4: Generate Git diffs and evaluate patches
        git_diff_node = GitDiffNode(git_repo, "edit_patches", return_list=True)

        # Step 5: Reset git state and messages if the patch is insufficient
        git_reset_node = GitResetNode(git_repo)
        reset_issue_bug_analyzer_messages_node = ResetMessagesNode("issue_bug_analyzer_messages")
        reset_edit_messages_node = ResetMessagesNode("edit_messages")

        # Step 6: Select the final patch from candidates
        final_patch_selection_node = FinalPatchSelectionNode(advanced_model, "final_patch")

        # Construct the LangGraph workflow
        workflow = StateGraph(IssueNotVerifiedBugState)

        # Add nodes to the graph
        workflow.add_node("issue_bug_context_message_node", issue_bug_context_message_node)
        workflow.add_node("context_retrieval_subgraph_node", context_retrieval_subgraph_node)

        workflow.add_node("issue_bug_analyzer_message_node", issue_bug_analyzer_message_node)
        workflow.add_node("issue_bug_analyzer_node", issue_bug_analyzer_node)

        workflow.add_node("edit_message_node", edit_message_node)
        workflow.add_node("edit_node", edit_node)
        workflow.add_node("edit_tools", edit_tools)
        workflow.add_node("git_diff_node", git_diff_node)

        workflow.add_node("git_reset_node", git_reset_node)
        workflow.add_node(
            "reset_issue_bug_analyzer_messages_node", reset_issue_bug_analyzer_messages_node
        )
        workflow.add_node("reset_edit_messages_node", reset_edit_messages_node)

        workflow.add_node("final_patch_selection_node", final_patch_selection_node)

        # Define control flow between nodes
        workflow.set_entry_point("issue_bug_context_message_node")
        workflow.add_edge("issue_bug_context_message_node", "context_retrieval_subgraph_node")
        workflow.add_edge("context_retrieval_subgraph_node", "issue_bug_analyzer_message_node")
        workflow.add_edge("issue_bug_analyzer_message_node", "issue_bug_analyzer_node")
        workflow.add_edge("issue_bug_analyzer_node", "edit_message_node")

        workflow.add_edge("edit_message_node", "edit_node")

        # Conditional path: if tool usage is needed, go to ToolNode; else proceed to diff
        workflow.add_conditional_edges(
            "edit_node",
            functools.partial(tools_condition, messages_key="edit_messages"),
            {"tools": "edit_tools", END: "git_diff_node"},
        )
        workflow.add_edge("edit_tools", "edit_node")

        # If not enough patches generated yet, reset and continue the loop
        workflow.add_conditional_edges(
            "git_diff_node",
            lambda state: len(state["edit_patches"]) < state["number_of_candidate_patch"],
            {True: "git_reset_node", False: "final_patch_selection_node"},
        )

        # Reset loop for next candidate patch generation
        workflow.add_edge("git_reset_node", "reset_issue_bug_analyzer_messages_node")
        workflow.add_edge("reset_issue_bug_analyzer_messages_node", "reset_edit_messages_node")
        workflow.add_edge("reset_edit_messages_node", "issue_bug_analyzer_message_node")

        # Final termination
        workflow.add_edge("final_patch_selection_node", END)

        self.subgraph = workflow.compile()

    def invoke(
        self,
        issue_title: str,
        issue_body: str,
        issue_comments: Sequence[Mapping[str, str]],
        number_of_candidate_patch: int,
        recursion_limit: int = 999,
    ):
        """
        Run the bug-fix subgraph on a given GitHub issue.

        Args:
            issue_title: The title of the GitHub issue.
            issue_body: The body/description of the issue.
            issue_comments: A list of comments on the issue for additional context.
            number_of_candidate_patch: How many patch candidates to attempt before finalizing.
            recursion_limit: Max iterations to allow in the graph loop (safety mechanism).

        Returns:
            Dict with the selected 'final_patch'.
        """
        config = {"recursion_limit": recursion_limit}

        input_state = {
            "issue_title": issue_title,
            "issue_body": issue_body,
            "issue_comments": issue_comments,
            "number_of_candidate_patch": number_of_candidate_patch,
            "max_refined_query_loop": 3,
        }

        output_state = self.subgraph.invoke(input_state, config)
        return {
            "final_patch": output_state["final_patch"],
        }
