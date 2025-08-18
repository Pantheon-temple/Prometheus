from typing import Any, Optional

from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import BaseMessage, trim_messages
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from pydantic import PrivateAttr

from prometheus.utils.llm_util import tiktoken_counter


class CustomChatOpenAI(ChatOpenAI):
    _max_input_tokens: int = PrivateAttr()

    def __init__(self, max_input_tokens: int, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._max_input_tokens = max_input_tokens

    def bind_tools(self, tools, tool_choice=None, **kwargs):
        kwargs["parallel_tool_calls"] = False
        return super().bind_tools(tools, tool_choice=tool_choice, **kwargs)

    def invoke(
        self,
        input: LanguageModelInput,
        config: Optional[RunnableConfig] = None,
        *,
        stop: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> BaseMessage:
        return super().invoke(
            input=trim_messages(
                input,
                token_counter=tiktoken_counter,
                strategy="last",
                max_tokens=self._max_input_tokens,
                start_on="human",
                end_on=("human", "tool"),
                include_system=True,
            ),
            config=config,
            stop=stop,
            **kwargs,
        )
