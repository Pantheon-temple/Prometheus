import os
import shutil
from pathlib import Path
from typing import Annotated
import json
import asyncio
from dynaconf.vendor.dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator
from mcp.server import Server
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData
from mcp.server.stdio import stdio_server
from mcp.types import (
    GetPromptResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    TextContent,
    Tool,
    INVALID_PARAMS,
    INTERNAL_ERROR,
)
from tavily import TavilyClient, InvalidAPIKeyError, UsageLimitExceededError
from prometheus.configuration.config import settings
from prometheus.utils.logger_manager import get_logger

logger = get_logger(__name__)


tavily_api_key = settings.get("TAVILY_API_KEY", None)
if tavily_api_key is None:
    logger.warning("Tavily API key is not set")
    tavily_client = None
else:
    tavily_client = TavilyClient(api_key=tavily_api_key)


class WebSearchInput(BaseModel):
    """Base parameters for Tavily search."""
    query: Annotated[str, Field(description="Search query")]

WEB_SEARCH_DESCRIPTION = """\
    Searches the web for technical information to aid in bug analysis and resolution. 
    Use this when you need external context, such as: 
    1. Looking up unfamiliar error messages, exceptions, or stack traces. 
    2. Finding official documentation or usage examples for a specific library, framework, or API. 
    3. Searching for known bugs, common pitfalls, or compatibility issues related to a software version. 
    4. Learning the best practices or design patterns for fixing a class of vulnerability (e.g., SQL injection, XSS). 
    
    Queries should be specific and include relevant keywords like library names, version numbers, and error codes.
"""

def format_results(response: dict) -> str:
        """Format Tavily search results into a readable string."""
        output = []
        
        # Add domain filter information if present
        if response.get("included_domains") or response.get("excluded_domains"):
            filters = []
            if response.get("included_domains"):
                filters.append(f"Including domains: {', '.join(response['included_domains'])}")
            if response.get("excluded_domains"):
                filters.append(f"Excluding domains: {', '.join(response['excluded_domains'])}")
            output.append("Search Filters:")
            output.extend(filters)
            output.append("")  # Empty line for separation
        
        if response.get("answer"):
            output.append(f"Answer: {response['answer']}")
            output.append("\nSources:")
            # Add immediate source references for the answer
            for result in response["results"]:
                output.append(f"- {result['title']}: {result['url']}")
            output.append("")  # Empty line for separation
        
        output.append("Detailed Results:")
        for result in response["results"]:
            output.append(f"\nTitle: {result['title']}")
            output.append(f"URL: {result['url']}")
            output.append(f"Content: {result['content']}")
            if result.get("published_date"):
                output.append(f"Published: {result['published_date']}")
            
        return "\n".join(output)



def web_search(query: str, 
        max_results: int = 5, 
        include_domains: list[str] = [
            'stackoverflow.com', 
            'github.com', 
            'developer.mozilla.org', 
            'learn.microsoft.com', 
            'docs.python.org', 
            'pydantic.dev',
            'pypi.org',
            'readthedocs.org',
        ], 
        exclude_domains: list[str] = None) -> str:
    """
    Search the web for technical information to aid in bug analysis and resolution.
    """
    if tavily_client is None:
        raise McpError(ErrorData(
            code=INTERNAL_ERROR,
            message="Tavily API key is not set"
        ))
    try:
        response = tavily_client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",
            include_answer=True,
            include_domains=include_domains or [],  # Convert None to empty list
            exclude_domains=exclude_domains or [],  # Convert None to empty list
        )
        return format_results(response)
    except InvalidAPIKeyError: 
        raise McpError(ErrorData(
            code=INVALID_PARAMS,
            message="Invalid Tavily API key"
        ))
    except UsageLimitExceededError:
        raise McpError(ErrorData(
            code=INTERNAL_ERROR,
            message="Usage limit exceeded"
        ))
    except Exception as e:
        raise McpError(ErrorData(
            code=INTERNAL_ERROR,
            message=f"An error occurred: {str(e)}"
        ))




if __name__ == "__main__":
    load_dotenv()
    tavily_api_key = os.getenv("PROMETHEUS_TAVILY_API_KEY")
    if tavily_api_key is None:
        logger.warning("Tavily API key is not set")
        tavily_client = None
    else:
        tavily_client = TavilyClient(api_key=tavily_api_key)

    print(web_search("What is the capital of France?")) 