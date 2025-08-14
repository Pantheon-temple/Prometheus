
from langchain_core.messages import HumanMessage

from prometheus.lang_graph.subgraphs.context_retrieval_state import ContextRetrievalState
from prometheus.utils.logger_manager import get_logger


class ContextQueryMessageNode:
    def __init__(self):
        self._logger = get_logger(__name__)

    def __call__(self, state: ContextRetrievalState):
        human_message = HumanMessage(state["query"])
        self._logger.debug(f"Sending query to ContextProviderNode:\n{human_message}")
        # The message will be added to the end of the context provider messages
        return {"context_provider_messages": [human_message]}
