import asyncio

from fastapi import APIRouter, Request

from prometheus.app.decorators.require_login import requireLogin
from prometheus.app.models.requests.issue import IssueRequest
from prometheus.app.models.response.issue import IssueResponse
from prometheus.app.models.response.response import Response
from prometheus.app.services.issue_service import IssueService
from prometheus.app.services.knowledge_graph_service import KnowledgeGraphService
from prometheus.app.services.repository_service import RepositoryService
from prometheus.app.services.user_service import UserService
from prometheus.configuration.config import settings
from prometheus.exceptions.server_exception import ServerException

router = APIRouter()


@router.post(
    "/answer/",
    summary="Process and generate a response for an issue",
    description="Analyzes an issue, generates patches if needed, runs optional builds and tests, and can push changes "
    "to a remote branch.",
    response_description="Returns the patch, test results, and issue response",
    response_model=Response[IssueResponse],
)
@requireLogin
async def answer_issue(issue: IssueRequest, request: Request) -> Response[IssueResponse]:
    # Retrieve necessary services from the application state
    repository_service: RepositoryService = request.app.state.service["repository_service"]
    user_service: UserService = request.app.state.service["user_service"]
    issue_service: IssueService = request.app.state.service["issue_service"]
    knowledge_graph_service: KnowledgeGraphService = request.app.state.service[
        "knowledge_graph_service"
    ]

    # Fetch the repository by ID
    repository = repository_service.get_repository_by_id(issue.repository_id)
    # Ensure the repository exists
    if not repository:
        raise ServerException(code=404, message="Repository not found")
    # Ensure the user has access to the repository
    if settings.ENABLE_AUTHENTICATION and repository.user_id != request.state.user_id:
        raise ServerException(code=403, message="You do not have access to this repository")

    # Check issue credit
    user_issue_credit = None
    if settings.ENABLE_AUTHENTICATION:
        user_issue_credit = user_service.get_issue_credit(request.state.user_id)
        if user_issue_credit <= 0:
            raise ServerException(
                code=403,
                message="Insufficient issue credits. Please purchase more to continue.",
            )

    # Validate Dockerfile and workdir inputs
    if issue.dockerfile_content or issue.image_name:
        if issue.workdir is None:
            raise ServerException(
                code=400,
                message="workdir must be provided for user defined environment",
            )
    # Ensure the repository is not currently being used
    if repository.is_working:
        raise ServerException(
            code=400,
            message="The repository is currently being used. Please try again later.",
        )

    # Load the git repository and knowledge graph
    git_repository = repository_service.get_repository(repository.playground_path)
    knowledge_graph = knowledge_graph_service.get_knowledge_graph(
        repository.kg_root_node_id,
        repository.kg_max_ast_depth,
        repository.kg_chunk_size,
        repository.kg_chunk_overlap,
    )

    # Process the issue in a separate thread to avoid blocking the event loop
    (
        patch,
        passed_reproducing_test,
        passed_build,
        passed_regression_test,
        passed_existing_test,
        issue_response,
        issue_type,
    ) = await asyncio.to_thread(
        issue_service.answer_issue,
        repository_id=repository.id,
        repository=git_repository,
        knowledge_graph=knowledge_graph,
        issue_title=issue.issue_title,
        issue_body=issue.issue_body,
        issue_comments=issue.issue_comments if issue.issue_comments else [],
        issue_type=issue.issue_type,
        run_build=issue.run_build,
        run_existing_test=issue.run_existing_test,
        run_regression_test=issue.run_regression_test,
        run_reproduce_test=issue.run_reproduce_test,
        number_of_candidate_patch=issue.number_of_candidate_patch,
        dockerfile_content=issue.dockerfile_content,
        image_name=issue.image_name,
        workdir=issue.workdir,
        build_commands=issue.build_commands,
        test_commands=issue.test_commands,
    )

    # Check if all outputs are in their initial state, indicating a failure
    if (
        patch,
        passed_reproducing_test,
        passed_build,
        passed_regression_test,
        passed_existing_test,
        issue_response,
        issue_type,
    ) == (None, False, False, False, False, None, None):
        raise ServerException(
            code=500,
            message="Failed to process the issue. Please try again later.",
        )

    # Deduct issue credit after successful processing
    if settings.ENABLE_AUTHENTICATION:
        user_service.update_issue_credit(request.state.user_id, user_issue_credit - 1)

    # Return the response
    return Response(
        data=IssueResponse(
            patch=patch,
            passed_reproducing_test=passed_reproducing_test,
            passed_build=passed_build,
            passed_regression_test=passed_regression_test,
            passed_existing_test=passed_existing_test,
            issue_response=issue_response,
            issue_type=issue_type,
        )
    )
