import functools
from typing import Mapping, Optional, Sequence

import neo4j
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from prometheus.docker.base_container import BaseContainer
from prometheus.git.git_repository import GitRepository
from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.lang_graph.nodes.bug_fix_verification_subgraph_node import (
    BugFixVerificationSubgraphNode,
)
from prometheus.lang_graph.nodes.build_and_test_subgraph_node import BuildAndTestSubgraphNode
from prometheus.lang_graph.nodes.context_retrieval_subgraph_node import ContextRetrievalSubgraphNode
from prometheus.lang_graph.nodes.edit_message_node import EditMessageNode
from prometheus.lang_graph.nodes.edit_node import EditNode
from prometheus.lang_graph.nodes.final_patch_selection_node import FinalPatchSelectionNode
from prometheus.lang_graph.nodes.git_diff_node import GitDiffNode
from prometheus.lang_graph.nodes.git_reset_node import GitResetNode
from prometheus.lang_graph.nodes.issue_bug_analyzer_message_node import IssueBugAnalyzerMessageNode
from prometheus.lang_graph.nodes.issue_bug_analyzer_node import IssueBugAnalyzerNode
from prometheus.lang_graph.nodes.issue_bug_context_message_node import IssueBugContextMessageNode
from prometheus.lang_graph.nodes.noop_node import NoopNode
from prometheus.lang_graph.nodes.reset_messages_node import ResetMessagesNode
from prometheus.lang_graph.nodes.update_container_node import UpdateContainerNode
from prometheus.lang_graph.subgraphs.issue_verified_bug_state import IssueVerifiedBugState


