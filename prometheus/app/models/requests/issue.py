from typing import Mapping, Optional, Sequence

from pydantic import BaseModel, Field

from prometheus.lang_graph.graphs.issue_state import IssueType


class IssueRequest(BaseModel):
    repository_id: int = Field(
        description="The ID of the repository this issue belongs to.", examples=[1]
    )
    issue_title: str = Field(
        description="The title of the issue", examples=["There is a memory leak"]
    )
    issue_body: str = Field(
        description="The description of the issue", examples=["foo/bar.c is causing a memory leak"]
    )
    issue_comments: Optional[Sequence[Mapping[str, str]]] = Field(
        default=None,
        description="Comments on the issue",
        examples=[
            [
                {"username": "user1", "comment": "I've experienced this issue as well."},
                {
                    "username": "user2",
                    "comment": "A potential fix is to adjust the memory settings.",
                },
            ]
        ],
    )
    issue_type: IssueType = Field(
        default=IssueType.AUTO,
        description="The type of the issue, set to auto if you do not know",
        examples=[IssueType.AUTO],
    )
    run_build: Optional[bool] = Field(
        default=False,
        description="When editing the code, whenever we should run the build to verify the fix",
        examples=[False],
    )
    run_existing_test: Optional[bool] = Field(
        default=False,
        description="When editing the code, whenever we should run the existing test to verify the fix",
        examples=[False],
    )
    run_regression_test: Optional[bool] = Field(
        default=True,
        description="When editing the code, whenever we should run regression tests to verify the fix",
        examples=[True],
    )
    run_reproduce_test: Optional[bool] = Field(
        default=True,
        description="When editing the code, whenever we should run the reproduce test to verify the fix",
        examples=[False],
    )
    number_of_candidate_patch: Optional[int] = Field(
        default=5,
        description="When the patch is not verified (through build or test), "
        "number of candidate patches we generate to select the best one",
        examples=[5],
    )
    dockerfile_content: Optional[str] = Field(
        default=None,
        description="Specify the containerized environment with dockerfile content",
        examples=["FROM python:3.11\nWORKDIR /app\nCOPY . /app"],
    )
    image_name: Optional[str] = Field(
        default=None,
        description="Specify the containerized environment with image name that should be pulled from dockerhub",
        examples=["python:3.11-slim"],
    )
    workdir: Optional[str] = Field(
        default=None,
        description="If you specified the container environment, you must also specify the workdir",
        examples=["/app"],
    )
    build_commands: Optional[Sequence[str]] = Field(
        default=None,
        description="If you specified dockerfile_content and run_build is True, "
        "you must also specify the build commands.",
        examples=[["pip install -r requirements.txt", "python -m build"]],
    )
    test_commands: Optional[Sequence[str]] = Field(
        default=None,
        description="If you specified dockerfile_content and run_test is True, "
        "you must also specify the test commands.",
        examples=[["pytest ."]],
    )
