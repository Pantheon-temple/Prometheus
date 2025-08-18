import logging
import threading
from collections import Counter

from prometheus.lang_graph.subgraphs.get_pass_regression_test_patch_state import (
    GetPassRegressionTestPatchState,
)
from prometheus.models.test_patch_result import TestedPatchResult


class GetPassRegressionTestPatchCheckResultNode:
    """
    Check if the applied patch passes all the regression tests and update the state accordingly.
    """

    def __init__(self):
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes."
            f"get_pass_regression_test_patch_check_result_node"
        )

    def __call__(self, state: GetPassRegressionTestPatchState):
        """
        Check if the applied patch passes all the regression tests and update the state accordingly.

        Args:
          state: Current state containing untested patches.
        """
        # Check if the tests passed before and after applying the patch is the same
        self._logger.debug(f"All regression tests {state['selected_regression_tests']}")
        self._logger.debug(f"Current passed tests {state['current_passed_tests']}")
        # A patch is considered to have passed if the set of tests that passed after applying the patch
        # is the same as the set of tests that passed before applying the patch,
        # or if there are no regression test failures.
        # This means that the patch did not introduce any new failures
        current_patch_passed = (
            Counter(state["selected_regression_tests"]) == Counter(state["current_passed_tests"])
            or not state["regression_test_fail_log"]
        )
        # If the before_passed_regression_tests is equal to the after_passed_regression_tests,
        self._logger.debug(current_patch_passed)
        test_patch_result = TestedPatchResult(
            patch=state["current_patch"],
            passed=current_patch_passed,
            regression_test_failure_log=state["regression_test_fail_log"],
        )

        return {
            "tested_patch_result": [test_patch_result],
        }
