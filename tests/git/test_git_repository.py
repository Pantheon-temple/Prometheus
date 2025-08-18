import sys
from pathlib import Path
from unittest import mock

import pytest

from prometheus.git.git_repository import GitRepository
from tests.test_utils import test_project_paths
from tests.test_utils.fixtures import git_repo_fixture  # noqa: F401


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Test fails on Windows because of cptree in git_repo_fixture",
)
@pytest.mark.git
def test_init_with_https_url(git_repo_fixture):  # noqa: F811
    with mock.patch("git.Repo.clone_from") as mock_clone_from, mock.patch("shutil.rmtree"):
        repo = git_repo_fixture
        mock_clone_from.return_value = repo

        access_token = "access_token"
        https_url = "https://github.com/foo/bar.git"
        target_directory = test_project_paths.TEST_PROJECT_PATH

        git_repo = GitRepository()
        git_repo.from_clone_repository(
            https_url=https_url, target_directory=target_directory, github_access_token=access_token
        )

        mock_clone_from.assert_called_once_with(
            f"https://{access_token}@github.com/foo/bar.git", target_directory / "bar"
        )


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Test fails on Windows because of cptree in git_repo_fixture",
)
@pytest.mark.git
def test_checkout_commit(git_repo_fixture):  # noqa: F811
    git_repo = GitRepository()
    git_repo.from_local_repository(git_repo_fixture.working_dir)

    commit_sha = "293551b7bd9572b63018c9ed2bccea0f37726805"
    assert git_repo.repo.head.commit.hexsha != commit_sha
    git_repo.checkout_commit(commit_sha)
    assert git_repo.repo.head.commit.hexsha == commit_sha


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Test fails on Windows because of cptree in git_repo_fixture",
)
@pytest.mark.git
def test_switch_branch(git_repo_fixture):  # noqa: F811
    git_repo = GitRepository()
    git_repo.from_local_repository(git_repo_fixture.working_dir)

    branch_name = "dev"
    assert git_repo.repo.active_branch.name != branch_name
    git_repo.switch_branch(branch_name)
    assert git_repo.repo.active_branch.name == branch_name


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Test fails on Windows because of cptree in git_repo_fixture",
)
@pytest.mark.git
def test_get_diff(git_repo_fixture):  # noqa: F811
    local_path = Path(git_repo_fixture.working_dir).absolute()
    test_file = local_path / "test.c"

    # Initialize repository
    git_repo = GitRepository()
    git_repo.from_local_repository(local_path)

    # Create a change by modifying test.c
    original_content = test_file.read_text()
    new_content = "int main() { return 0; }\n"
    test_file.write_text(new_content)

    # Get diff without exclusions
    diff = git_repo.get_diff()
    assert diff is not None
    expected_diff = """\
diff --git a/test.c b/test.c
index 79a1160..76e8197 100644
--- a/test.c
+++ b/test.c
@@ -1,6 +1 @@
-#include <stdio.h>
-
-int main() {
-    printf("Hello world!");
-    return 0;
-}
\ No newline at end of file
+int main() { return 0; }
"""
    assert diff == expected_diff

    # Test with excluded files
    diff_with_exclusion = git_repo.get_diff(excluded_files=["test.c"])
    assert diff_with_exclusion == ""

    # Cleanup - restore original content
    test_file.write_text(original_content)


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Test fails on Windows because of cptree in git_repo_fixture",
)
@pytest.mark.git
def test_apply_patch(git_repo_fixture):  # noqa: F811
    local_path = Path(git_repo_fixture.working_dir).absolute()

    # Initialize repository
    git_repo = GitRepository()
    git_repo.from_local_repository(local_path)

    # Apply a patch that modifies test.c
    patch = """\
diff --git a/test.c b/test.c
--- a/test.c
+++ b/test.c
@@ -1,6 +1,1 @@
-#include <stdio.h>
-
-int main() {
-    printf("Hello world!");
-    return 0;
-}
\ No newline at end of file
+int main() { return 0; }
\ No newline at end of file

"""
    git_repo.apply_patch(patch)
    # Verify the change
    test_file = local_path / "test.c"
    assert test_file.exists()
    assert test_file.read_text() == "int main() { return 0; }"


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Test fails on Windows because of cptree in git_repo_fixture",
)
@pytest.mark.git
def test_remove_repository(git_repo_fixture):  # noqa: F811
    with mock.patch("shutil.rmtree") as mock_rmtree:
        local_path = git_repo_fixture.working_dir

        git_repo = GitRepository()
        git_repo.from_local_repository(local_path)
        assert git_repo.repo is not None

        git_repo.remove_repository()

        mock_rmtree.assert_called_once_with(local_path)
        assert git_repo.repo is None
