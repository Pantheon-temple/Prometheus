"""Git repository management module."""

import asyncio
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Sequence

from git import Git, GitCommandError, InvalidGitRepositoryError, Repo


class GitRepository:
    """A class for managing Git repositories with support for both local and remote operations.

    This class provides a unified interface for working with Git repositories,
    whether they are local or remote (HTTPS). It supports common Git operations
    such as cloning, checking out commits, switching branches, and pushing changes.
    For remote repositories, it handles authentication using GitHub access tokens.
    """

    def __init__(self):
        """
        Initialize a GitRepository instance.
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

        self.repo = None
        self.playground_path = None

    def _set_default_branch(self):
        if self.repo is None:
            raise InvalidGitRepositoryError("No repository is currently set.")
        try:
            self.default_branch = (
                self.repo.remote().refs["HEAD"].reference.name.replace("refs/heads/", "")
            )
        except ValueError:
            self.default_branch = self.repo.active_branch.name

    async def from_clone_repository(
        self, https_url: str, github_access_token: str, target_directory: Path
    ):
        """Clone a remote repository using HTTPS authentication.

        Args:
          https_url: HTTPS URL of the remote repository.
          github_access_token: GitHub access token for authentication.
          target_directory: Directory where the repository will be cloned.

        Returns:
            Repo: GitPython Repo object representing the cloned repository.
        """
        https_url = https_url.replace("https://", f"https://x-access-token:{github_access_token}@")
        repo_name = https_url.split("/")[-1].split(".")[0]
        local_path = target_directory / repo_name
        if local_path.exists():
            shutil.rmtree(local_path)

        self.repo = await asyncio.to_thread(Repo.clone_from, https_url, local_path)
        self.playground_path = local_path
        self._set_default_branch()

    def from_local_repository(self, local_path: Path):
        """Initialize the GitRepository from a local repository path.

        Args:
            local_path: Path to the local Git repository.

        Raises:
            InvalidGitRepositoryError: If the provided path is not a valid Git repository.
        """
        if not local_path.is_dir() or not (local_path / ".git").exists():
            raise InvalidGitRepositoryError(f"{local_path} is not a valid Git repository.")

        self.repo = Repo(local_path)
        self.playground_path = local_path
        self._set_default_branch()

    def checkout_commit(self, commit_sha: str):
        if self.repo is None:
            raise InvalidGitRepositoryError("No repository is currently set.")
        self.repo.git.checkout(commit_sha)

    def switch_branch(self, branch_name: str):
        if self.repo is None:
            raise InvalidGitRepositoryError("No repository is currently set.")
        self.repo.git.checkout(branch_name)

    def pull(self):
        if self.repo is None:
            raise InvalidGitRepositoryError("No repository is currently set.")
        self.repo.git.pull()

    def get_diff(self, excluded_files: Optional[Sequence[str]] = None) -> str:
        if self.repo is None:
            raise InvalidGitRepositoryError("No repository is currently set.")
        self.repo.git.add("-A")
        if excluded_files:
            self.repo.git.reset(excluded_files)
        diff = self.repo.git.diff("--staged")
        if diff and not diff.endswith("\n"):
            diff += "\n"
        self.repo.git.reset()
        return diff

    def get_working_directory(self) -> Path:
        if self.repo is None:
            raise InvalidGitRepositoryError("No repository is currently set.")
        return Path(self.repo.working_dir).absolute()

    def reset_repository(self):
        if self.repo is None:
            raise InvalidGitRepositoryError("No repository is currently set.")
        self.repo.git.reset("--hard")
        self.repo.git.clean("-fd")

    def remove_repository(self):
        if self.repo is not None:
            shutil.rmtree(self.repo.working_dir)
            self.repo = None

    def apply_patch(self, patch: str):
        """Apply a patch to the current repository."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".patch") as tmp_file:
            tmp_file.write(patch)
            tmp_file.flush()
            self.repo.git.apply(tmp_file.name)

    async def create_and_push_branch(self, branch_name: str, commit_message: str, patch: str):
        """Create a new branch, commit changes, and push to remote.

        This method creates a new branch, switches to it, stages all changes,
        commits them with the provided message, and pushes the branch to the
        remote repository.

        Args:
            branch_name: Name of the new branch to create.
            commit_message: Message for the commit.
            patch: Patch to apply to the branch.
        """
        if self.repo is None:
            raise InvalidGitRepositoryError("No repository is currently set.")

        # Get the current commit SHA to ensure we can reset later
        start_commit_sha = self.repo.head.commit.hexsha
        try:
            # create and checkout new branch
            new_branch = self.repo.create_head(branch_name)
            new_branch.checkout()
            # Apply the patch and commit changes
            self.apply_patch(patch)
            self.repo.git.add(A=True)
            self.repo.index.commit(commit_message)
            await asyncio.to_thread(self.repo.git.push, "--set-upstream", "origin", branch_name)
        except GitCommandError as e:
            raise e
        finally:
            self.reset_repository()
            # Reset to the original commit
            self.checkout_commit(start_commit_sha)
