import shutil
import tarfile
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Sequence

import docker
from prometheus.utils.logger_manager import get_logger


class BaseContainer(ABC):
    """An abstract base class for managing Docker containers with file synchronization capabilities.

    This class provides core functionality for creating, managing, and interacting with Docker
    containers. It handles container lifecycle operations including building images, starting
    containers, updating files, and cleanup. The class is designed to be extended for specific
    container implementations that specifies the Dockerfile, how to build and how to run the test.
    """

    client: docker.DockerClient = docker.from_env()
    tag_name: str
    workdir: str = "/app"
    container: docker.models.containers.Container
    project_path: Path
    timeout: int = 120

    def __init__(self, project_path: Path, workdir: Optional[str] = None):
        """Initialize the container with a project directory.

        Creates a temporary copy of the project directory to work with.

        Args:
          project_path: Path to the project directory to be containerized.
        """
        self._logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        temp_dir = Path(tempfile.mkdtemp())
        temp_project_path = temp_dir / project_path.name
        shutil.copytree(project_path, temp_project_path)
        self.project_path = temp_project_path.absolute()
        self._logger.info(f"Created temporary project directory: {self.project_path}")

        if workdir:
            self.workdir = workdir
        self._logger.debug(f"Using workdir: {self.workdir}")

        self.container = None

    @abstractmethod
    def get_dockerfile_content(self) -> str:
        """Get the content of the Dockerfile for building the container image.

        Returns:
            str: Content of the Dockerfile as a string.
        """
        pass

    def build_docker_image(self):
        """Build a Docker image using the Dockerfile content.

        Creates a Dockerfile in the project directory and builds a Docker image
        using the specified tag name.
        """
        dockerfile_content = self.get_dockerfile_content()
        dockerfile_path = self.project_path / "prometheus.Dockerfile"
        dockerfile_path.write_text(dockerfile_content)
        self._logger.info(f"Building docker image {self.tag_name}")
        self.client.images.build(
            path=str(self.project_path), dockerfile=dockerfile_path.name, tag=self.tag_name
        )

    def start_container(self):
        """Start a Docker container from the built image.

        Starts a detached container with TTY enabled and mounts the Docker socket.
        """
        self._logger.info(f"Starting container from image {self.tag_name}")
        self.container = self.client.containers.run(
            self.tag_name,
            detach=True,
            tty=True,
            network_mode="host",
            environment={"PYTHONPATH": f"{self.workdir}:$PYTHONPATH"},
            volumes={"/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"}},
        )

    def is_running(self) -> bool:
        return bool(self.container)

    def update_files(
        self, project_root_path: Path, updated_files: Sequence[Path], removed_files: Sequence[Path]
    ):
        """Update files in the running container with files from a local directory.

        Creates a tar archive of the new files and copies them into the workdir of the container.

        Args:
          new_project_path: Path to the directory containing new files.
        """
        if not project_root_path.is_absolute():
            raise ValueError("project_root_path {project_root_path} must be a absolute path")

        self._logger.info("Updating files in the container after edits.")
        for file in removed_files:
            self._logger.info(f"Removing file {file} in the container")
            self.execute_command(f"rm {file}")

        parent_dirs = {str(file.parent) for file in updated_files}
        for dir_path in sorted(parent_dirs):
            self._logger.info(f"Creating directory {dir_path} in the container")
            self.execute_command(f"mkdir -p {dir_path}")

        with tempfile.NamedTemporaryFile() as temp_tar:
            with tarfile.open(fileobj=temp_tar, mode="w") as tar:
                for file in updated_files:
                    local_absolute_file = project_root_path / file
                    self._logger.info(f"Updating {file} in the container")
                    tar.add(local_absolute_file, arcname=str(file))

            temp_tar.seek(0)

            self.container.put_archive(self.workdir, temp_tar.read())

        self._logger.info("Files updated successfully")

    @abstractmethod
    def run_build(self):
        """Run build commands in the container.

        This method should be implemented by subclasses to define build steps.
        """
        pass

    @abstractmethod
    def run_test(self):
        """Run test commands in the container.

        This method should be implemented by subclasses to define test steps.
        """
        pass

    def execute_command(self, command: str) -> str:
        """Execute a command in the running container.

        Args:
            command: Command to execute in the container.

        Returns:
            str: Output of the command as a string.
        """
        timeout_msg = f"""
*******************************************************************************
{command} timeout after {self.timeout} seconds
*******************************************************************************
"""
        timeout_command = f"timeout -k 5 {self.timeout}s {command}"
        command = f'/bin/bash -l -c "{timeout_command}"'
        self._logger.debug(f"Running command in container: {command}")
        exec_result = self.container.exec_run(command, workdir=self.workdir)
        exec_result_str = exec_result.output.decode("utf-8")

        if exec_result.exit_code in (124, 137):
            exec_result_str += timeout_msg

        self._logger.debug(f"Command output:\n{exec_result_str}")
        return exec_result_str

    def restart_container(self):
        self._logger.info("Restarting the container")
        if self.container:
            self.container.stop(timeout=10)
            self.container.remove(force=True)

        self.start_container()

    def cleanup(self):
        """Clean up container resources and temporary files.

        Stops and removes the container, removes the Docker image,
        and deletes temporary project files.
        """
        self._logger.info("Cleaning up container and temporary files")
        if self.container:
            self.container.stop(timeout=10)
            self.container.remove(force=True)
            self.container = None
            self.client.images.remove(self.tag_name, force=True)

        shutil.rmtree(self.project_path)
