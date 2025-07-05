"""Git repository management module."""

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Sequence

from git import Git, InvalidGitRepositoryError, Repo


class GitRepository:
    """A class for managing Git repositories with support for both local and remote operations.

    This class provides a unified interface for working with Git repositories,
    whether they are local or remote (HTTPS). It supports common Git operations
    such as cloning, checking out commits, switching branches, and pushing changes.
    For remote repositories, it handles authentication using GitHub access tokens..
    """

    def __init__(
        self,
        address: str,
        working_directory: Path,
        copy_to_working_dir: bool = True,
        github_access_token: Optional[str] = None,
    ):
        """Initialize a GitRepository instance.

        Args:
          address: Either a local path to a Git repository or an HTTPS URL
            for a remote repository.
          working_directory: Directory where the repository will be stored
            or copied to.
          copy_to_working_dir: If True, creates a copy of a local
            repository in the working directory. Defaults to True.
          github_access_token: GitHub access token for authentication with remote
            repositories. Required if address is an HTTPS URL. Defaults to None.
        """
        self._logger = logging.getLogger("prometheus.git.git_repository")

        # Configure git command to use our logger
        g = Git()
        type(g).GIT_PYTHON_TRACE = "full"
        git_cmd_logger = logging.getLogger("git.cmd")

        # Ensure git command output goes to our logger
        for handler in git_cmd_logger.handlers:
            git_cmd_logger.removeHandler(handler)
        git_cmd_logger.parent = self._logger
        git_cmd_logger.propagate = True

        if address.startswith("https://"):
            if github_access_token is None:
                raise ValueError("github_access_token is required for https repository")
            self.repo = self._clone_repository(address, github_access_token, working_directory)
            self._set_default_branch()
        else:
            local_path = address
            if copy_to_working_dir:
                local_path = working_directory / os.path.basename(address)
                shutil.copytree(address, local_path)
            try:
                self.repo = Repo(local_path)
                self._set_default_branch()
            except InvalidGitRepositoryError:
                self.repo = Repo.init(local_path)
                self._set_default_branch()

    def _set_default_branch(self):
        try:
            self.default_branch = (
                self.repo.remote().refs["HEAD"].reference.name.replace("refs/heads/", "")
            )
        except ValueError:
            self.default_branch = self.repo.active_branch.name

    def _clone_repository(
        self, https_url: str, github_access_token: str, target_directory: Path
    ) -> Repo:
        """Clone a remote repository using HTTPS authentication.

        Args:
          https_url: HTTPS URL of the remote repository.
          github_access_token: GitHub access token for authentication.
          target_directory: Directory where the repository will be cloned.

        Returns:
            Repo: GitPython Repo object representing the cloned repository.
        """
        self._original_https_url = https_url
        https_url = https_url.replace("https://", f"https://{github_access_token}@")
        repo_name = https_url.split("/")[-1].split(".")[0]
        local_path = target_directory / repo_name
        if local_path.exists():
            shutil.rmtree(local_path)

        return Repo.clone_from(https_url, local_path)

    def checkout_commit(self, commit_sha: str):
        self.repo.git.checkout(commit_sha)

    def switch_branch(self, branch_name: str):
        self.repo.git.checkout(branch_name)

    def pull(self):
        self.repo.git.pull()

    def get_diff(self, excluded_files: Optional[Sequence[str]] = None) -> str:
        self.repo.git.add("-A")
        if excluded_files:
            self.repo.git.reset(excluded_files)
        diff = self.repo.git.diff("--staged")
        if diff and not diff.endswith("\n"):
            diff += "\n"
        self.repo.git.reset()
        return diff

    def get_working_directory(self) -> Path:
        return Path(self.repo.working_dir).absolute()

    def reset_repository(self):
        self.repo.git.reset("--hard")
        self.repo.git.clean("-fd")

    def remove_repository(self):
        if self.repo is not None:
            shutil.rmtree(self.repo.working_dir)
            self.repo = None

    def create_and_push_branch(self, branch_name: str, commit_message: str, patch: str):
        """Create a new branch, commit changes, and push to remote.

        This method creates a new branch, switches to it, stages all changes,
        commits them with the provided message, and pushes the branch to the
        remote repository.

        Args:
            branch_name: Name of the new branch to create.
            commit_message: Message for the commit.
            patch: The patch content to apply to the new branch.
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".patch") as tmp_file:
            tmp_file.write(patch)
            tmp_file.flush()

            new_branch = self.repo.create_head(branch_name)
            new_branch.checkout()

            self.repo.git.apply(tmp_file.name)
            self.repo.git.add(A=True)
            self.repo.index.commit(commit_message)
            self.repo.git.push("--set-upstream", "origin", branch_name)
            self.reset_repository()
            self.switch_branch(self.default_branch)
