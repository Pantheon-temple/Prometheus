import logging
import threading
from typing import Dict

from langchain_core.language_models.chat_models import BaseChatModel

from prometheus.docker.base_container import BaseContainer
from prometheus.lang_graph.subgraphs.run_regression_tests_subgraph import RunRegressionTestsSubgraph


class RunRegressionTestsSubgraphNode:
    def __init__(
        self, model: BaseChatModel, container: BaseContainer, passed_regression_tests_key: str
    ):
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.run_regression_tests_subgraph_node"
        )
        self.subgraph = RunRegressionTestsSubgraph(
            base_model=model,
            container=container,
        )
        self.passed_regression_tests_key = passed_regression_tests_key

    def __call__(self, state: Dict):
        self._logger.info("Enter run_regression_tests_subgraph_node")
        if not state["selected_regression_tests"]:
            self._logger.info("No regression tests selected, skipping regression tests subgraph.")
            return {
                self.passed_regression_tests_key: [],
                "regression_test_fail_log": "",
            }

        self._logger.debug(f"selected_regression_tests: {state['selected_regression_tests']}")

        output_state = self.subgraph.invoke(
            selected_regression_tests=state["selected_regression_tests"]
        )

        self._logger.info(f"passed_regression_tests: {output_state['passed_regression_tests']}")
        self._logger.debug(f"regression_test_fail_log: {output_state['regression_test_fail_log']}")

        return {
            self.passed_regression_tests_key: output_state["passed_regression_tests"],
            "regression_test_fail_log": output_state["regression_test_fail_log"],
        }
