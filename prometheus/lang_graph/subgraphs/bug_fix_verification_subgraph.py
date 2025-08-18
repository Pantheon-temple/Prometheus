import functools
from typing import Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from prometheus.docker.base_container import BaseContainer
from prometheus.git.git_repository import GitRepository
from prometheus.lang_graph.nodes.bug_fix_verify_node import BugFixVerifyNode
from prometheus.lang_graph.nodes.bug_fix_verify_structured_node import BugFixVerifyStructuredNode
from prometheus.lang_graph.nodes.git_apply_patch_node import GitApplyPatchNode
from prometheus.lang_graph.nodes.update_container_node import UpdateContainerNode
from prometheus.lang_graph.subgraphs.bug_fix_verification_state import BugFixVerificationState


class BugFixVerificationSubgraph:
    def __init__(
        self,
        model: BaseChatModel,
        container: BaseContainer,
        git_repo: GitRepository,
    ):
        edit_patch_apply_node = GitApplyPatchNode(git_repo=git_repo, state_patch_name="edit_patch")
        reproduce_bug_patch_apply_node = GitApplyPatchNode(
            git_repo=git_repo, state_patch_name="reproduced_bug_patch"
        )
        update_container_node = UpdateContainerNode(container=container, git_repo=git_repo)

        bug_fix_verify_node = BugFixVerifyNode(model, container)
        bug_fix_verify_tools = ToolNode(
            tools=bug_fix_verify_node.tools,
            name="bug_fix_verify_tools",
            messages_key="bug_fix_verify_messages",
        )
        bug_fix_verify_structured_node = BugFixVerifyStructuredNode(model)

        workflow = StateGraph(BugFixVerificationState)

        workflow.add_node("edit_patch_apply_node", edit_patch_apply_node)
        workflow.add_node("reproduce_bug_patch_apply_node", reproduce_bug_patch_apply_node)
        workflow.add_node("update_container_node", update_container_node)
        workflow.add_node("bug_fix_verify_node", bug_fix_verify_node)
        workflow.add_node("bug_fix_verify_tools", bug_fix_verify_tools)
        workflow.add_node("bug_fix_verify_structured_node", bug_fix_verify_structured_node)

        workflow.set_entry_point("edit_patch_apply_node")
        workflow.add_edge("edit_patch_apply_node", "reproduce_bug_patch_apply_node")
        workflow.add_edge("reproduce_bug_patch_apply_node", "update_container_node")
        workflow.add_edge("update_container_node", "bug_fix_verify_node")
        workflow.add_conditional_edges(
            "bug_fix_verify_node",
            functools.partial(tools_condition, messages_key="bug_fix_verify_messages"),
            {
                "tools": "bug_fix_verify_tools",
                END: "bug_fix_verify_structured_node",
            },
        )
        workflow.add_edge("bug_fix_verify_tools", "bug_fix_verify_node")
        workflow.add_edge("bug_fix_verify_structured_node", END)

        self.subgraph = workflow.compile()

    def invoke(
        self,
        reproduced_bug_file: str,
        reproduced_bug_commands: Sequence[str],
        reproduced_bug_patch: str,
        edit_patch: str,
        recursion_limit: int = 50,
    ):
        config = {
            "recursion_limit": recursion_limit,
        }

        input_state = {
            "reproduced_bug_file": reproduced_bug_file,
            "reproduced_bug_commands": reproduced_bug_commands,
            "reproduced_bug_patch": reproduced_bug_patch,
            "edit_patch": edit_patch,
        }

        output_state = self.subgraph.invoke(input_state, config)

        return {
            "reproducing_test_fail_log": output_state["reproducing_test_fail_log"],
        }
