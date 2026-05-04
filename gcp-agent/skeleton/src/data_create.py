"""
GCP Vertex AI Agent Creation Client
This module provides a client for creating agents via the GCP AI Enterprise Portal API.
"""

import json
import os
import sys
import argparse
import requests
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from dotenv import load_dotenv
from utils.log_helper import setup_logging

# Load environment variables from .env file
load_dotenv()
logger = setup_logging()

from config.config import (
    # Values from JSON config file
    DATA_APP_API_URL,
    CLOUDRUN_SERVICE_URL,
    AGENT_DISPLAY_NAME,
    SYSTEM_INSTRUCTION,
    MODEL_NAME,
    REGION,
    GUARDRAIL_NAME,
    GROUNDTRUTH_NAME,
    GENERAL_GROUNDTRUTH_NAME
)

# Validate required environment variables
if not DATA_APP_API_URL:
    raise ValueError("DATA_APP_API_URL environment variable is required but not set")
if not CLOUDRUN_SERVICE_URL:
    raise ValueError("CLOUDRUN_SERVICE_URL environment variable is required but not set")

# Extract values from configuration
agent_name = AGENT_DISPLAY_NAME
agent_instruction = SYSTEM_INSTRUCTION
model_name = MODEL_NAME
region_name = REGION
guardrail_name = GUARDRAIL_NAME
groundtruth_name = GROUNDTRUTH_NAME
general_groundtruth_name = GENERAL_GROUNDTRUTH_NAME



def _get_dataset_name(filepath):
    if os.path.exists(filepath):
        # Read the JSON file
        with open(filepath, 'r') as file:
            config = json.load(file)

        # Loop through each agent in the data array
        for rag_item in config:
            if "rag_details" not in rag_item or "value" not in rag_item["rag_details"] or "datasetname" not in rag_item["rag_details"]["value"]:
                logger.warning("RAG details or datasetname missing in configuration.")
                continue
            datasetname = rag_item["rag_details"]["value"]["datasetname"]
            return datasetname
    return ""

dataset_name = _get_dataset_name("rag_configuration.json")
def _extract_and_store_gcspaths(response_data: dict):
    """Extract GCS paths from API response and store them in json file"""
    
    output_data = {}
    output_data["rag_groundtruth_gcs_path"] = ""
    output_data["general_groundtruth_gcs_path"] = ""
    # Extract RAG groundtruth GCS path (first and only dataset)
    rag_datasets = response_data.get("raggroundtruthdatasetnames", [])
    if rag_datasets and rag_datasets[0].get("versions"):
        gcspath = rag_datasets[0]["versions"][0].get("s3path")
        if gcspath:
            output_data["rag_groundtruth_gcs_path"] = gcspath
            logger.info(f"Extracted RAG groundtruth GCS path: {gcspath}")
    
    # Extract General groundtruth S3 path (first and only dataset)
    general_datasets = response_data.get("generalgroundtruthdatasetnames", [])
    if general_datasets:
        gcspath = general_datasets[0].get("s3path")
        if gcspath:
            output_data["general_groundtruth_gcs_path"] = gcspath
            logger.info(f"Extracted General groundtruth S3 path: {gcspath}")
    
    if not output_data:
        logger.warning("No GCS paths found in response")
        return

    with open("/workspace/groundtruth_output.json", "w") as f:
        json.dump(output_data, f)
    logger.info(f"Agent information written to /workspace/groundtruth_output.json")

def _get_id_token(target_audience: str) -> str:
    """Get ID token for authenticating with Cloud Run services."""
    try:
        # Get the default credentials and generate an ID token
        auth_req = Request()
        token = id_token.fetch_id_token(auth_req, target_audience)
        return token
    except Exception as e:
        logger.warning(f"Failed to fetch ID token: {e}. Proceeding without authentication.")
        return None

