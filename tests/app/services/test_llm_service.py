from unittest.mock import Mock, patch

import pytest

from prometheus.app.services.llm_service import CustomChatOpenAI, LLMService, get_model


@pytest.fixture
def mock_custom_chat_openai():
    with patch("prometheus.app.services.llm_service.CustomChatOpenAI") as mock:
        yield mock


@pytest.fixture
def mock_chat_anthropic():
    with patch("prometheus.app.services.llm_service.ChatAnthropic") as mock:
        yield mock


@pytest.fixture
def mock_chat_google():
    with patch("prometheus.app.services.llm_service.ChatGoogleGenerativeAI") as mock:
        yield mock


def test_llm_service_init(mock_custom_chat_openai, mock_chat_anthropic):
    # Setup
    mock_gpt_instance = Mock()
    mock_claude_instance = Mock()
    mock_custom_chat_openai.return_value = mock_gpt_instance
    mock_chat_anthropic.return_value = mock_claude_instance

    # Exercise
    service = LLMService(
        advanced_model_name="gpt-4",
        base_model_name="claude-2.1",
        advanced_model_max_input_tokens=64000,
        advanced_model_max_output_tokens=8000,
        advanced_model_temperature=0.0,
        base_model_max_input_tokens=64000,
        base_model_max_output_tokens=8000,
        base_model_temperature=0.0,
        openai_format_api_key="openai-key",
        openai_format_base_url="https://api.openai.com/v1",
        anthropic_api_key="anthropic-key",
    )

    # Verify
    assert service.advanced_model == mock_gpt_instance
    assert service.base_model == mock_claude_instance
    mock_custom_chat_openai.assert_called_once_with(
        max_input_tokens=64000,
        model="gpt-4",
        api_key="openai-key",
        base_url="https://api.openai.com/v1",
        temperature=0.0,
        max_tokens=8000,
        max_retries=3,
    )
    mock_chat_anthropic.assert_called_once_with(
        model_name="claude-2.1",
        api_key="anthropic-key",
        temperature=0.0,
        max_tokens_to_sample=8000,
        max_retries=3,
    )


def test_get_openai_format_model(mock_custom_chat_openai):
    # Exercise
    get_model(
        model_name="openrouter/model",
        openai_format_api_key="openrouter-key",
        openai_format_base_url="https://openrouter.ai/api/v1",
        max_output_tokens=16000,
        max_input_tokens=60000,
        temperature=0.0,
    )

    # Verify
    mock_custom_chat_openai.assert_called_once_with(
        max_input_tokens=60000,
        model="openrouter/model",
        api_key="openrouter-key",
        base_url="https://openrouter.ai/api/v1",
        temperature=0.0,
        max_tokens=16000,
        max_retries=3,
    )


def test_get_model_claude(mock_chat_anthropic):
    # Exercise
    get_model(
        model_name="claude-2.1",
        anthropic_api_key="anthropic-key",
        temperature=0.0,
        max_output_tokens=8000,
        max_input_tokens=60000,
    )

    # Verify
    mock_chat_anthropic.assert_called_once_with(
        model_name="claude-2.1",
        api_key="anthropic-key",
        temperature=0.0,
        max_tokens_to_sample=8000,
        max_retries=3,
    )


def test_get_model_gemini(mock_chat_google):
    # Exercise
    get_model(
        model_name="gemini-pro",
        gemini_api_key="gemini-key",
        temperature=0.0,
        max_output_tokens=8000,
        max_input_tokens=60000,
    )

    # Verify
    mock_chat_google.assert_called_once_with(
        model="gemini-pro",
        api_key="gemini-key",
        temperature=0.0,
        max_tokens=8000,
        max_retries=3,
    )


def test_custom_chat_openai_bind_tools():
    # Setup
    model = CustomChatOpenAI(api_key="test-key", max_input_tokens=64000)
    mock_tools = [Mock()]

    # Exercise
    with patch("prometheus.chat_models.custom_chat_openai.ChatOpenAI.bind_tools") as mock_bind:
        model.bind_tools(mock_tools)

    # Verify
    mock_bind.assert_called_once_with(mock_tools, tool_choice=None, parallel_tool_calls=False)
