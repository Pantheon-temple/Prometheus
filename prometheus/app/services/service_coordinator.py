"""Central coordinator for managing interactions between various prometheus services.

This coordinator orchestrates the interactions between multiple specialized services
including knowledge graph management, LLM operations, database connections, and
repository management. It provides a unified interface for codebase analysis,
issue handling, and conversation management.
"""

import traceback
from datetime import datetime
from pathlib import Path
from typing import Mapping, Optional, Sequence

from prometheus.app.services.issue_service import IssueService
from prometheus.app.services.knowledge_graph_service import KnowledgeGraphService
from prometheus.app.services.llm_service import LLMService
from prometheus.app.services.neo4j_service import Neo4jService
from prometheus.app.services.repository_service import RepositoryService
from prometheus.lang_graph.graphs.issue_state import IssueType
from prometheus.utils.logger_manager import get_logger, create_timestamped_file_handler


class ServiceCoordinator:
    """Coordinates operations between various prometheus services.

    This class serves as the central orchestrator for all service interactions,
    managing the lifecycle of various operations including codebase analysis,
    issue handling, and conversation management. It ensures proper initialization,
    coordination, and cleanup of all dependent services.
    """

    def __init__(
        self,
        issue_service: IssueService,
        knowledge_graph_service: KnowledgeGraphService,
        llm_service: LLMService,
        neo4j_service: Neo4jService,
        repository_service: RepositoryService,
        max_token_per_neo4j_result: int,
        github_token: str,
        working_directory: Path,
    ):
        """Initializes the service coordinator with required services.

        Args:
          issue_service: Service for issue handling.
          knowledge_graph_service: Service for knowledge graph operations.
          llm_service: Service for language model operations.
          neo4j_service: Service for Neo4j database operations.
          repository_service: Service for repository management.
          max_token_per_neo4j_result: Maximum number of tokens per Neo4j result.
          github_token: GitHub access token for repository operations.
          working_directory: Working directory for all Prometheus related files.
        """
        self.issue_service = issue_service
        self.knowledge_graph_service = knowledge_graph_service
        self.llm_service = llm_service
        self.neo4j_service = neo4j_service
        self.repository_service = repository_service
        self.max_token_per_neo4j_result = max_token_per_neo4j_result
        self.github_token = github_token
        self.working_directory = working_directory
        self.answer_issue_log_dir = self.working_directory / "answer_issue_logs"
        self.answer_issue_log_dir.mkdir(parents=True, exist_ok=True)
        self._logger = get_logger(__name__)

        if (
            self.knowledge_graph_service.get_local_path()
            != self.repository_service.get_working_dir()
        ):
            self._logger.critical(
                f"Knowledge graph and repository working directories do not match: {self.knowledge_graph_service.get_local_path()} vs {self.repository_service.get_working_dir()}. Resetting all services."
            )
            self.clear()

    def answer_issue(
        self,
        issue_number: int,
        issue_title: str,
        issue_body: str,
        issue_comments: Sequence[Mapping[str, str]],
        issue_type: IssueType,
        run_build: bool,
        run_existing_test: bool,
        number_of_candidate_patch: int,
        dockerfile_content: Optional[str] = None,
        image_name: Optional[str] = None,
        workdir: Optional[str] = None,
        build_commands: Optional[Sequence[str]] = None,
        test_commands: Optional[Sequence[str]] = None,
        push_to_remote: Optional[bool] = None,
    ):
        """
        Processes an issue, generates patches if needed, runs optional builds and tests,
        and can push changes to a remote branch.

        Args:
            issue_number: The issue number to process.
            issue_title: Title of the issue.
            issue_body: Body of the issue.
            issue_comments: Comments on the issue.
            issue_type: Type of the issue (e.g., bug, feature).
            run_build: Whether to run a build after applying the patch.
            run_existing_test: Whether to run existing tests after applying the patch.
            number_of_candidate_patch: Number of candidate patches to generate.
            dockerfile_content: Optional Dockerfile content for user-defined environment.
            image_name: Optional name for the Docker image.
            workdir: Working directory for the container.
            build_commands: Commands to build the project.
            test_commands: Commands to test the project.
            push_to_remote: Whether to push changes to a remote branch.
        Returns:
            A tuple containing:
                - remote_branch_name: Name of the remote branch if changes were pushed.
                - patch: The generated patch for the issue.
                - passed_reproducing_test: Whether the reproducing test passed.
                - passed_build: Whether the build passed.
                - passed_existing_test: Whether existing tests passed.
                - issue_response: Response from the issue service after processing.
        """
        # 为这个特定的issue处理创建带时间戳的日志文件处理器
        file_handler = create_timestamped_file_handler(
            self.answer_issue_log_dir, 
            f"issue_{issue_number}", 
            "prometheus"
        )

        try:
            # fix issue
            patch, passed_reproducing_test, passed_build, passed_existing_test, issue_response = (
                self.issue_service.answer_issue(
                    issue_title=issue_title,
                    issue_body=issue_body,
                    issue_comments=issue_comments,
                    issue_type=issue_type,
                    run_build=run_build,
                    run_existing_test=run_existing_test,
                    number_of_candidate_patch=number_of_candidate_patch,
                    dockerfile_content=dockerfile_content,
                    image_name=image_name,
                    workdir=workdir,
                    build_commands=build_commands,
                    test_commands=test_commands,
                )
            )
            # push to remote if requested
            remote_branch_name = None
            if patch and push_to_remote:
                remote_branch_name = self.repository_service.push_change_to_remote(
                    f"Fixes #{issue_number}", patch
                )
            return (
                remote_branch_name,
                patch,
                passed_reproducing_test,
                passed_build,
                passed_existing_test,
                issue_response,
            )
        except Exception as e:
            self._logger.error(f"Error in answer_issue: {str(e)}\n{traceback.format_exc()}")
            return None, None, False, False, False, None
        # finally:
        #     # 移除文件处理器并关闭文件
        #     self._logger.remove_file_handler(file_handler, "prometheus")

    def exists_knowledge_graph(self) -> bool:
        return self.knowledge_graph_service.exists()

    def upload_local_repository(self, path: Path):
        """Uploads a local repository.

        Args:
          path: Path to the local repository directory.
        """
        self.clear()
        self.knowledge_graph_service.build_and_save_knowledge_graph(path)

    def upload_github_repository(self, https_url: str, commit_id: Optional[str] = None):
        """Uploads a GitHub repository.

        Args:
            https_url: HTTPS URL of the GitHub repository.
            commit_id: Optional specific commit to analyze.
        """
        # CLean the existing knowledge graph and repository state
        self.clear()
        # Clone the repository
        saved_path = self.repository_service.clone_github_repo(
            self.github_token, https_url, commit_id
        )
        # Build and save the knowledge graph from the cloned repository
        self.knowledge_graph_service.build_and_save_knowledge_graph(
            saved_path, https_url, commit_id
        )

    def clear(self):
        """Clears all service state and working directories.

        Resets the knowledge graph, cleans repository working directory,
        and reinitializes subgraph services.
        """
        self.knowledge_graph_service.clear()
        self.repository_service.clean()

    def close(self):
        """Closes all database connections and releases resources.

        This method should be called when the coordinator is no longer needed
        to ensure proper cleanup of database connections and resources.
        """
        self.neo4j_service.close()
