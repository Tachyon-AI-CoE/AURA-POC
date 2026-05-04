import os
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from utils.log_helper import setup_logging

logger = setup_logging()


class DeployableMCPToolset(McpToolset):

    def __deepcopy__(self, memo):
        new_obj = DeployableMCPToolset(connection_params=self._connection_params)

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


def load_mcp_toolset():
    """Initialize and return MCP toolset if configured, otherwise return None."""
    try:
        mcp_url = os.getenv("MCP_SERVER_URL")
        if not mcp_url or mcp_url.strip() == "":
            logger.info("MCP_SERVER_URL not configured, skipping MCP toolset initialization")
            return None

        toolset = DeployableMCPToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=mcp_url, errlog=None
            )
        )
        logger.info("MCP toolset initialized successfully")
        return toolset

    except Exception as e:
        logger.error(f"Failed to initialize MCP toolset: {e}")
        logger.warning("Continuing without MCP toolset")
        return None
