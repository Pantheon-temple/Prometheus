import functools

from langchain.tools import StructuredTool
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.lang_graph.subgraphs.bug_reproduction_state import BugReproductionState
from prometheus.tools.file_operation import FileOperationTool
from prometheus.utils.lang_graph_util import get_last_message_content
from prometheus.utils.logger_manager import get_logger


class BugReproducingFileNode:
    SYS_PROMPT = """\
You are a test file manager. Your task is to save the provided bug reproducing code in the project. You should:

1. Examine the project structure to identify existing test file naming patterns and test folder organization
2. Use the create_file tool to save the bug reproducing code in a SINGLE new test file that do not yet exists,
   the name should follow the project's existing test filename conventions
3. After creating the file, return its relative path

Tools available:
- create_file: Create a new SINGLE file with specified content

If create_file fails because there is already a file with that names, use another name.
Respond with the created file's relative path.
"""

    HUMAN_PROMPT = """\
Save this bug reproducing code in the project:
{bug_reproducing_code}

Current project structure:
{project_structure}
"""

    def __init__(
        self,
        model: BaseChatModel,
        kg: KnowledgeGraph,
    ):
        self.kg = kg
        self.file_operation_tool = FileOperationTool(str(kg.get_local_path()))
        self.tools = self._init_tools()
        self.model_with_tools = model.bind_tools(self.tools)
        self.system_prompt = SystemMessage(self.SYS_PROMPT)
        self._logger = get_logger(__name__)
        

    def _init_tools(self):
        """Initializes file operation tools."""
        tools = []

        read_file_fn = functools.partial(self.file_operation_tool.read_file)
        read_file_tool = StructuredTool.from_function(
            func=read_file_fn,
            name=FileOperationTool.read_file.__name__,
            description=FileOperationTool.read_file_spec.description,
            args_schema=FileOperationTool.read_file_spec.input_schema,
        )
        tools.append(read_file_tool)

        create_file_fn = functools.partial(self.file_operation_tool.create_file)
        create_file_tool = StructuredTool.from_function(
            func=create_file_fn,
            name=FileOperationTool.create_file.__name__,
            description=FileOperationTool.create_file_spec.description,
            args_schema=FileOperationTool.create_file_spec.input_schema,
        )
        tools.append(create_file_tool)

        return tools

    def format_human_message(self, state: BugReproductionState) -> HumanMessage:
        return HumanMessage(
            self.HUMAN_PROMPT.format(
                bug_reproducing_code=get_last_message_content(
                    state["bug_reproducing_write_messages"]
                ),
                project_structure=self.kg.get_file_tree(),
            )
        )

    def __call__(self, state: BugReproductionState):
        message_history = [self.system_prompt, self.format_human_message(state)] + state[
            "bug_reproducing_file_messages"
        ]

        response = self.model_with_tools.invoke(message_history)
        self._logger.debug(response)
        return {"bug_reproducing_file_messages": [response]}
