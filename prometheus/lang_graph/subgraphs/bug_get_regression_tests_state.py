from typing import Mapping, Sequence, TypedDict

from prometheus.models.context import Context


class BugGetRegressionTestsState(TypedDict):
    issue_title: str
    issue_body: str
    issue_comments: Sequence[Mapping[str, str]]

    max_refined_query_loop: int

    select_regression_query: str
    select_regression_context: Sequence[Context]

    # Number of regression tests to select
    number_of_selected_regression_tests: int
    # Selected regression tests to run
    selected_regression_tests: Sequence[str]
