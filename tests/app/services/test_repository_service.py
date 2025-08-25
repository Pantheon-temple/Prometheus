from pathlib import Path
from unittest.mock import create_autospec, patch

import pytest

from prometheus.app.entity.repository import Repository
from prometheus.app.services.database_service import DatabaseService
from prometheus.app.services.knowledge_graph_service import KnowledgeGraphService
from prometheus.app.services.repository_service import RepositoryService
from prometheus.git.git_repository import GitRepository
from tests.test_utils.fixtures import postgres_container_fixture  # noqa: F401


@pytest.fixture
def mock_kg_service():
    # Mock KnowledgeGraphService; RepositoryService only reads its attributes in other paths
    kg_service = create_autospec(KnowledgeGraphService, instance=True)
    kg_service.max_ast_depth = 3
    kg_service.chunk_size = 1000
    kg_service.chunk_overlap = 100
    return kg_service


@pytest.fixture
def mock_database_service(postgres_container_fixture):  # noqa: F811
    service = DatabaseService(postgres_container_fixture.get_connection_url())
    service.start()
    yield service
    service.close()


@pytest.fixture
def mock_git_repository():
    repo = create_autospec(GitRepository, instance=True)
    repo.get_working_directory.return_value = Path("/test/working/dir/repositories/repo")
    return repo


@pytest.fixture
def service(mock_kg_service, mock_database_service, monkeypatch):
    working_dir = "/test/working/dir"
    # Avoid touching the real filesystem when creating the base repo folder
    monkeypatch.setattr(Path, "mkdir", lambda *args, **kwargs: None)
    return RepositoryService(
        kg_service=mock_kg_service,
        database_service=mock_database_service,  # <-- use the correct fixture here
        working_dir=working_dir,
    )


async def test_clone_new_github_repo(service, mock_git_repository, monkeypatch):
    # Arrange
    test_url = "https://github.com/test/repo"
    test_commit = "abc123"
    test_github_token = "test_token"
    expected_path = Path("/test/working/dir/repositories/repo")

    # Force get_new_playground_path() to return a deterministic path for assertions
    monkeypatch.setattr(service, "get_new_playground_path", lambda: expected_path)

    # Patch GitRepository so its constructor returns our mock instance
    with patch(
        "prometheus.app.services.repository_service.GitRepository",
        return_value=mock_git_repository,
    ) as mock_git_class:
        # Act
        result_path = await service.clone_github_repo(test_github_token, test_url, test_commit)

        # Assert

        # GitRepository should be instantiated without args (per current implementation)
        mock_git_class.assert_called_once_with()

        # Ensure the clone method was invoked with correct parameters
        mock_git_repository.from_clone_repository.assert_called_once_with(
            test_url, test_github_token, expected_path
        )

        # Verify the requested commit was checked out
        mock_git_repository.checkout_commit.assert_called_once_with(test_commit)

        # The returned path should be the working directory of the mocked repo
        assert result_path == expected_path


def test_get_new_playground_path(service):
    expected_uuid = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    expected_path = service.target_directory / expected_uuid
    with patch("uuid.uuid4") as mock_uuid:
        mock_uuid.return_value.hex = expected_uuid
        result = service.get_new_playground_path()

    assert result == expected_path


def test_clean_repository_removes_dir_and_parent(service, monkeypatch):
    """
    Should call shutil.rmtree on the repository path and remove its parent directory
    when the path exists.
    """
    repo_path = Path("/tmp/repositories/abc123")
    repository = Repository(playground_path=str(repo_path))

    # Patch path.exists() to return True
    monkeypatch.setattr(Path, "exists", lambda self: self == repo_path)

    # Track calls to shutil.rmtree and Path.rmdir
    removed = {"rmtree": None, "rmdir": []}

    monkeypatch.setattr(
        "shutil.rmtree",
        lambda target: removed.update(rmtree=target),
    )
    monkeypatch.setattr(
        Path,
        "rmdir",
        lambda self: removed["rmdir"].append(self),
    )

    service.clean_repository(repository)

    # Assert rmtree called with correct path string
    assert removed["rmtree"] == str(repo_path)
    # Assert rmdir called on the parent directory
    assert repo_path.parent in removed["rmdir"]


def test_clean_repository_skips_when_not_exists(service, monkeypatch):
    """
    Should not call rmtree or rmdir when the repository path does not exist.
    """
    repo_path = Path("/tmp/repositories/abc123")
    repository = Repository(playground_path=str(repo_path))

    # Path.exists returns False
    monkeypatch.setattr(Path, "exists", lambda self: False)

    monkeypatch.setattr("shutil.rmtree", lambda target: pytest.fail("rmtree should not be called"))
    monkeypatch.setattr(Path, "rmdir", lambda self: pytest.fail("rmdir should not be called"))

    # No exception means pass
    service.clean_repository(repository)


def test_get_repository_returns_git_repo_instance(service):
    """
    Should create a GitRepository, call from_local_repository with the given path,
    and return the GitRepository instance.
    """
    test_path = "/some/local/path"

    mock_git_repo_instance = create_autospec(GitRepository, instance=True)

    # Patch GitRepository() constructor to return our mock instance
    with patch(
        "prometheus.app.services.repository_service.GitRepository",
        return_value=mock_git_repo_instance,
    ) as mock_git_class:
        result = service.get_repository(test_path)

    # Verify GitRepository() was called with no args
    mock_git_class.assert_called_once_with()

    # Verify from_local_repository was called with the correct Path object
    mock_git_repo_instance.from_local_repository.assert_called_once_with(Path(test_path))

    # Verify the returned object is the same as the mock instance
    assert result == mock_git_repo_instance


def test_create_new_repository(service):
    # Exercise
    service.create_new_repository(
        url="https://github.com/test/repo",
        commit_id="abc123",
        playground_path="/tmp/repositories/repo",
        user_id=None,
        kg_root_node_id=0,
    )


def test_get_all_repositories(service):
    # Exercise
    repos = service.get_all_repositories()
    # Verify
    assert len(repos) == 1