def create_data(querystringparameters: dict, data: dict, path: str):
    """Make a POST request to create data via the API gateway."""
    # Construct full URL with query parameters
    url = f"{DATA_APP_API_URL}{path}"

    
    headers = {
        "Content-Type": "application/json",
    }
    
    # Add authentication token for Cloud Run services
    # Use the actual Cloud Run service URL for token audience (required for authentication)
    # even when making requests through internal load balancer
    token = _get_id_token(CLOUDRUN_SERVICE_URL)
    if token:
        headers["Authorization"] = f"Bearer {token}"
        logger.info("Added ID token for Cloud Run authentication")
    
    logger.info(f"Making POST request to: {url}")
    logger.info(f"Query parameters: {querystringparameters}")
    logger.info(f"Request data: {json.dumps(data, indent=2)}")
    
    response = requests.post(
        url,
        params=querystringparameters,
        json=data,
        headers=headers,
    )

    logger.info(f"Response status code: {response.status_code}")
    logger.info(f"Response headers: {dict(response.headers)}")
    
    # Log response content for debugging, especially for errors
    try:
        response_content = response.json()
        logger.info(f"Response content: {json.dumps(response_content, indent=2)}")
    except:
        logger.info(f"Response text: {response.text}")
    
    # Raise exception if request failed
    response.raise_for_status()

    return response.json()

def create_agent(
    agent_name: str,
    agent_instruction: str,
    model_name: str,
    region_name: str,
    dataset_name: str = None,
    guardrail_name: str = None,
    groundtruth_names: list = None,
    general_groundtruth_names: list = None,
    rag_groundtruth_names: list = None,
    action_groups: list = None,
    agent_status: str = "In Progress",
    provider_id: int = 3,
    agent_desc: str = None,
    agent_aliasname: str = None,
    agent_aliasdescription: str = None,
    default_agent: bool = True,
    toolname: str = "",
    actiongroupname: str = "",
    actiongroupdesc: str = None,
    actiongroupschemauri: str = ""
):
    """Create an agent with all required parameters matching the API endpoint structure."""
    
    # Set defaults for KB agents
    if agent_desc is None:
        agent_desc = f"GCP Vertex AI Agent '{agent_name}'"
        if dataset_name:
            agent_desc += " with Knowledge Base capabilities"
    if agent_aliasname is None:
        agent_aliasname = f"{agent_name}-alias"
    if agent_aliasdescription is None:
        agent_aliasdescription = f"Production alias for {agent_name}"
    if actiongroupdesc is None:
        actiongroupdesc = f"Knowledge base action group for {agent_name}" if actiongroupname else ""
    if groundtruth_names is None:
        groundtruth_names = []
    if general_groundtruth_names is None:
        general_groundtruth_names = []
    if rag_groundtruth_names is None:
        rag_groundtruth_names = []
    if action_groups is None:
        action_groups = []
    
    # RAG Groundtruth configuration - provide default empty array if not specified
    rag_groundtruth_names = []
    
    # Check if GROUNDTRUTH_NAME is provided (single string, no splitting)
    if groundtruth_name and groundtruth_name.strip():
        rag_entry = {
            "name": groundtruth_name.strip(),
        }
        rag_groundtruth_names.append(rag_entry)

     # General Groundtruth configuration - provide default empty array if not specified
    general_groundtruth_names = []
    
     # Check if GENERAL_GROUNDTRUTH_NAME is provided (single string, no splitting)
    if general_groundtruth_name and general_groundtruth_name.strip():
        general_entry = {
            "name": general_groundtruth_name.strip()
        }
        general_groundtruth_names.append(general_entry)
        
    # Prepare the data payload matching the CreateAgentRequest structure
    data = {
        "agent_name": agent_name,
        "agent_instruction": agent_instruction,
        "modelname": model_name,
        "region_name": region_name,
        "datasetname": dataset_name,
        "groundtruthnames": groundtruth_names,
        "generalgroundtruthnames": general_groundtruth_names,
        "raggroundtruthnames": rag_groundtruth_names,
        "action_groups": action_groups,
        "provider_id": provider_id,
        "agent_desc": agent_desc,
        "agent_aliasname": agent_aliasname,
        "agent_aliasdescription": agent_aliasdescription,
        "default_agent": default_agent,
        "actiongroupdesc": actiongroupdesc,
        "toolname": toolname or "",
        "actiongroupname": actiongroupname or "",
        "actiongroupschemauri": actiongroupschemauri or ""
    }
    
    # Only add tool-related fields if they are provided (for Knowledge Base agents, these might be empty)
    if toolname:
        data["toolname"] = toolname
    else:
        data["toolname"] = ""
        
    if actiongroupname:
        data["actiongroupname"] = actiongroupname
    else:
        data["actiongroupname"] = ""
        
    if actiongroupschemauri:
        data["actiongroupschemauri"] = actiongroupschemauri
    else:
        data["actiongroupschemauri"] = ""

    if guardrail_name:
        data["guardrail"] = { "name": guardrail_name }
    
    agent_path = "/agent/"
    querystringparameters = {}
    
    return create_data(
        querystringparameters=querystringparameters, 
        data=data, 
        path=agent_path
    )

