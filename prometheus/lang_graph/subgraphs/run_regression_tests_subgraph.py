import functools
from typing import Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from prometheus.docker.base_container import BaseContainer
from prometheus.lang_graph.nodes.run_regression_tests_node import RunRegressionTestsNode
from prometheus.lang_graph.nodes.run_regression_tests_structure_node import (
    RunRegressionTestsStructuredNode,
)
from prometheus.lang_graph.subgraphs.run_regression_tests_state import RunRegressionTestsState


class RunRegressionTestsSubgraph:
    """
    This class defines a LangGraph-based state machine that automatically selects and runs regression tests
    for GitHub issues. It orchestrates context retrieval, tests selection, test execution, and feedback loops.
    """

    def __init__(
        self,
        base_model: BaseChatModel,
        container: BaseContainer,
    ):
        """
        Initialize the run regression tests pipeline with all necessary parts.

        Args:
            base_model: Lighter LLM for simpler tasks (e.g., file selection).
            container: Docker-based sandbox for running code.
        """
        # Run regression tests node
        run_regression_tests_node = RunRegressionTestsNode(model=base_model, container=container)
        run_regression_tests_tools = ToolNode(
            tools=run_regression_tests_node.tools,
            name="run_regression_tests_tools",
            messages_key="run_regression_tests_messages",
        )
        run_regression_tests_structured_node = RunRegressionTestsStructuredNode(model=base_model)
        # Define the state machine
        workflow = StateGraph(RunRegressionTestsState)
        workflow.add_node("run_regression_tests_node", run_regression_tests_node)
        workflow.add_node("run_regression_tests_tools", run_regression_tests_tools)
        workflow.add_node(
            "run_regression_tests_structured_node", run_regression_tests_structured_node
        )
        workflow.set_entry_point("run_regression_tests_node")
        workflow.add_conditional_edges(
            "run_regression_tests_node",
            functools.partial(tools_condition, messages_key="run_regression_tests_messages"),
            {
                "tools": "run_regression_tests_tools",
                END: "run_regression_tests_structured_node",
            },
        )
        workflow.add_edge("run_regression_tests_tools", "run_regression_tests_node")
        workflow.add_conditional_edges(
            "run_regression_tests_structured_node",
            lambda state: state["total_tests_run"] < len(state["selected_regression_tests"]),
            {
                True: "run_regression_tests_node",
                False: END,
            },
        )
        # Compile the full LangGraph subgraph
        self.subgraph = workflow.compile()

    def invoke(
        self,
        selected_regression_tests: Sequence[str],
        recursion_limit: int = 50,
    ):
        """
        Run the bug regression subgraph.

        Args:
            selected_regression_tests: List of selected regression tests to run.
            recursion_limit: Max steps before triggering recovery fallback.
        Returns:
            The result of the bug regression process
        """
        config = {"recursion_limit": recursion_limit}

        input_state = {"selected_regression_tests": selected_regression_tests}

        output_state = self.subgraph.invoke(input_state, config)
        return {
            "passed_regression_tests": output_state["passed_regression_tests"],
            "regression_test_fail_log": output_state["regression_test_fail_log"],
        }
