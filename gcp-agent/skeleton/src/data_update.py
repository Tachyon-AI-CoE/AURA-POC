import argparse
import json
import os
import sys
import requests
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from dotenv import load_dotenv
from utils.log_helper import setup_logging

load_dotenv()
logger = setup_logging()

from config.config import (
    # Values from JSON config file
    DATA_APP_API_URL,
    CLOUDRUN_SERVICE_URL,
    AGENT_DISPLAY_NAME
)

# Validate required environment variables
if not DATA_APP_API_URL:
    raise ValueError("DATA_APP_API_URL environment variable is required but not set")
if not CLOUDRUN_SERVICE_URL:
    raise ValueError("CLOUDRUN_SERVICE_URL environment variable is required but not set")

# Extract values from configuration
agent_name = AGENT_DISPLAY_NAME

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

def update_data(querystringparameters: dict, data: dict, path: str):
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
    
    logger.info(f"Making PUT request to: {url}")
    logger.info(f"Query parameters: {querystringparameters}")
    logger.info(f"Request data: {json.dumps(data, indent=2)}")
    
    response = requests.put(
        url,
        params=querystringparameters,
        json=data,
        headers=headers,
    )

    logger.info(f"Response status code: {response.status_code}")
    logger.info(f"Response headers: {dict(response.headers)}")
    
    # Print response content for debugging, especially for errors
    try:
        response_content = response.json()
        logger.info(f"Response content: {json.dumps(response_content, indent=2)}")
    except:
        logger.info(f"Response text: {response.text}")
    
    # Raise exception if request failed
    response.raise_for_status()
    return response.json()


def update_agent(
    agent_name: str,
    agent_base_id: str,
    agent_alias_id: str,
    agent_url: str,
    status: str,
) -> dict:
    """Prepare payload and delegate to update_data()."""

    data = {
        "agentName": agent_name,
        "agentBaseId": agent_base_id,
        "agentAliasId": agent_alias_id,
        "agentUrl": agent_url,
        "status": status,
    }
    agent_path = "/updateagent/"
    querystringparameters = {"agent_name": agent_name}
    return update_data(
        querystringparameters=querystringparameters, data=data, path=agent_path
    )


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="data_update.py")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    up = subparsers.add_parser("update_agent", help="Update agent record in DB")
    up.add_argument("agent_base_id")
    up.add_argument("agent_alias_id")
    up.add_argument("agent_url")
    up.add_argument("status")

    args = parser.parse_args(argv)

    if args.subcommand == "update_agent":
        # Check if we should read from JSON file (when placeholders are used)
        if (args.agent_base_id == "AGENT_BASE_ID" or 
            args.agent_alias_id == "AGENT_ALIAS_ID" or 
            args.agent_url == "AGENT_URL"):
            
            # Read from the JSON file created by agent.py
            try:
                with open("/workspace/agent_output.json", "r") as f:
                    agent_data = json.load(f)
                
                logger.info("Reading agent data from /workspace/agent_output.json:")
                logger.info(json.dumps(agent_data, indent=2))
                
                # Use values from JSON file
                actual_agent_base_id = agent_data.get("agent_base_id", "")
                actual_agent_alias_id = agent_data.get("agent_alias_id", "")
                actual_agent_url = agent_data.get("agent_url", "")
                
                logger.info(f"Using values from JSON: base_id={actual_agent_base_id}, alias_id={actual_agent_alias_id}, url={actual_agent_url}")
                
                resp = update_agent(
                    agent_name,
                    actual_agent_base_id,
                    actual_agent_alias_id,
                    actual_agent_url,
                    args.status,
                )
            except FileNotFoundError:
                logger.error("Error: /workspace/agent_output.json not found. Using placeholder values.")
                resp = update_agent(
                    agent_name,
                    args.agent_base_id,
                    args.agent_alias_id,
                    args.agent_url,
                    "Failed",
                )
            except Exception as e:
                logger.error(f"Error reading agent data from JSON: {e}. Using placeholder values.")
                resp = update_agent(
                    agent_name,
                    args.agent_base_id,
                    args.agent_alias_id,
                    args.agent_url,
                    "Failed",
                )
        else:
            # Use command line arguments as provided
            resp = update_agent(
                agent_name,
                args.agent_base_id,
                args.agent_alias_id,
                args.agent_url,
                args.status,
            )
        
        logger.info("Agent DB update response:")
        logger.info(json.dumps(resp, indent=2))
    else:
        parser.error(f"Unknown subcommand: {args.subcommand}")


if __name__ == "__main__":
    main()