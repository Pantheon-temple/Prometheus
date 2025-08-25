from typing import Mapping, Sequence, TypedDict

from prometheus.models.context import Context


class IssueQuestionState(TypedDict):
    issue_title: str
    issue_body: str
    issue_comments: Sequence[Mapping[str, str]]

    max_refined_query_loop: int

    question_query: str
    question_context: Sequence[Context]

    question_response: str
