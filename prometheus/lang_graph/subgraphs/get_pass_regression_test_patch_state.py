from operator import add
from typing import Annotated, Sequence, TypedDict

from prometheus.models.test_patch_result import TestedPatchResult


class GetPassRegressionTestPatchState(TypedDict):
    # selected regression tests to run
    selected_regression_tests: Sequence[str]
    # untested patches to run regression tests on
    untested_patches: Sequence[str]
    # tested patches with
    tested_patch_result: Annotated[Sequence[TestedPatchResult], add]
    # Current patch
    current_patch: str
    # Current patch regression test failure log
    regression_test_fail_log: str
    # Current passed tests
    current_passed_tests: Sequence[str]