def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="data_create.py")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    create_parser = subparsers.add_parser("create_agent", help="Create GCP Vertex AI agent record in DB")
    create_parser.add_argument("--dataset-name", help="Optional dataset name (Vector Search index)")
    create_parser.add_argument("--groundtruth-names", nargs='*', help="Optional groundtruth names (space-separated)")
    create_parser.add_argument("--agent-status", default="In Progress", help="Agent status (default: In Progress)")
    create_parser.add_argument("--provider-id", type=int, default=3, help="Provider ID (default: 3)")
    create_parser.add_argument("--agent-desc", help="Agent description")
    create_parser.add_argument("--agent-aliasname", help="Agent alias name")
    create_parser.add_argument("--agent-aliasdescription", help="Agent alias description")
    create_parser.add_argument("--default-agent", type=bool, default=True, help="Whether this is the default agent (default: True)")
    create_parser.add_argument("--toolname", default="", help="Tool name (empty for KB agents)")
    create_parser.add_argument("--actiongroupname", default="", help="Action group name (empty for KB agents)")
    create_parser.add_argument("--actiongroupdesc", help="Action group description")
    create_parser.add_argument("--actiongroupschemauri", default="", help="Action group schema URI")

    args = parser.parse_args(argv)

    if args.subcommand == "create_agent":
        # Convert single groundtruth_name to list if provided
        groundtruth_names = [groundtruth_name] if groundtruth_name else args.groundtruth_names

        resp = create_agent(
            agent_name=agent_name,
            agent_instruction=agent_instruction,
            model_name=model_name,
            region_name=region_name,
            dataset_name=dataset_name,
            guardrail_name=guardrail_name,
            groundtruth_names=groundtruth_names,
            agent_status=args.agent_status,
            provider_id=args.provider_id,
            agent_desc=args.agent_desc,
            agent_aliasname=args.agent_aliasname,
            agent_aliasdescription=args.agent_aliasdescription,
            default_agent=args.default_agent,
            toolname=args.toolname,
            actiongroupname=args.actiongroupname,
            actiongroupdesc=args.actiongroupdesc,
            actiongroupschemauri=args.actiongroupschemauri,
        )
        
        logger.info("Agent creation response:")
        logger.info(json.dumps(resp, indent=2))
        agent_id = resp["agentid"]
        version_tag = resp["version_tag"]
        rag_run_id = resp["rag_run_id"]
        general_run_id = resp["general_run_id"]
        output_data = {
            "agent_id": agent_id,
            "agent_version_tag":version_tag,
            "rag_run_id": rag_run_id,
            "general_run_id": general_run_id,
        }
        with open("/workspace/agent_data_create.json", "w") as f:
            json.dump(output_data, f)
        logger.info(f"Agent information written to /workspace/agent_data_create.json")
        
        # Extract and store GCS paths
        _extract_and_store_gcspaths(resp)
        
        
    else:
        parser.error(f"Unknown subcommand: {args.subcommand}")

if __name__ == "__main__":
    main()
