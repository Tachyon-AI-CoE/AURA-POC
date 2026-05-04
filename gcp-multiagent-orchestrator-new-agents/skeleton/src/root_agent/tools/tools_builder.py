from typing import List, Optional, Dict, Any, Union
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval
from root_agent.tools.rag_tool import create_rag_tool_from_yaml_config
from utils.log_helper import setup_logging

logger = setup_logging()


class ToolsBuilder:
    """Centralized builder class for creating various tools from YAML configuration."""

    def __init__(self):
        self._tools: List[Any] = []
        self._global_config: Optional[Dict[str, Any]] = None

    def set_global_config(self, global_config: Dict[str, Any]) -> "ToolsBuilder":
        """Set global configuration for tools that need project_id, location, etc."""
        self._global_config = global_config
        return self

    def add_tool(self, tool: Any) -> "ToolsBuilder":
        """Add a single tool to the collection."""
        if tool:
            self._tools.append(tool)
        return self

    def add_tools(self, tools: List[Any]) -> "ToolsBuilder":
        """Add multiple tools to the collection."""
        valid_tools = [tool for tool in tools if tool is not None]
        self._tools.extend(valid_tools)
        return self

    def clear_tools(self) -> "ToolsBuilder":
        """Clear all tools from the collection."""
        self._tools.clear()
        return self

    def create_rag_tool(
        self, rag_tool_config: Dict[str, Any], agent_name: str = None
    ) -> Optional[VertexAiRagRetrieval]:
        """
        Create a RAG tool from YAML tool configuration using functional approach.

        Args:
            rag_tool_config: RAG tool configuration from YAML
            agent_name: Name of the agent (for logging purposes)

        Returns:
            Configured VertexAiRagRetrieval tool or None if creation fails
        """
        try:
            # Use the functional approach to create RAG tools
            rag_tool = create_rag_tool_from_yaml_config(
                rag_tool_config, self._global_config, agent_name
            )
            return rag_tool
        except Exception as e:
            logger.warning(
                f"Failed to create RAG tool '{rag_tool_config.get('name', 'unnamed')}' for agent {agent_name}: {e}"
            )
            return None

    def create_mcp_tool(
        self, mcp_tool_config: Dict[str, Any], agent_name: str = None
    ) -> Optional[Any]:
        """
        Create an MCP tool from YAML tool configuration.

        Args:
            mcp_tool_config: MCP tool configuration from YAML
            agent_name: Name of the agent (for logging purposes)

        Returns:
            Configured MCP tool or None if creation fails or not implemented
        """
        try:
            # TODO: Implement MCP tool creation when MCP tools are available
            logger.info(
                f"MCP tool '{mcp_tool_config.get('name', 'unnamed')}' configured but not implemented yet for agent {agent_name}"
            )
            return None
        except Exception as e:
            logger.warning(
                f"Failed to create MCP tool '{mcp_tool_config.get('name', 'unnamed')}' for agent {agent_name}: {e}"
            )
            return None

    def create_custom_tool(
        self, tool_config: Dict[str, Any], agent_name: str = None
    ) -> Optional[Any]:
        """
        Create a custom tool from YAML tool configuration.

        Args:
            tool_config: Custom tool configuration from YAML
            agent_name: Name of the agent (for logging purposes)

        Returns:
            Configured custom tool or None if creation fails
        """
        try:
            # TODO: Implement custom tool creation based on tool type
            tool_type = tool_config.get("type", "unknown")
            logger.info(
                f"Custom tool of type '{tool_type}' configured but not implemented yet for agent {agent_name}"
            )
            return None
        except Exception as e:
            logger.warning(
                f"Failed to create custom tool '{tool_config.get('name', 'unnamed')}' for agent {agent_name}: {e}"
            )
            return None

    def build_tools_from_yaml_config(
        self, tools_config: Dict[str, Any], agent_name: str = None
    ) -> "ToolsBuilder":
        """
        Build all tools from YAML tools configuration.

        Args:
            tools_config: Tools configuration dictionary from YAML
            agent_name: Name of the agent (for logging purposes)

        Returns:
            Self for method chaining
        """
        if not tools_config:
            return self

        # Handle RAG tools
        rag_tools_config = tools_config.get("rag", [])
        for rag_tool_config in rag_tools_config:
            rag_tool = self.create_rag_tool(rag_tool_config, agent_name)
            if rag_tool:
                self.add_tool(rag_tool)

        # Handle MCP tools
        mcp_tools_config = tools_config.get("mcp", [])
        for mcp_tool_config in mcp_tools_config:
            mcp_tool = self.create_mcp_tool(mcp_tool_config, agent_name)
            if mcp_tool:
                self.add_tool(mcp_tool)

        # Handle custom tools
        custom_tools_config = tools_config.get("custom", [])
        for custom_tool_config in custom_tools_config:
            custom_tool = self.create_custom_tool(custom_tool_config, agent_name)
            if custom_tool:
                self.add_tool(custom_tool)

        # Handle any other tool types that might be added in the future
        for tool_type, tool_configs in tools_config.items():
            if tool_type not in ["rag", "mcp", "custom"]:
                logger.info(
                    f"Unknown tool type '{tool_type}' found in configuration for agent {agent_name}"
                )

        return self

    def get_tools(self) -> List[Any]:
        """Get all built tools."""
        return self._tools.copy()

    def get_tool_count(self) -> int:
        """Get the number of tools built."""
        return len(self._tools)

    def has_tools(self) -> bool:
        """Check if any tools have been built."""
        return len(self._tools) > 0

    def reset(self) -> "ToolsBuilder":
        """Reset the builder to initial state."""
        self._tools.clear()
        self._global_config = None
        return self


