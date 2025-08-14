"""Container synchronization handler for agent-made changes.

This module provides functionality to synchronize file changes made by AI agents
with a container environment. It ensures that any modifications made to the project
files are properly reflected in the container's filesystem, maintaining consistency
between the agent's workspace and the container environment.
"""

from typing import Dict

from prometheus.docker.base_container import BaseContainer
from prometheus.git.git_repository import GitRepository
from prometheus.utils.patch_util import get_updated_files
from prometheus.utils.logger_manager import get_logger


class UpdateContainerNode:
    """Synchronizes agent-made changes with container filesystem.

    This class handles the synchronization of file changes between an agent's
    workspace and a container environment. It ensures that any modifications
    made by AI agents (such as code fixes or edits) are properly reflected
    in the container where builds, tests, or other operations may occur.
    """

    def __init__(self, container: BaseContainer, git_repo: GitRepository):
        """Initializes the UpdateContainerNode with a target container.

        Args:
          container: Container instance that will receive file updates. Must
            be a subclass of BaseContainer implementing the update_files method.
          git_repo: The local git repository used to retrieve the project's files.
        """
        self.container = container
        self.git_repo = git_repo
        self._logger = get_logger(__name__)

    def __call__(self, _: Dict):
        """Synchronizes the current project state with the container."""
        if self.container.is_running():
            self._logger.info("Copy over all updated files to the container")
            all_files_patch = self.git_repo.get_diff()
            self.container.restart_container()
            added_files, modified_file, removed_files = get_updated_files(all_files_patch)
            self.container.update_files(
                self.git_repo.get_working_directory(), added_files + modified_file, removed_files
            )
        else:
            self._logger.info(
                "Not updating files in docker container because it is not running, "
                "most likely due to run_build and run_test are both false."
            )
