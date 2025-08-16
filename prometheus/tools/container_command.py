from pydantic import BaseModel, Field
from prometheus.docker.general_container import GeneralContainer
from dataclasses import dataclass

@dataclass
class ToolSpec:
    description: str
    input_schema: type

class RunCommandInput(BaseModel):
    command: str = Field("The shell command to be run in the container")

class ContainerCommandTool:
    """Tool class for executing shell commands in containers."""
    
    run_command_spec = ToolSpec(
        description="""\
        Run a shell command in the container and return the result of the command. You are always at the root
        of the codebase.
        """,
        input_schema=RunCommandInput
    )
    
    def __init__(self, container: GeneralContainer):
        """Initialize the container command tool.
        Args:
            container: The GeneralContainer instance to execute commands in.
        """
        self.container = container
    
    def run_command(self, command: str) -> str:
        """Run a shell command in the container and return the result.
        Args:
            command: The shell command to be run in the container.  
        Returns:
            The output of the command execution.
        """
        return self.container.execute_command(command)
