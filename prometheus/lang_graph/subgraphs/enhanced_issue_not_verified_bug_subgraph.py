"""Enhanced Issue Not Verified Bug Subgraph

This module integrates the agent parallel voting system, providing enhanced patch selection capabilities.
Includes complete workflow for patch normalization, test execution and majority voting.
"""

import functools
from typing import Mapping, Sequence, Optional

import neo4j
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from prometheus.git.git_repository import GitRepository
from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.docker.base_container import BaseContainer

# Original nodes
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
from prometheus.lang_graph.nodes.general_build_node import GeneralBuildNode
from prometheus.lang_graph.nodes.general_test_node import GeneralTestNode

# New voting-related nodes
from prometheus.lang_graph.nodes.patch_normalization_node import PatchNormalizationNode
from prometheus.lang_graph.nodes.agent_voting_node import AgentVotingNode

from prometheus.lang_graph.subgraphs.issue_not_verified_bug_state import IssueNotVerifiedBugState


class EnhancedIssueNotVerifiedBugSubgraph:
    """Enhanced Issue Not Verified Bug Subgraph
    
    Integrated complete workflow with agent parallel voting system:
    1. Original context retrieval and bug analysis
    2. Patch generation and diff
    3. Patch normalization and deduplication
    4. Patch test execution
    5. Agent parallel voting selection
    6. Fallback original selector
    """
    
    def __init__(
        self,
        advanced_model: BaseChatModel,
        base_model: BaseChatModel,
        kg: KnowledgeGraph,
        git_repo: GitRepository,
        neo4j_driver: neo4j.Driver,
        max_token_per_neo4j_result: int,
        container: Optional[BaseContainer] = None,
        enable_agent_voting: bool = True,
        enable_context_enhancement: bool = True,
        num_voting_agents: int = 5,
        early_stopping_threshold: float = 0.6
    ):
        """Initialize enhanced subgraph
        
        Args:
            advanced_model: Advanced language model (for complex reasoning)
            base_model: Base language model (for simple tasks)
            kg: Knowledge graph
            git_repo: Git repository instance
            neo4j_driver: Neo4j driver
            max_token_per_neo4j_result: Maximum tokens for Neo4j results
            container: Docker container (optional, for future use)
            enable_agent_voting: Whether to enable agent voting
            enable_context_enhancement: Whether to enable context enhancement
            num_voting_agents: Number of voting agents
            early_stopping_threshold: Early stopping threshold
        """
        
        # === Original Node Initialization ===
        issue_bug_context_message_node = IssueBugContextMessageNode()
        context_retrieval_subgraph_node = ContextRetrievalSubgraphNode(
            model=base_model,
            kg=kg,
            local_path=git_repo.playground_path,
            neo4j_driver=neo4j_driver,
            max_token_per_neo4j_result=max_token_per_neo4j_result,
            query_key_name="bug_fix_query",
            context_key_name="bug_fix_context",
        )

        issue_bug_analyzer_message_node = IssueBugAnalyzerMessageNode()
        issue_bug_analyzer_node = IssueBugAnalyzerNode(advanced_model)

        edit_message_node = EditMessageNode()
        edit_node = EditNode(advanced_model, git_repo.playground_path)
        edit_tools = ToolNode(
            tools=edit_node.tools,
            name="edit_tools",
            messages_key="edit_messages",
        )
        git_diff_node = GitDiffNode(git_repo, "edit_patches", return_list=True)

        git_reset_node = GitResetNode(git_repo)
        reset_issue_bug_analyzer_messages_node = ResetMessagesNode("issue_bug_analyzer_messages")
        reset_edit_messages_node = ResetMessagesNode("edit_messages")

        # Original patch selection node (as fallback)
        original_final_patch_selection_node = FinalPatchSelectionNode(advanced_model)
        
        # === New Voting-Related Nodes ===
        self.enable_agent_voting = enable_agent_voting
        self.enable_context_enhancement = enable_context_enhancement
        
        # Patch normalization node
        patch_normalization_node = PatchNormalizationNode()
        
        # Agent voting node
        agent_voting_node = None
        if enable_agent_voting:
            agent_voting_node = AgentVotingNode(
                model=advanced_model,
                num_voting_agents=num_voting_agents,
                early_stopping_threshold=early_stopping_threshold,
                enable_early_stopping=True
            )
        
        # === Build Workflow Graph ===
        workflow = StateGraph(IssueNotVerifiedBugState)
        
        # Add original nodes
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
        workflow.add_node("original_final_patch_selection_node", original_final_patch_selection_node)
        
        # Add new voting-related nodes
        workflow.add_node("patch_normalization_node", patch_normalization_node)
        if agent_voting_node:
            workflow.add_node("agent_voting_node", agent_voting_node)
        
        # === Build Workflow Edges ===
        
        # Original first half workflow remains unchanged
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

        # === Key Decision Point: Choose Voting Flow or Continue Generating Patches ===
        workflow.add_conditional_edges(
            "git_diff_node",
            self._routing_logic,
            {
                "continue_generation": "git_reset_node",  # Continue generating more patches
                "start_voting": "patch_normalization_node",  # Start voting flow
                "single_patch": "original_final_patch_selection_node"  # Single patch direct selection
            }
        )

        # Continue generating patches - original flow
        workflow.add_edge("git_reset_node", "reset_issue_bug_analyzer_messages_node")
        workflow.add_edge("reset_issue_bug_analyzer_messages_node", "reset_edit_messages_node")
        workflow.add_edge("reset_edit_messages_node", "issue_bug_analyzer_message_node")

        # === New Voting Flow ===
        # Flow: normalization -> voting
        if agent_voting_node:
            workflow.add_edge("patch_normalization_node", "agent_voting_node")
            workflow.add_edge("agent_voting_node", END)
        else:
            workflow.add_edge("patch_normalization_node", "original_final_patch_selection_node")

        # Original selector exit
        workflow.add_edge("original_final_patch_selection_node", END)

        self.subgraph = workflow.compile()
    
    def _routing_logic(self, state: IssueNotVerifiedBugState) -> str:
        """Routing logic: decide next workflow step
        
        Args:
            state: Current state
            
        Returns:
            str: Next node identifier
        """
        patches = state.get("edit_patches", [])
        target_patch_count = state.get("number_of_candidate_patch", 1)
        current_patch_count = len(patches)
        
        # 1. If haven't reached target patch count, continue generating
        if current_patch_count < target_patch_count:
            return "continue_generation"
        
        # 2. If only one patch or agent voting disabled, use original selector
        if current_patch_count <= 1 or not self.enable_agent_voting:
            return "single_patch"
        
        # 3. Multiple patches and voting enabled, start voting flow
        return "start_voting"
    
    def invoke(
        self,
        issue_title: str,
        issue_body: str,
        issue_comments: Sequence[Mapping[str, str]],
        number_of_candidate_patch: int,
        recursion_limit: int = 500,  # Increase recursion limit to support more complex workflow
    ):
        """Invoke enhanced subgraph
        
        Args:
            issue_title: Issue title
            issue_body: Issue description
            issue_comments: Issue comments
            number_of_candidate_patch: Number of candidate patches
            recursion_limit: Recursion limit
            
        Returns:
            Dictionary containing final patch and voting results
        """
        config = {"recursion_limit": recursion_limit}

        input_state = {
            "issue_title": issue_title,
            "issue_body": issue_body,
            "issue_comments": issue_comments,
            "number_of_candidate_patch": number_of_candidate_patch,
            "max_refined_query_loop": 5,
        }

        output_state = self.subgraph.invoke(input_state, config)
        
        # Build return result
        result = {
            "final_patch": output_state.get("final_patch", ""),
        }
        
        # If voting system was used, add voting-related information
        if "voting_result" in output_state and output_state["voting_result"]:
            voting_result = output_state["voting_result"]
            result.update({
                "voting_result": {
                    "selected_patch_index": voting_result.selected_patch_index,
                    "vote_distribution": voting_result.vote_distribution,
                    "consensus_strength": voting_result.get_consensus_strength(),
                    "average_confidence": voting_result.get_average_confidence(),
                    "total_voters": voting_result.total_voters,
                    "early_stopped": voting_result.early_stopped,
                    "consensus_metrics": voting_result.consensus_metrics
                }
            })
        
        # Add patch processing statistics
        if "unique_patch_count" in output_state:
            result["patch_statistics"] = {
                "original_patch_count": output_state.get("original_patch_count", 0),
                "unique_patch_count": output_state.get("unique_patch_count", 0),
                "deduplication_ratio": output_state.get("unique_patch_count", 0) / max(output_state.get("original_patch_count", 1), 1)
            }
        
        return result


# Backward compatibility alias
EnhancedIssueNotVerifiedBugSubgraph.__name__ = "EnhancedIssueNotVerifiedBugSubgraph"
