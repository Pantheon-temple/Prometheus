from enum import StrEnum
from typing import Mapping, Sequence, TypedDict


class IssueType(StrEnum):
    AUTO = "auto"
    BUG = "bug"
    FEATURE = "feature"
    DOCUMENTATION = "documentation"
    QUESTION = "question"


class IssueState(TypedDict):
    # Attributes provided by the user
    issue_title: str
    issue_body: str
    issue_comments: Sequence[Mapping[str, str]]
    issue_type: IssueType
    run_build: bool
    run_existing_test: bool
    run_regression_test: bool
    run_reproduce_test: bool
    number_of_candidate_patch: int

    edit_patch: str

    passed_regression_test: bool
    passed_reproducing_test: bool
    passed_build: bool
    passed_existing_test: bool

    issue_response: str
