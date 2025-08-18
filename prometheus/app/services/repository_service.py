"""Service for managing repository (GitHub or local) operations."""

import shutil
import uuid
from pathlib import Path
from typing import Optional

from sqlmodel import Session, select

from prometheus.app.entity.repository import Repository
from prometheus.app.services.base_service import BaseService
from prometheus.app.services.database_service import DatabaseService
from prometheus.app.services.knowledge_graph_service import KnowledgeGraphService
from prometheus.git.git_repository import GitRepository


class RepositoryService(BaseService):
    """Manages repository operations.

    This service provides functionality for Git repository operations including
    cloning repositories, managing commits, pushing changes, and maintaining
    a clean working directory. It integrates with a knowledge graph service
    to track repository state and avoid redundant operations.
    """

    def __init__(
        self,
        kg_service: KnowledgeGraphService,
        database_service: DatabaseService,
        working_dir: str,
    ):
        """Initializes the repository service.

        Args:
          kg_service: Knowledge graph service instance for codebase tracking.
          working_dir: Base directory for repository operations. A 'repositories'
              subdirectory will be created under this path.
        """
        self.kg_service = kg_service
        self.database_service = database_service
        self.engine = database_service.engine
        self.target_directory = Path(working_dir) / "repositories"
        self.target_directory.mkdir(parents=True, exist_ok=True)

    def get_new_playground_path(self) -> Path:
        """Generates a new unique playground path for cloning a repository.

        Returns:
            A Path object representing the new unique playground directory.
        """
        unique_id = uuid.uuid4().hex
        new_path = self.target_directory / unique_id
        while new_path.exists():
            unique_id = uuid.uuid4().hex
            new_path = self.target_directory / unique_id
        new_path.mkdir(parents=True)
        return new_path

    async def clone_github_repo(
        self, github_token: str, https_url: str, commit_id: Optional[str] = None
    ) -> Path:
        """Clones a GitHub repository to the local workspace.

        Clones the specified repository and optionally checks out a specific commit.
        If the repository is already present and matches the requested state,
        the operation may be skipped.

        Args:
            github_token: GitHub access token for authentication.
            https_url: HTTPS URL of the GitHub repository.
            commit_id: Optional specific commit to check out.

        Returns:
            Path to the local repository directory.
        """
        git_repo = GitRepository()
        await git_repo.from_clone_repository(
            https_url, github_token, self.get_new_playground_path()
        )

        if commit_id:
            git_repo.checkout_commit(commit_id)
        return git_repo.get_working_directory()

    def create_new_repository(
        self,
        url: str,
        commit_id: Optional[str],
        playground_path: str,
        user_id: Optional[int],
        kg_root_node_id: int,
    ) -> int:
        """
        Creates a new empty repository in the working directory.

        Args:
            url: The url of the repository to be created.
            commit_id: Optional commit ID to associate with the repository.
            playground_path: Path where the repository will be cloned.
            user_id: Optional user ID associated with the repository.
            kg_root_node_id: ID of the root node in the knowledge graph for this repository.

        Returns:
            The ID of the newly created repository in the database.
        """
        with Session(self.engine) as session:
            repository = Repository(
                url=url,
                commit_id=commit_id,
                playground_path=playground_path,
                user_id=user_id,
                kg_root_node_id=kg_root_node_id,
                kg_max_ast_depth=self.kg_service.max_ast_depth,
                kg_chunk_size=self.kg_service.chunk_size,
                kg_chunk_overlap=self.kg_service.chunk_overlap,
            )
            session.add(repository)
            session.commit()
            session.refresh(repository)
        return repository.id

    def get_repository_by_id(self, repository_id: int) -> Optional[Repository]:
        """
        Retrieves a repository by its ID.

        Args:
            repository_id: The ID of the repository to retrieve.

        Returns:
            The Repository instance if found, otherwise None.
        """
        with Session(self.engine) as session:
            statement = select(Repository).where(Repository.id == repository_id)
            return session.exec(statement).first()

    def get_repository_by_url_and_commit_id(self, url: str, commit_id: str) -> Optional[Repository]:
        """
        Retrieves a repository by its URL and commit ID.

        Args:
            url: The URL of the repository.
            commit_id: The commit ID of the repository.

        Returns:
            The Repository instance if found, otherwise None.
        """
        with Session(self.engine) as session:
            statement = select(Repository).where(
                Repository.url == url, Repository.commit_id == commit_id
            )
            return session.exec(statement).first()

    def update_repository_status(self, repository_id: int, is_working: bool):
        """
        Updates the working status of a repository.

        Args:
            repository_id: The ID of the repository to update.
            is_working: The new working status to set for the repository.
        """
        with Session(self.engine) as session:
            repository = session.get(Repository, repository_id)
            if repository:
                repository.is_working = is_working
                session.add(repository)
                session.commit()

    def clean_repository(self, repository: Repository):
        path = Path(repository.playground_path)
        if path.exists():
            shutil.rmtree(repository.playground_path)
            path.parent.rmdir()

    def delete_repository(self, repository: Repository):
        """
        deletes a repository from the database.

        Args:
            repository: The repository instance to mark as cleaned.
        """
        with Session(self.engine) as session:
            obj = session.get(Repository, repository.id)
            if obj:
                session.delete(obj)
                session.commit()

    def get_repository(self, local_path) -> GitRepository:
        git_repo = GitRepository()
        git_repo.from_local_repository(Path(local_path))
        return git_repo
