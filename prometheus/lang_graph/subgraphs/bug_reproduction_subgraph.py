import functools
from typing import Mapping, Optional, Sequence

import neo4j
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.errors import GraphRecursionError
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
        self.git_repo = git_repo

        issue_bug_reproduction_context_message_node = IssueBugReproductionContextMessageNode()
        context_retrieval_subgraph_node = ContextRetrievalSubgraphNode(
            base_model,
            kg,
            neo4j_driver,
            max_token_per_neo4j_result,
            "bug_reproducing_query",
            "bug_reproducing_context",
        )

        bug_reproducing_write_message_node = BugReproducingWriteMessageNode()
        bug_reproducing_write_node = BugReproducingWriteNode(advanced_model, kg)
        bug_reproducing_write_tools = ToolNode(
            tools=bug_reproducing_write_node.tools,
            name="bug_reproducing_write_tools",
            messages_key="bug_reproducing_write_messages",
        )
        bug_reproducing_file_node = BugReproducingFileNode(base_model, kg)
        bug_reproducing_file_tools = ToolNode(
            tools=bug_reproducing_file_node.tools,
            name="bug_reproducing_file_tools",
            messages_key="bug_reproducing_file_messages",
        )
        git_diff_node = GitDiffNode(git_repo, "bug_reproducing_patch")
        update_container_node = UpdateContainerNode(container, git_repo)
        bug_reproducing_execute_node = BugReproducingExecuteNode(
            base_model, container, test_commands
        )
        bug_reproducing_execute_tools = ToolNode(
            tools=bug_reproducing_execute_node.tools,
            name="bug_reproducing_execute_tools",
            messages_key="bug_reproducing_execute_messages",
        )
        bug_reproducing_structured_node = BugReproducingStructuredNode(advanced_model)
        reset_bug_reproducing_file_messages_node = ResetMessagesNode(
            "bug_reproducing_file_messages"
        )
        reset_bug_reproducing_execute_messages_node = ResetMessagesNode(
            "bug_reproducing_execute_messages"
        )
        git_reset_node = GitResetNode(git_repo)

        workflow = StateGraph(BugReproductionState)

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

        workflow.set_entry_point("issue_bug_reproduction_context_message_node")
        workflow.add_edge(
            "issue_bug_reproduction_context_message_node", "context_retrieval_subgraph_node"
        )
        workflow.add_edge("context_retrieval_subgraph_node", "bug_reproducing_write_message_node")

        workflow.add_edge("bug_reproducing_write_message_node", "bug_reproducing_write_node")
        workflow.add_conditional_edges(
            "bug_reproducing_write_node",
            functools.partial(tools_condition, messages_key="bug_reproducing_write_messages"),
            {
                "tools": "bug_reproducing_write_tools",
                END: "bug_reproducing_file_node",
            },
        )
        workflow.add_edge("bug_reproducing_write_tools", "bug_reproducing_write_node")
        workflow.add_conditional_edges(
            "bug_reproducing_file_node",
            functools.partial(tools_condition, messages_key="bug_reproducing_file_messages"),
            {
                "tools": "bug_reproducing_file_tools",
                END: "git_diff_node",
            },
        )
        workflow.add_edge("bug_reproducing_file_tools", "bug_reproducing_file_node")
        workflow.add_edge("git_diff_node", "update_container_node")
        workflow.add_edge("update_container_node", "bug_reproducing_execute_node")
        workflow.add_conditional_edges(
            "bug_reproducing_execute_node",
            functools.partial(tools_condition, messages_key="bug_reproducing_execute_messages"),
            {
                "tools": "bug_reproducing_execute_tools",
                END: "bug_reproducing_structured_node",
            },
        )
        workflow.add_edge("bug_reproducing_execute_tools", "bug_reproducing_execute_node")
        workflow.add_conditional_edges(
            "bug_reproducing_structured_node",
            lambda state: state["reproduced_bug"],
            {True: END, False: "reset_bug_reproducing_file_messages_node"},
        )

        workflow.add_edge(
            "reset_bug_reproducing_file_messages_node",
            "reset_bug_reproducing_execute_messages_node",
        )
        workflow.add_edge(
            "reset_bug_reproducing_execute_messages_node",
            "git_reset_node",
        )
        workflow.add_edge(
            "git_reset_node",
            "bug_reproducing_write_message_node",
        )

        self.subgraph = workflow.compile()

    def invoke(
        self,
        issue_title: str,
        issue_body: str,
        issue_comments: Sequence[Mapping[str, str]],
        recursion_limit: int = 50,
    ):
        config = {"recursion_limit": recursion_limit}

        input_state = {
            "issue_title": issue_title,
            "issue_body": issue_body,
            "issue_comments": issue_comments,
            "max_refined_query_loop": 3,
        }

        try:
            output_state = self.subgraph.invoke(input_state, config)
            return {
                "reproduced_bug": output_state["reproduced_bug"],
                "reproduced_bug_file": output_state["reproduced_bug_file"],
                "reproduced_bug_commands": output_state["reproduced_bug_commands"],
            }
        except GraphRecursionError:
            self.git_repo.reset_repository()
            return {
                "reproduced_bug": False,
                "reproduced_bug_file": "",
                "reproduced_bug_commands": "",
            }
