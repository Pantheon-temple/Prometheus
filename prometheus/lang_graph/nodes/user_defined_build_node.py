import uuid
from typing import Any

from langchain_core.messages import ToolMessage

from prometheus.docker.base_container import BaseContainer
from prometheus.utils.logger_manager import get_logger


class UserDefinedBuildNode:
    def __init__(self, container: BaseContainer):
        self.container = container
        self._logger = get_logger(__name__)

    def __call__(self, _: Any):
        build_output = self.container.run_build()
        self._logger.debug(f"UserDefinedBuildNode response:\n{build_output}")

        tool_message = ToolMessage(
            content=build_output,
            tool_call_id=f"user_defined_build_commands_{uuid.uuid4().hex[:10]}",
        )
        return {"build_messages": [tool_message]}
