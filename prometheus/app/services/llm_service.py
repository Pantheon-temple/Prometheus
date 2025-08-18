from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from prometheus.app.services.base_service import BaseService
from prometheus.chat_models.custom_chat_openai import CustomChatOpenAI


class LLMService(BaseService):
    def __init__(
        self,
        advanced_model_name: str,
        base_model_name: str,
        advanced_model_max_input_tokens: int,
        advanced_model_max_output_tokens: int,
        advanced_model_temperature: float,
        base_model_max_input_tokens: int,
        base_model_max_output_tokens: int,
        base_model_temperature: float,
        openai_format_api_key: Optional[str] = None,
        openai_format_base_url: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
    ):
        self.advanced_model = get_model(
            advanced_model_name,
            advanced_model_temperature,
            advanced_model_max_input_tokens,
            advanced_model_max_output_tokens,
            openai_format_api_key,
            openai_format_base_url,
            anthropic_api_key,
            gemini_api_key,
        )
        self.base_model = get_model(
            base_model_name,
            base_model_temperature,
            base_model_max_input_tokens,
            base_model_max_output_tokens,
            openai_format_api_key,
            openai_format_base_url,
            anthropic_api_key,
            gemini_api_key,
        )


def get_model(
    model_name: str,
    temperature: float,
    max_input_tokens: int,
    max_output_tokens: int,
    openai_format_api_key: Optional[str] = None,
    openai_format_base_url: Optional[str] = None,
    anthropic_api_key: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
) -> BaseChatModel:
    if "claude" in model_name:
        return ChatAnthropic(
            model_name=model_name,
            api_key=anthropic_api_key,
            temperature=temperature,
            max_tokens_to_sample=max_output_tokens,
            max_retries=3,
        )
    elif "gemini" in model_name:
        return ChatGoogleGenerativeAI(
            model=model_name,
            api_key=gemini_api_key,
            temperature=temperature,
            max_tokens=max_output_tokens,
            max_retries=3,
        )
    else:
        """
        Use tiktoken_counter to ensure that the input messages do not exceed the maximum token limit.
        """
        return CustomChatOpenAI(
            max_input_tokens=max_input_tokens,
            model=model_name,
            api_key=openai_format_api_key,
            base_url=openai_format_base_url,
            temperature=temperature,
            max_tokens=max_output_tokens,
            max_retries=3,
        )
