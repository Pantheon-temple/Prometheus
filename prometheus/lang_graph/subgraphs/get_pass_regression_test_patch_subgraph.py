from typing import Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.constants import END
from langgraph.graph import StateGraph

from prometheus.docker.base_container import BaseContainer
from prometheus.git.git_repository import GitRepository
from prometheus.lang_graph.nodes.get_pass_regression_test_patch_check_result_node import (
    GetPassRegressionTestPatchCheckResultNode,
)
from prometheus.lang_graph.nodes.get_pass_regression_test_patch_update_node import (
    GetPassRegressionTestPatchUpdateNode,
)
from prometheus.lang_graph.nodes.noop_node import NoopNode
from prometheus.lang_graph.nodes.run_regression_tests_subgraph_node import (
    RunRegressionTestsSubgraphNode,
)
from prometheus.lang_graph.nodes.update_container_node import UpdateContainerNode
from prometheus.lang_graph.subgraphs.get_pass_regression_test_patch_state import (
    GetPassRegressionTestPatchState,
)


class GetPassRegressionTestPatchSubgraph:
    """
    This class defines a LangGraph-based state machine that automatically tests and runs regression tests
    on given patch(es) and return the patch(es) that pass the regression tests.
    """

    def __init__(
        self,
        base_model: BaseChatModel,
        container: BaseContainer,
        git_repo: GitRepository,
    ):
        """
        Initialize the pipeline with all necessary parts.

        Args:
            base_model: Lighter LLM for simpler tasks (e.g., file selection).
            container: Docker-based sandbox for running code.
        """
        noop_nodes = NoopNode()
        # Step 1: Update the Git repository with the current testing patch
        get_pass_regression_test_patch_update_node = GetPassRegressionTestPatchUpdateNode(
            git_repo=git_repo
        )
        # Step 2: Update the container with the current testing patch
        update_container_node = UpdateContainerNode(container=container, git_repo=git_repo)
        # Step 3: Run regression tests on the current testing patch
        run_regression_tests_subgraph_node = RunRegressionTestsSubgraphNode(
            model=base_model,
            container=container,
            passed_regression_tests_key="current_passed_tests",
        )
        # Step 4: Check the results of the regression tests
        get_pass_regression_test_patch_check_result_node = (
            GetPassRegressionTestPatchCheckResultNode()
        )

        # Define the state machine
        workflow = StateGraph(GetPassRegressionTestPatchState)
        # Add nodes to the workflow
        workflow.add_node("noop_nodes", noop_nodes)
        workflow.add_node(
            "get_pass_regression_test_patch_update_node", get_pass_regression_test_patch_update_node
        )
        workflow.add_node("update_container_node", update_container_node)
        workflow.add_node("run_regression_tests_subgraph_node", run_regression_tests_subgraph_node)
        workflow.add_node(
            "get_pass_regression_test_patch_check_result_node",
            get_pass_regression_test_patch_check_result_node,
        )
        # Set the entry point of the workflow
        workflow.set_entry_point("noop_nodes")
        workflow.add_conditional_edges(
            "noop_nodes",
            lambda state: len(state["untested_patches"]) > 0,
            {
                True: "get_pass_regression_test_patch_update_node",
                False: END,
            },
        )
        # Add edges between nodes
        workflow.add_edge("get_pass_regression_test_patch_update_node", "update_container_node")
        workflow.add_edge("update_container_node", "run_regression_tests_subgraph_node")
        workflow.add_edge(
            "run_regression_tests_subgraph_node", "get_pass_regression_test_patch_check_result_node"
        )
        workflow.add_edge("get_pass_regression_test_patch_check_result_node", "noop_nodes")

        # Compile the full LangGraph subgraph
        self.subgraph = workflow.compile()

    def invoke(
        self,
        selected_regression_tests: Sequence[str],
        patches: Sequence[str],
    ):
        """
        Run the bug regression subgraph.

        Args:
            selected_regression_tests: List of selected regression tests to run.
            patches: List of patches to run.
        Returns:
            The result of the bug regression process
        """
        config = {"recursion_limit": len(patches) * 20}

        input_state = {
            "selected_regression_tests": selected_regression_tests,
            "untested_patches": patches,
        }

        output_state = self.subgraph.invoke(input_state, config)
        return {
            "tested_patch_result": output_state["tested_patch_result"],
        }
