from pydantic import BaseModel

from prometheus.lang_graph.graphs.issue_state import IssueType


class IssueResponse(BaseModel):
    patch: str | None = None
    passed_reproducing_test: bool
    passed_build: bool
    passed_regression_test: bool
    passed_existing_test: bool
    issue_response: str | None = None
    issue_type: IssueType | None = None
