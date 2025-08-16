
# Ensure MCP tools are registered when this package is imported by the MCP server
# Importing the module executes the @mcp.tool decorators
from prometheus.mcp_tools import web_search as _mcp_web_search  # noqa: F401