# Convenience functions for creating tools
def create_tools_from_yaml_config(
    tools_config: Dict[str, Any],
    global_config: Optional[Dict[str, Any]] = None,
    agent_name: str = None,
) -> List[Any]:
    """
    Convenience function to create all tools from YAML configuration.

    Args:
        tools_config: Tools configuration dictionary from YAML
        global_config: Global configuration dictionary (for project_id, location, etc.)
        agent_name: Name of the agent (for logging purposes)

    Returns:
        List of configured tools
    """
    builder = ToolsBuilder()
    if global_config:
        builder.set_global_config(global_config)

    builder.build_tools_from_yaml_config(tools_config, agent_name)
    return builder.get_tools()


def create_rag_tools_from_yaml_config(
    rag_tools_config: List[Dict[str, Any]],
    global_config: Optional[Dict[str, Any]] = None,
    agent_name: str = None,
) -> List[VertexAiRagRetrieval]:
    """
    Convenience function to create RAG tools from YAML configuration.

    Args:
        rag_tools_config: List of RAG tool configurations from YAML
        global_config: Global configuration dictionary (for project_id, location, etc.)
        agent_name: Name of the agent (for logging purposes)

    Returns:
        List of configured RAG tools
    """
    tools = []
    for rag_tool_config in rag_tools_config:
        rag_tool = create_rag_tool_from_yaml_config(
            rag_tool_config, global_config, agent_name
        )
        if rag_tool:
            tools.append(rag_tool)

    return tools


def create_mcp_tools_from_yaml_config(
    mcp_tools_config: List[Dict[str, Any]],
    global_config: Optional[Dict[str, Any]] = None,
    agent_name: str = None,
) -> List[Any]:
    """
    Convenience function to create MCP tools from YAML configuration.

    Args:
        mcp_tools_config: List of MCP tool configurations from YAML
        global_config: Global configuration dictionary
        agent_name: Name of the agent (for logging purposes)

    Returns:
        List of configured MCP tools
    """
    tools = []
    for mcp_tool_config in mcp_tools_config:
        # TODO: Implement MCP tool creation when available
        logger.info(
            f"MCP tool '{mcp_tool_config.get('name', 'unnamed')}' configured but not implemented yet for agent {agent_name}"
        )

    return tools


# Tool factory function
def create_tool_by_type(
    tool_type: str,
    tool_config: Dict[str, Any],
    global_config: Optional[Dict[str, Any]] = None,
    agent_name: str = None,
) -> Optional[Any]:
    """
    Factory function to create a tool by type.

    Args:
        tool_type: Type of tool to create ('rag', 'mcp', 'custom')
        tool_config: Tool configuration dictionary
        global_config: Global configuration dictionary
        agent_name: Name of the agent (for logging purposes)

    Returns:
        Configured tool or None if creation fails
    """
    if tool_type == "rag":
        return create_rag_tool_from_yaml_config(tool_config, global_config, agent_name)
    elif tool_type == "mcp":
        # TODO: Implement MCP tool creation when available
        logger.info(
            f"MCP tool type requested but not implemented yet for agent {agent_name}"
        )
        return None
    elif tool_type == "custom":
        # TODO: Implement custom tool creation
        logger.info(
            f"Custom tool type requested but not implemented yet for agent {agent_name}"
        )
        return None
    else:
        logger.warning(f"Unknown tool type '{tool_type}' for agent {agent_name}")
        return None


# Example usage:
"""
# Example YAML tools configuration:
tools_config = {
    'rag': [
        {
            'name': 'VertexAI_RAG_Tool',
            'description': 'A tool to retrieve information from a knowledge base using RAG.',
            'config': {
                'rag_resource': ['corpus_id_1', 'corpus_id_2'],
                'vector_distance_threshold': 0.8,
                'similarity_top_k': 10
            }
        }
    ],
    'mcp': [
        {
            'name': 'MCP_Tool',
            'description': 'A tool to interact with the MCP system.',
            'config': {
                'server_url': 'https://your-mcp-endpoint.com/api'
            }
        }
    ]
}

global_config = {
    'project_id': 'your-project-id',
    'location': 'us-central1'
}

# Create all tools
tools = create_tools_from_yaml_config(tools_config, global_config, 'test_agent')

# Create only RAG tools
rag_tools = create_rag_tools_from_yaml_config(tools_config['rag'], global_config, 'test_agent')

# Create a single tool by type
single_tool = create_tool_by_type('rag', tools_config['rag'][0], global_config, 'test_agent')
"""
