import logging
import threading
import uuid
from typing import Any

from langchain_core.messages import ToolMessage

from prometheus.docker.base_container import BaseContainer


class UserDefinedTestNode:
    def __init__(self, container: BaseContainer):
        self.container = container
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.user_defined_test_node"
        )

    def __call__(self, _: Any):
        test_output = self.container.run_test()
        self._logger.debug(f"UserDefinedTestNode response:\n{test_output}")

        tool_message = ToolMessage(
            test_output, tool_call_id=f"user_defined_test_commands_{uuid.uuid4().hex[:10]}"
        )
        return {"test_messages": [tool_message]}
