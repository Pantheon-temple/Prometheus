from typing import Mapping, Sequence, TypedDict

from prometheus.models.context import Context


class IssueClassificationState(TypedDict):
    # Attributes provided by the user
    issue_title: str
    issue_body: str
    issue_comments: Sequence[Mapping[str, str]]

    max_refined_query_loop: int

    # Attributes generated and by the subgraph
    issue_classification_query: str
    issue_classification_context: Sequence[Context]

    issue_type: str
