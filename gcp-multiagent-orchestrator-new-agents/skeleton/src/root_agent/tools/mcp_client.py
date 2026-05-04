from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from typing import Dict, Any, Optional
from utils.log_helper import setup_logging
logger = setup_logging()


class DeployableMcpToolset(McpToolset):

    def __deepcopy__(self, memo):
        new_obj = DeployableMcpToolset(connection_params=self._connection_params)

        # Copy all attributes from both __dict__ and Pydantic private storage.
        all_attrs = set(self.__dict__) | set(getattr(self, '__pydantic_private__', None) or {})
        for attr in all_attrs:
            try:
                setattr(new_obj, attr, getattr(self, attr))
            except Exception:
                pass

        # Guarantee known auth attributes survive — they may be absent on self
        # if lost during unpickling (setattr-assigned, not a Pydantic field).
        for attr in ("_auth_config", "_use_mcp_resources"):
            if not hasattr(new_obj, attr):
                try:
                    setattr(new_obj, attr, getattr(self, attr, None))
                except Exception:
                    pass

        return new_obj

def create_http_connection_params(
    url: str, headers: Optional[Dict[str, str]] = None
) -> StreamableHTTPConnectionParams:
    """Create HTTP connection parameters."""
    if not url:
        raise ValueError("❌ URL is required for HTTP connection")

    return StreamableHTTPConnectionParams(url=url, headers=headers or {}, errlog=None)


def create_bearer_auth_headers(token: str) -> Dict[str, str]:
    """Create headers with Bearer authentication."""
    return {"Authorization": f"Bearer {token}"}


def merge_headers(*header_dicts: Optional[Dict[str, str]]) -> Dict[str, str]:
    """Merge multiple header dictionaries."""
    merged_headers = {}
    for headers in header_dicts:
        if headers:
            merged_headers.update(headers)
    return merged_headers


def create_http_mcp_toolset(
    url: str, auth_token: Optional[str] = None, headers: Optional[Dict[str, str]] = None
) -> DeployableMcpToolset:
    """Create an HTTP MCP toolset with optional bearer authentication."""
    auth_headers = create_bearer_auth_headers(auth_token) if auth_token else {}
    final_headers = merge_headers(auth_headers, headers)

    connection_params = create_http_connection_params(url, final_headers)
    toolset = DeployableMcpToolset(connection_params=connection_params)
    # Attach a minimal auth config expected by downstream code. Keep shape simple.
    try:
        setattr(toolset, "_auth_config", {"auth_token": auth_token} if auth_token else {})
    except Exception as e:
        logger.warning(f"Failed to attach '_auth_config' to MCPToolset: {e}")
    return toolset


def create_mcp_toolset_from_config(config: Dict[str, Any]) -> MCPToolset:
    """Create an MCPToolset from a configuration dictionary."""
    # Handle direct connection_params
    if "connection_params" in config:
        return MCPToolset(connection_params=config["connection_params"])

    # Handle HTTP connection configuration
    if "url" not in config:
        raise ValueError(
            "❌ Either 'connection_params' or 'url' must be provided in config"
        )

    url = config["url"]
    headers = config.get("headers", {})

    # Handle various auth token keys
    auth_token = config.get("auth_token") or config.get("bearer_token")

    return create_http_mcp_toolset(url, auth_token, headers)


def create_mcp_toolset_with_connection_params(
    connection_params: StreamableHTTPConnectionParams,
) -> MCPToolset:
    """Create an MCPToolset with pre-built connection parameters."""
    return MCPToolset(connection_params=connection_params)


# Example configuration dictionaries:
http_mcp_config = {
    "url": "https://your-mcp-server-url.run.app/mcp",
    "auth_token": "your-auth-token",
}

http_mcp_with_headers_config = {
    "url": "https://your-mcp-server-url.run.app/mcp",
    "headers": {
        "Authorization": "Bearer your-auth-token",
        "Content-Type": "application/json",
        "X-API-Version": "v1",
    },
}

# Usage examples:
# toolset1 = create_mcp_toolset_from_config(http_mcp_config)
# toolset2 = create_mcp_toolset_from_config(http_mcp_with_headers_config)
# toolset3 = create_http_mcp_toolset("https://example.com/mcp", "your-token")


# Direct usage:
def create_example_toolset() -> MCPToolset:
    """Create an example toolset."""
    return create_http_mcp_toolset(
        url="https://your-mcp-server-url.run.app/mcp", auth_token="your-auth-token"
    )


# Alternative using dictionary config:
toolset = create_mcp_toolset_from_config(http_mcp_config)
