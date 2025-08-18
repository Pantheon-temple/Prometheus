import git
from fastapi import APIRouter, Request

from prometheus.app.decorators.require_login import requireLogin
from prometheus.app.models.requests.repository import (
    CreateBranchAndPushRequest,
    UploadRepositoryRequest,
)
from prometheus.app.models.response.response import Response
from prometheus.app.services.knowledge_graph_service import KnowledgeGraphService
from prometheus.app.services.repository_service import RepositoryService
from prometheus.app.services.user_service import UserService
from prometheus.configuration.config import settings
from prometheus.exceptions.server_exception import ServerException

router = APIRouter()


def get_github_token(request: Request, github_token: str) -> str:
    """Retrieve GitHub token from the request or user profile."""
    # If the token is provided in the request, use it directly
    if github_token:
        return github_token
    # If the token is not provided, fetch it from the user profile if logged in
    # Check if the user is authenticated
    if not settings.ENABLE_AUTHENTICATION:
        # If the user is not authenticated, raise an exception
        raise ServerException(
            code=400, message="GitHub token is required, please provide it or log in"
        )
    # If the user is authenticated, get the user service and fetch the token
    user_service: UserService = request.app.state.service["user_service"]
    user = user_service.get_user_by_id(request.state.user_id)
    github_token = user.github_token if user else None

    # If the token is still not available, raise an exception
    if not github_token:
        raise ServerException(
            code=400, message="Either provide a GitHub token or set it in your user profile"
        )
    return github_token


@router.post(
    "/upload/",
    description="""
    Upload a GitHub repository to Prometheus, default to the latest commit in the main branch.
    """,
    response_model=Response,
)
@requireLogin
async def upload_github_repository(
    upload_repository_request: UploadRepositoryRequest, request: Request
):
    # Get the repository and knowledge graph services
    repository_service: RepositoryService = request.app.state.service["repository_service"]
    repository = repository_service.get_repository_by_url_and_commit_id(
        upload_repository_request.https_url, commit_id=upload_repository_request.commit_id
    )
    if settings.ENABLE_AUTHENTICATION:
        if repository and request.state.user_id == repository.user_id:
            return Response(
                message="Repository already exists", data={"repository_id": repository.id}
            )
    else:
        if repository:
            # If the repository already exists, return its ID
            return Response(
                message="Repository already exists", data={"repository_id": repository.id}
            )

    knowledge_graph_service: KnowledgeGraphService = request.app.state.service[
        "knowledge_graph_service"
    ]
    github_token = get_github_token(request, upload_repository_request.github_token)

    try:
        # Clone the repository
        saved_path = await repository_service.clone_github_repo(
            github_token, upload_repository_request.https_url, upload_repository_request.commit_id
        )
    except git.exc.GitCommandError:
        raise ServerException(
            code=400, message=f"Unable to clone {upload_repository_request.https_url}."
        )
    # Build and save the knowledge graph from the cloned repository
    root_node_id = await knowledge_graph_service.build_and_save_knowledge_graph(saved_path)
    repository_id = repository_service.create_new_repository(
        url=upload_repository_request.https_url,
        commit_id=upload_repository_request.commit_id,
        playground_path=str(saved_path),
        user_id=request.state.user_id if settings.ENABLE_AUTHENTICATION else None,
        kg_root_node_id=root_node_id,
    )
    return Response(data={"repository_id": repository_id})


@router.post(
    "/create-branch-and-push/",
    description="""
    Create a new branch in the repository, commit changes, and push to remote.
    """,
    response_model=Response,
)
@requireLogin
async def create_branch_and_push(
    create_branch_and_push_request: CreateBranchAndPushRequest, request: Request
):
    repository_service: RepositoryService = request.app.state.service["repository_service"]
    repository = repository_service.get_repository_by_id(
        create_branch_and_push_request.repository_id
    )
    if not repository:
        raise ServerException(code=404, message="Repository not found")
    # Check if the user has permission to modify the repository
    if settings.ENABLE_AUTHENTICATION and repository.user_id != request.state.user_id:
        raise ServerException(
            code=403, message="You do not have permission to modify this repository"
        )
    git_repo = repository_service.get_repository(repository.playground_path)
    try:
        await git_repo.create_and_push_branch(
            branch_name=create_branch_and_push_request.branch_name,
            commit_message=create_branch_and_push_request.commit_message,
            patch=create_branch_and_push_request.patch,
        )
    except git.exc.GitCommandError as e:
        raise e
    return Response()


@router.delete(
    "/delete/",
    description="""
    Delete the repository uploaded to Prometheus, along with other information.
    """,
    response_model=Response,
)
@requireLogin
def delete(repository_id: int, request: Request):
    knowledge_graph_service: KnowledgeGraphService = request.app.state.service[
        "knowledge_graph_service"
    ]
    repository_service: RepositoryService = request.app.state.service["repository_service"]
    repository = repository_service.get_repository_by_id(repository_id)
    if not repository:
        raise ServerException(code=404, message="Repository not found")
    # Check if the user has permission to delete the repository
    if settings.ENABLE_AUTHENTICATION and repository.user_id != request.state.user_id:
        raise ServerException(
            code=403, message="You do not have permission to delete this repository"
        )
    # Clear the knowledge graph and repository data
    knowledge_graph_service.clear_kg(repository.kg_root_node_id)
    repository_service.clean_repository(repository)
    # Delete the repository from the database
    repository_service.delete_repository(repository)
    return Response()
