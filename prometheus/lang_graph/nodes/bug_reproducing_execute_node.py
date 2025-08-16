import functools
from pathlib import Path
from typing import Optional, Sequence

from langchain.tools import StructuredTool
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from prometheus.docker.base_container import BaseContainer
from prometheus.lang_graph.subgraphs.bug_reproduction_state import BugReproductionState
from prometheus.tools.container_command import ContainerCommandTool
from prometheus.utils.issue_util import format_test_commands
from prometheus.utils.patch_util import get_updated_files
from prometheus.utils.logger_manager import get_logger  


class BugReproducingExecuteNode:
    SYS_PROMPT = """\
You are a testing expert focused solely on executing THE SINGLE bug reproduction test file.
Your only goal is to run the test file created by the previous agent and return its output as it is.

Adapt the user provided test command to execute the single bug reproduction test file, otherwise
figure out what test framework it uses.

Rules:
* DO NOT EXECUTE THE WHOLE TEST SUITE. ONLY EXECUTE THE SINGLE BUG REPRODUCTION TEST FILE.
* DO NOT EDIT ANY FILES.
* DO NOT ASSUME ALL DEPENDENCIES ARE INSTALLED.
* STOP TRYING IF THE TEST EXECUTES.

REMINDER:
* Install dependencies if needed!
"""

    HUMAN_PROMPT = """\
ISSUE INFORMATION:
Title: {title}
Description: {body}
Comments: {comments}

Bug reproducing file:
{reproduced_bug_file}

User provided test commands:
{test_commands}
"""

    def __init__(
        self,
        model: BaseChatModel,
        container: BaseContainer,
        test_commands: Optional[Sequence[str]] = None,
    ):
        self.test_commands = test_commands
        self.container_command_tool = ContainerCommandTool(container)
        self.tools = self._init_tools()
        self.model_with_tools = model.bind_tools(self.tools)
        self.system_prompt = SystemMessage(self.SYS_PROMPT)
        self._logger = get_logger(__name__)

    def _init_tools(self):
        tools = []

        run_command_fn = functools.partial(self.container_command_tool.run_command)
        run_command_tool = StructuredTool.from_function(
            func=run_command_fn,
            name=self.container_command_tool.run_command.__name__,
            description=self.container_command_tool.run_command_spec.description,
            args_schema=self.container_command_tool.run_command_spec.input_schema,
        )
        tools.append(run_command_tool)

        return tools

    def added_test_filename(self, state: BugReproductionState) -> Path:
        added_files, modified_file, removed_files = get_updated_files(
            state["bug_reproducing_patch"]
        )
        if removed_files:
            raise ValueError("The bug reproducing patch delete files")
        if modified_file:
            raise ValueError("The bug reproducing patch modified existing files")
        if len(added_files) != 1:
            raise ValueError("The bug reproducing patch added not one files")
        return added_files[0]

    def format_human_message(
        self, state: BugReproductionState, reproduced_bug_file: str
    ) -> HumanMessage:
        test_commands_str = ""
        if self.test_commands:
            test_commands_str = format_test_commands(self.test_commands)
        return HumanMessage(
            self.HUMAN_PROMPT.format(
                title=state["issue_title"],
                body=state["issue_body"],
                comments=state["issue_comments"],
                reproduced_bug_file=reproduced_bug_file,
                test_commands=test_commands_str,
            )
        )

    def __call__(self, state: BugReproductionState):
        try:
            reproduced_bug_file = self.added_test_filename(state)
        except ValueError as e:
            self._logger.error(f"Error in bug reproducing execute node: {e}")
            return {
                "bug_reproducing_execute_messages": [
                    AIMessage(f"THE TEST WAS NOT EXECUTED BECAUSE OF AN ERROR: {str(e)}")
                ],
            }

        message_history = [
            self.system_prompt,
            self.format_human_message(state, str(reproduced_bug_file)),
        ] + state["bug_reproducing_execute_messages"]

        response = self.model_with_tools.invoke(message_history)
        self._logger.debug(response)
        return {
            "bug_reproducing_execute_messages": [response],
            "reproduced_bug_file": reproduced_bug_file,
        }
