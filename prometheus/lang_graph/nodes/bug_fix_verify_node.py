import functools

from langchain.tools import StructuredTool
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from prometheus.docker.base_container import BaseContainer
from prometheus.lang_graph.subgraphs.bug_fix_verification_state import BugFixVerficationState
from prometheus.tools.container_command import ContainerCommandTool
from prometheus.utils.logger_manager import get_logger


class BugFixVerifyNode:
    SYS_PROMPT = """\
You are a bug fix verification agent. Your role is to verify whether a bug has been fixed by running the reproduction steps and reporting the results accurately.

Your tasks are to:
1. Execute the provided reproduction commands on the given bug reproduction file
2. If a command fails due to simple environment issues (like missing "./" prefix), make minimal adjustments to make it work
3. Report the exact output of the successful commands

Guidelines for command execution:
- Start by running commands exactly as provided
- If a command fails, you may make minimal adjustments like:
  * Adding "./" for executable files
  * Using appropriate path separators for the environment
  * Adding basic command prefixes if clearly needed (e.g., "python" for .py files)
- Do NOT modify the core logic or parameters of the commands
- Do NOT attempt to fix bugs or modify test logic
- DO NOT ASSUME ALL DEPENDENCIES ARE INSTALLED.

REMINDER:
- Install dependencies if needed!

Format your response as:
```
Result:
[exact output/result]
```

Remember: Your only job is to execute the commands and report results faithfully. Do not offer suggestions, analyze results, or try to fix issues.
"""

    HUMAN_PROMPT = """\
Reproducing bug file:
{reproduced_bug_file}

Reproducing bug commands:
{reproduced_bug_commands}
"""

    def __init__(self, model: BaseChatModel, container: BaseContainer):
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

    def format_human_message(self, state: BugFixVerficationState) -> HumanMessage:
        return HumanMessage(
            self.HUMAN_PROMPT.format(
                reproduced_bug_file=state["reproduced_bug_file"],
                reproduced_bug_commands=state["reproduced_bug_commands"],
            )
        )

    def __call__(self, state: BugFixVerficationState):
        human_message = self.format_human_message(state)
        message_history = [self.system_prompt, human_message] + state["bug_fix_verify_messages"]

        response = self.model_with_tools.invoke(message_history)

        self._logger.debug(response)
        return {"bug_fix_verify_messages": [response]}
