"""Initializes and configures all prometheus services."""

from prometheus.app.services.base_service import BaseService
from prometheus.app.services.database_service import DatabaseService
from prometheus.app.services.issue_service import IssueService
from prometheus.app.services.knowledge_graph_service import KnowledgeGraphService
from prometheus.app.services.llm_service import LLMService
from prometheus.app.services.neo4j_service import Neo4jService
from prometheus.app.services.repository_service import RepositoryService
from prometheus.app.services.user_service import UserService
from prometheus.configuration.config import settings


def initialize_services() -> dict[str, BaseService]:
    """Initializes and configures the complete prometheus service stack.

    This function creates and configures all required services for prometheus
    operation, using settings from the configuration module. It ensures proper
    initialization order and service dependencies.

    Note:
        This function assumes all required settings are properly configured in
        the settings module using Dynaconf. The following settings are required:
        - NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
        - LITELLM_MODEL
        - NEO4J_BATCH_SIZE
        - KNOWLEDGE_GRAPH_MAX_AST_DEPTH
        - WORKING_DIRECTORY
        - GITHUB_ACCESS_TOKEN

    Returns:
        A fully configured ServiceCoordinator instance managing all services.
    """
    neo4j_service = Neo4jService(
        settings.NEO4J_URI, settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD
    )
    database_service = DatabaseService(settings.DATABASE_URL)
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
    knowledge_graph_service = KnowledgeGraphService(
        neo4j_service,
        settings.NEO4J_BATCH_SIZE,
        settings.KNOWLEDGE_GRAPH_MAX_AST_DEPTH,
        settings.KNOWLEDGE_GRAPH_CHUNK_SIZE,
        settings.KNOWLEDGE_GRAPH_CHUNK_OVERLAP,
    )
    repository_service = RepositoryService(
        knowledge_graph_service, database_service, settings.WORKING_DIRECTORY
    )
    issue_service = IssueService(
        neo4j_service,
        repository_service,
        llm_service,
        settings.MAX_TOKEN_PER_NEO4J_RESULT,
        settings.WORKING_DIRECTORY,
        settings.LOGGING_LEVEL,
    )

    user_service = UserService(database_service)

    return {
        "neo4j_service": neo4j_service,
        "llm_service": llm_service,
        "knowledge_graph_service": knowledge_graph_service,
        "repository_service": repository_service,
        "issue_service": issue_service,
        "database_service": database_service,
        "user_service": user_service,
    }