class IssueVerifiedBugSubgraph:
    """
    LangGraph subgraph for resolving verified bugs with iterative patch generation
    and final selection from multiple candidates.
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
        build_commands: Optional[Sequence[str]] = None,
        test_commands: Optional[Sequence[str]] = None,
        candidate_patch_number: int = 5,
    ):
        self.candidate_patch_number = candidate_patch_number

        # Step 1: Context setup
        issue_bug_context_message_node = IssueBugContextMessageNode()
        context_retrieval_subgraph_node = ContextRetrievalSubgraphNode(
            model=base_model,
            kg=kg,
            neo4j_driver=neo4j_driver,
            max_token_per_neo4j_result=max_token_per_neo4j_result,
            query_key_name="bug_fix_query",
            context_key_name="bug_fix_context",
        )

        # Step 2: Bug analysis
        issue_bug_analyzer_message_node = IssueBugAnalyzerMessageNode()
        issue_bug_analyzer_node = IssueBugAnalyzerNode(advanced_model)

        # Step 3: Patch generation
        edit_message_node = EditMessageNode()
        edit_node = EditNode(advanced_model, kg)
        edit_tools = ToolNode(
            tools=edit_node.tools,
            name="edit_tools",
            messages_key="edit_messages",
        )

        # Step 4: Git diff accumulation
        git_diff_node = GitDiffNode(
            git_repo, "edit_patches", "reproduced_bug_file", return_list=True
        )

        # Reset & loop control
        git_reset_node = GitResetNode(git_repo)
        reset_issue_bug_analyzer_messages_node = ResetMessagesNode("issue_bug_analyzer_messages")
        reset_edit_messages_node = ResetMessagesNode("edit_messages")

        # Step 5: Patch selection and update container
        patches_selection_node = FinalPatchSelectionNode(
            final_patch_name="edit_patch", model=advanced_model
        )
        update_container_node = UpdateContainerNode(container, git_repo)

        # Step 6: Bug test
        bug_fix_verification_subgraph_node = BugFixVerificationSubgraphNode(
            base_model, container
        )

        # Step 7: Optional full build/test
        build_or_test_branch_node = NoopNode()
        build_and_test_subgraph_node = BuildAndTestSubgraphNode(
            container, advanced_model, kg, build_commands, test_commands
        )

        # Build graph
        workflow = StateGraph(IssueVerifiedBugState)

        # Add nodes
        workflow.add_node("issue_bug_context_message_node", issue_bug_context_message_node)
        workflow.add_node("context_retrieval_subgraph_node", context_retrieval_subgraph_node)
        workflow.add_node("issue_bug_analyzer_message_node", issue_bug_analyzer_message_node)
        workflow.add_node("issue_bug_analyzer_node", issue_bug_analyzer_node)
        workflow.add_node("edit_message_node", edit_message_node)
        workflow.add_node("edit_node", edit_node)
        workflow.add_node("edit_tools", edit_tools)
        workflow.add_node("git_diff_node", git_diff_node)
        workflow.add_node("git_reset_node", git_reset_node)
        workflow.add_node("reset_issue_bug_analyzer_messages_node", reset_issue_bug_analyzer_messages_node)
        workflow.add_node("reset_edit_messages_node", reset_edit_messages_node)
        workflow.add_node("patches_selection_node", patches_selection_node)
        workflow.add_node("update_container_node", update_container_node)
        workflow.add_node("bug_fix_verification_subgraph_node", bug_fix_verification_subgraph_node)
        workflow.add_node("build_or_test_branch_node", build_or_test_branch_node)
        workflow.add_node("build_and_test_subgraph_node", build_and_test_subgraph_node)

        # Graph transitions
        workflow.set_entry_point("issue_bug_context_message_node")
        workflow.add_edge("issue_bug_context_message_node", "context_retrieval_subgraph_node")
        workflow.add_edge("context_retrieval_subgraph_node", "issue_bug_analyzer_message_node")
        workflow.add_edge("issue_bug_analyzer_message_node", "issue_bug_analyzer_node")
        workflow.add_edge("issue_bug_analyzer_node", "edit_message_node")
        workflow.add_edge("edit_message_node", "edit_node")

        workflow.add_conditional_edges(
            "edit_node",
            functools.partial(tools_condition, messages_key="edit_messages"),
            {"tools": "edit_tools", END: "git_diff_node"},
        )
        workflow.add_edge("edit_tools", "edit_node")

        # Loop if not enough patches
        workflow.add_conditional_edges(
            "git_diff_node",
            lambda state: len(state["edit_patches"]) < state["number_of_candidate_patch"],
            {True: "git_reset_node", False: "patches_selection_node"},
        )

        workflow.add_edge("git_reset_node", "reset_issue_bug_analyzer_messages_node")
        workflow.add_edge("reset_issue_bug_analyzer_messages_node", "reset_edit_messages_node")
        workflow.add_edge("reset_edit_messages_node", "issue_bug_analyzer_message_node")

        workflow.add_edge("patches_selection_node", "update_container_node")
        workflow.add_edge("update_container_node", "bug_fix_verification_subgraph_node")

        # If test still fails, loop back to reanalyze the bug
        workflow.add_conditional_edges(
            "bug_fix_verification_subgraph_node",
            lambda state: bool(state["reproducing_test_fail_log"]),
            {True: "issue_bug_analyzer_message_node", False: "build_or_test_branch_node"},
        )

        # Optionally run full build/test suite
        workflow.add_conditional_edges(
            "build_or_test_branch_node",
            lambda state: state["run_build"] or state["run_existing_test"],
            {True: "build_and_test_subgraph_node", False: END},
        )

        # If build/test fail, go back to reanalyze and patch
        workflow.add_conditional_edges(
            "build_and_test_subgraph_node",
            lambda state: bool(state["build_fail_log"]) or bool(state["existing_test_fail_log"]),
            {True: "issue_bug_analyzer_message_node", False: END},
        )

        # Compile and assign the subgraph
        self.subgraph = workflow.compile()

    def invoke(
        self,
        issue_title: str,
        issue_body: str,
        issue_comments: Sequence[Mapping[str, str]],
        run_build: bool,
        run_existing_test: bool,
        reproduced_bug_file: str,
        reproduced_bug_commands: Sequence[str],
        recursion_limit: int = 80,
    ):
        config = {"recursion_limit": recursion_limit}

        input_state = {
            "issue_title": issue_title,
            "issue_body": issue_body,
            "issue_comments": issue_comments,
            "run_build": run_build,
            "run_existing_test": run_existing_test,
            "reproduced_bug_file": reproduced_bug_file,
            "reproduced_bug_commands": reproduced_bug_commands,
            "number_of_candidate_patch": self.candidate_patch_number,
            "max_refined_query_loop": 3,
        }

        output_state = self.subgraph.invoke(input_state, config)
        return {
            "edit_patch": output_state["edit_patch"],
            "reproducing_test_fail_log": output_state["reproducing_test_fail_log"],
            "exist_build": output_state.get("exist_build", False),
            "build_fail_log": output_state.get("build_fail_log", ""),
            "exist_test": output_state.get("exist_test", False),
            "existing_test_fail_log": output_state.get("existing_test_fail_log", ""),
        }
