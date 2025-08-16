from mcp.server.fastmcp import FastMCP
import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

import yaml
from langchain_mcp_adapters.client import MultiServerMCPClient


# ==========================================
# MCP Server (existing behavior preserved)
# ==========================================
# Create unified MCP server instance
mcp = FastMCP("PrometheusTools")


# ==========================================
# Dynamic MCP client based on node_tools.yml
# ==========================================
_NODE_TOOLS_CACHE: Optional[Dict[str, List[str]]] = None
_CLIENT_CACHE: Optional[MultiServerMCPClient] = None


def _load_node_tools_map(config_path: Optional[Path] = None) -> Dict[str, List[str]]:
    """Load node->tools mapping from prometheus/graph_config/node_tools.yml.

    Returns a dict: { node_name: [tool_name, ...] }
    """
    global _NODE_TOOLS_CACHE
    if _NODE_TOOLS_CACHE is not None:
        return _NODE_TOOLS_CACHE

    if config_path is None:
        # mcp_server.py is in prometheus/tools/, go up one to prometheus/
        project_root = Path(__file__).resolve().parents[1]
        config_path = project_root / "graph_config" / "node_tools.yml"

    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    nodes = data.get("nodes", [])
    node_to_tools: Dict[str, List[str]] = {}
    for item in nodes:
        name = item.get("name")
        tools = item.get("tools", []) or []
        if name is None:
            continue
        if isinstance(tools, list):
            node_to_tools[name] = tools
        else:
            # In case of malformed YAML (non-list), coerce to list
            node_to_tools[name] = [tools]

    _NODE_TOOLS_CACHE = node_to_tools
    return node_to_tools


def _load_server_configs() -> Dict[str, Dict[str, Any]]:
    """Load MCP server configurations from environment.

    Expected env var PROMETHEUS_MCP_SERVERS as JSON, e.g.:
    {
      "math": {
        "command": "python",
        "args": ["/abs/path/to/examples/math_server.py"],
        "transport": "stdio"
      },
      "weather": {
        "url": "http://localhost:8000/mcp/",
        "transport": "streamable_http"
      }
    }

    If not provided, default to spawning this file as a stdio MCP server under id "PrometheusTools".
    """
    raw = os.getenv("PROMETHEUS_MCP_SERVERS")
    if raw:
        try:
            cfg = json.loads(raw)
            if isinstance(cfg, dict):
                return cfg
        except json.JSONDecodeError:
            pass

    # Fallback: local stdio server using this file
    this_file = Path(__file__).resolve()
    return {
        "PrometheusTools": {
            "command": "python",
            "args": [str(this_file)],
            "transport": "stdio",
        }
    }


def _build_client(server_configs: Optional[Dict[str, Dict[str, Any]]] = None) -> MultiServerMCPClient:
    global _CLIENT_CACHE
    if _CLIENT_CACHE is not None:
        return _CLIENT_CACHE

    if server_configs is None:
        server_configs = _load_server_configs()

    client = MultiServerMCPClient(server_configs)
    _CLIENT_CACHE = client
    return client


async def get_all_tools() -> List[Any]:
    """Fetch all tools from all configured MCP servers."""
    client = _build_client()
    tools = await client.get_tools()
    return tools


def get_required_tool_names_for_node(node_name: str) -> List[str]:
    mapping = _load_node_tools_map()
    return mapping.get(node_name, [])


async def get_tools_for_node(node_name: str) -> List[Any]:
    """Return the list of MCP tools required by the given node name.

    This will connect to all configured MCP servers, fetch their tools, and filter
    by the names listed for the node in node_tools.yml.
    """
    required: Set[str] = set(get_required_tool_names_for_node(node_name))
    if not required:
        return []
    all_tools = await get_all_tools()
    return [t for t in all_tools if getattr(t, "name", None) in required]


def build_default_node_tool_client() -> MultiServerMCPClient:
    """Expose a builder for external callers if needed."""
    return _build_client()


if __name__ == "__main__":
    # 确保在启动前注册所有工具
    sys.path.append("~/lix/Prometheus")
    import prometheus.tools  # noqa: F401
    mcp.run(transport="stdio")

    async def main():
        tools = await get_all_tools()
        for t in sorted(tools, key=lambda x: getattr(x, "name", "")):
            print(getattr(t, "name", str(t)))

    asyncio.run(main())
