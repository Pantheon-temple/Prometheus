from langchain_core.messages import HumanMessage

from prometheus.app.services.llm_service import LLMService
from prometheus.configuration.config import settings


def test_model_response():
    llm_service = LLMService(
        settings.ADVANCED_MODEL,
        settings.BASE_MODEL,
        settings.ADVANCED_MODEL_MAX_INPUT_TOKENS,
        settings.ADVANCED_MODEL_MAX_OUTPUT_TOKENS,
        settings.ADVANCED_MODEL_TEMPERATURE,
        settings.BASE_MODEL_MAX_INPUT_TOKENS,
        settings.BASE_MODEL_MAX_OUTPUT_TOKENS,
        settings.BASE_MODEL_TEMPERATURE,
        settings.OPENAI_FORMAT_API_KEY,
        settings.OPENAI_FORMAT_BASE_URL,
        settings.ANTHROPIC_API_KEY,
        settings.GEMINI_API_KEY,
    )

    # Test base model
    chat_model = llm_service.base_model
    print(f"\nTesting model Base Model: {settings.BASE_MODEL}")

    # Run a simple chat generation
    response = chat_model.invoke([HumanMessage(content="Hello! Tell me a fun fact about space.")])
    print("Response:", response.content)

    # Test advanced model
    chat_model = llm_service.advanced_model
    print(f"\nTesting model Advanced Model: {settings.ADVANCED_MODEL}")
    # Run a simple chat generation
    response = chat_model.invoke([HumanMessage(content="Hello! Tell me a fun fact about space.")])
    print("Response:", response.content)
    print("Test completed successfully!")


if __name__ == "__main__":
    test_model_response()
