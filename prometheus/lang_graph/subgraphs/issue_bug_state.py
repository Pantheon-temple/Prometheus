from typing import Mapping, Sequence, TypedDict


class IssueBugState(TypedDict):
    issue_title: str
    issue_body: str
    issue_comments: Sequence[Mapping[str, str]]

    run_build: bool
    run_existing_test: bool
    run_regression_test: bool
    run_reproduce_test: bool

    number_of_candidate_patch: int

    reproduced_bug: bool
    reproduced_bug_file: str
    reproduced_bug_commands: Sequence[str]
    reproduced_bug_patch: str

    selected_regression_tests: Sequence[str]

    edit_patch: str

    passed_reproducing_test: bool
    passed_build: bool
    passed_existing_test: bool

    issue_response: str
