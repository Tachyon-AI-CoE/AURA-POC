"""Agent Configuration Generator - Merges agents.json with root-agent-config.yaml."""

import json
import os
from typing import Any, Dict, List, Optional
import yaml

from utils.log_helper import setup_logging
logger = setup_logging()

def load_agents_from_json(json_file_path: str) -> List[Dict[str, Any]]:
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            agents = json.load(f)
        logger.info(
            f"✅ Successfully loaded {len(agents)} agents from {json_file_path}"
        )
        return agents
    except FileNotFoundError:
        logger.error(f"❌ File not found: {json_file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"❌ Error decoding JSON from {json_file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error loading agents from JSON: {e}")
        raise


def load_root_agent_config(yaml_file_path: str) -> Dict[str, Any]:
    try:
        with open(yaml_file_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        logger.info(f"✅ Successfully loaded root agent config from {yaml_file_path}")
        return config
    except FileNotFoundError:
        logger.error(f"❌ File not found: {yaml_file_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"❌ Error parsing YAML from {yaml_file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error loading root agent config: {e}")
        raise


def transform_rag_config(tools: Dict[str, Any]) -> List[Dict[str, Any]]:
    if "rag" not in tools:
        return []

    rag_config = tools.get("rag", [])

    # Ensure rag_config is a list, if not make it a list
    if not isinstance(rag_config, list):
        rag_config = [rag_config]

    transformed_rag = []
    for rag_item in rag_config:
        rag_entry = {}

        # Extract RAG configuration
        # Expected format: {"rag_details": {"value": {"datasetname": "...", "vectorizeddatasetbaseid": "...", "description": "..."}}, ...}

        rag_name_value = ""
        vectorized_dataset_base_id = ""
        description = ""

        # Extract from rag_details object
        if "rag_details" in rag_item and isinstance(rag_item["rag_details"], dict):
            rag_details = rag_item["rag_details"]
            if "value" in rag_details and isinstance(rag_details["value"], dict):
                value_obj = rag_details["value"]
                rag_name_value = value_obj.get("datasetname", "")
                vectorized_dataset_base_id = value_obj.get(
                    "vectorizeddatasetbaseid", ""
                )
                description = value_obj.get("description", "")
        else:
            logger.warning(
                f"⚠️ RAG item missing 'rag_details' object or invalid format: {rag_item}"
            )

        rag_entry["name"] = rag_name_value

        # Add description if provided
        if description:
            rag_entry["description"] = description

        # Create config section
        rag_entry["config"] = {}

        # Handle resource_id - use vectorizeddatasetbaseid if available
        resource_id = rag_item.get("resource_id", "")
        if not resource_id and vectorized_dataset_base_id:
            resource_id = vectorized_dataset_base_id
            logger.info(
                f"✅ Using vectorizeddatasetbaseid as resource ID for RAG '{rag_name_value}': {resource_id}"
            )
        elif not resource_id:
            logger.warning(
                f"⚠️ No resource_id or vectorizeddatasetbaseid found for RAG '{rag_name_value}', using empty string"
            )

        # Create rag_resources list with the resource_id
        if resource_id:
            rag_entry["config"]["rag_resources"] = [{"rag_resource": resource_id}]
        else:
            rag_entry["config"]["rag_resources"] = []

        # Copy other rag fields into config
        if "vector_distance_threshold" in rag_item:
            rag_entry["config"]["vector_distance_threshold"] = rag_item[
                "vector_distance_threshold"
            ]
        if "similarity_top_k" in rag_item:
            rag_entry["config"]["similarity_top_k"] = rag_item["similarity_top_k"]

        transformed_rag.append(rag_entry)

    return transformed_rag


def transform_mcp_config(tools: Dict[str, Any]) -> List[Dict[str, Any]]:
    if "mcp" not in tools:
        return []

    mcp_config = tools.get("mcp", {})

    # Check if mcp_config is a dict with mcp_servers or already a list
    if isinstance(mcp_config, dict) and "mcp_servers" in mcp_config:
        # Old format: {"mcp_servers": ["server1", "server2"]}
        # Convert to new format with full server configuration
        mcp_servers = mcp_config.get("mcp_servers", [])
        transformed_mcp = []
        for server_name in mcp_servers:
            # Retrieve server configuration from external source
            logger.info(
                f"🔍 Retrieving MCP server configuration for '{server_name}'..."
            )
            server_config = get_mcp_server_config(server_name)
            if server_config:
                transformed_mcp.append(server_config)
            else:
                logger.warning(
                    f"⚠️ Could not retrieve configuration for MCP server '{server_name}', skipping"
                )
        return transformed_mcp
    elif isinstance(mcp_config, list):
        # New format: already a list of server configurations
        return mcp_config
    else:
        # Fallback to empty list
        return []


def transform_agent_for_yaml(agent: Dict[str, Any]) -> Dict[str, Any]:
    """Transform agent configuration from JSON to YAML format."""
    # Start with name as the first field
    transformed = {}

    # Add name first if it exists
    if "name" in agent:
        transformed["name"] = agent["name"]

    # Fields to exclude from the output
    exclude_fields = [
        "model_id",
        "tools",
        "sub_agents",
        "name",
        "show_advanced_options",
        "show_sub_agent_advanced",
    ]

    # Copy all other top-level fields except ones we'll handle specially
    for key, value in agent.items():
        if key not in exclude_fields:
            transformed[key] = value

    # Handle model_id - extract value if it's a dict
    model_id = agent.get("model_id", {})
    if isinstance(model_id, dict):
        transformed["model_id"] = model_id.get("value", "gemini-2.0-flash-001")
    else:
        transformed["model_id"] = model_id or "gemini-2.0-flash-001"

    # Handle tools configuration
    tools = agent.get("tools", {})
    if tools:
        transformed["tools"] = {}

        # Copy enabled_tools if present
        if "enabled_tools" in tools:
            transformed["tools"]["enabled_tools"] = tools["enabled_tools"]

        if ("rag" in tools and 
            tools["rag"].get("rag_details", {}) != {} and 
            "RAG" in tools.get("enabled_tools", [])):
            # Handle RAG tool using dedicated transformation method
            rag_transformed = transform_rag_config(tools)
            if rag_transformed:
                transformed["tools"]["rag"] = rag_transformed

        if ("mcp" in tools and 
            tools["mcp"].get("mcp_servers", []) != [None] and 
            "MCP" in tools.get("enabled_tools", [])):
            # Handle MCP tool using dedicated transformation method
            mcp_transformed = transform_mcp_config(tools)
            if mcp_transformed:
                transformed["tools"]["mcp"] = mcp_transformed

    # Handle sub-agents (recursive transformation)
    if agent.get("sub_agents"):
        transformed["sub_agents"] = []
        for sub_agent in agent.get("sub_agents", []):
            transformed_sub_agent = transform_agent_for_yaml(sub_agent)
            transformed["sub_agents"].append(transformed_sub_agent)

    return transformed


def merge_agents_to_root_config(
    root_config: Dict[str, Any], agents: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Merge agents from JSON into the root agent configuration."""
    merged_config = root_config.copy()

    # Ensure the 'agents' key exists in root_agent
    if "root_agent" not in merged_config:
        merged_config["root_agent"] = {}

    # Ensure agents is a list (handle None or missing key)
    if "agents" not in merged_config or merged_config["agents"] is None:
        merged_config["agents"] = []

    # Transform and add each agent
    for agent in agents:
        transformed_agent = transform_agent_for_yaml(agent)
        merged_config["agents"].append(transformed_agent)

    logger.info(f"✅ Merged {len(agents)} agents into root configuration")
    return merged_config


def save_agent_config_yaml(config: Dict[str, Any], output_file_path: str) -> bool:
    """Save the merged agent configuration to a YAML file."""
    try:
        # Create a custom YAML dumper with proper indentation settings
        class CustomDumper(yaml.SafeDumper):
            def increase_indent(self, flow=False, indentless=False):
                return super(CustomDumper, self).increase_indent(flow, False)

        def dict_representer(dumper, data):
            return dumper.represent_mapping("tag:yaml.org,2002:map", data.items())

        def list_representer(dumper, data):
            return dumper.represent_sequence("tag:yaml.org,2002:seq", data)

        CustomDumper.add_representer(dict, dict_representer)
        CustomDumper.add_representer(list, list_representer)

        with open(output_file_path, "w", encoding="utf-8") as f:
            yaml.dump(
                config,
                f,
                Dumper=CustomDumper,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
                indent=2,
                width=float("inf"),  # Prevent line wrapping
            )
        logger.info(f"✅ Successfully saved agent configuration to {output_file_path}")
        return True
    except Exception as e:
        logger.error(f"❌ Error saving agent configuration to YAML: {e}")
        raise


def generate_agent_config(
    agents_json_path: str = "agents.json",
    root_config_yaml_path: str = "root-agent-config.yaml",
    output_yaml_path: str = "agent-config.yaml",
) -> bool:
    """Generate agent-config.yaml by merging agents.json with root-agent-config.yaml."""
    logger.info("🚀 Starting agent configuration generation...")

    # Load agents from JSON
    agents = load_agents_from_json(agents_json_path)
    if not agents:
        logger.error("❌ No agents loaded from JSON file. Aborting.")
        return False

    # Load root agent configuration
    root_config = load_root_agent_config(root_config_yaml_path)
    if not root_config:
        logger.error("❌ Failed to load root agent configuration. Aborting.")
        return False

    # Merge agents into root configuration
    merged_config = merge_agents_to_root_config(root_config, agents)

    # Save to output file
    success = save_agent_config_yaml(merged_config, output_yaml_path)

    if success:
        logger.info("✅ Agent configuration generation completed successfully!")
    else:
        logger.error("❌ Agent configuration generation failed.")

    return success


def get_mcp_server_config(server_name: str) -> Optional[Dict[str, Any]]:
    """Retrieve MCP server configuration from an external source."""
    try:
        # TODO: Implement actual logic to retrieve MCP server configuration

        logger.info(f"🔍 Retrieving configuration for MCP server '{server_name}'...")

        # Placeholder: Return a default configuration
        # In production, this should query a database or configuration service
        default_config = {
            "name": server_name,
            "description": f"A tool to interact with the {server_name} MCP system.",
            "tool_filter": [],
            "config": {"server_url": f""},
        }

        logger.info(
            f"✅ Generated default configuration for MCP server '{server_name}'"
        )
        return default_config

        # fectch the MCP server configuration

    except Exception as e:
        logger.error(
            f"❌ Error retrieving configuration for MCP server '{server_name}': {e}"
        )
        raise


if __name__ == "__main__":
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Define file paths relative to the script directory
    agents_json = os.path.join(script_dir, "agents.json")
    root_config_yaml = os.path.join(script_dir, "root-agent-config.yaml")
    output_yaml = os.path.join(script_dir, "agent-config.yaml")

    # Generate the agent configuration
    generate_agent_config(agents_json, root_config_yaml, output_yaml)
