"""Agent deployment module for Vertex AI Agent Engine."""

import vertexai
from vertexai import agent_engines

from root_agent.agent import root_agent
from config import config

import json
import os

from utils.log_helper import setup_logging
logger = setup_logging()

# Project configuration
PROJECT_ID = config.PROJECT_ID
LOCATION = config.LOCATION
STAGING_BUCKET = config.STAGING_BUCKET
MODEL_ID = config.model_id
SERVICE_ACCOUNT = config.SERVICE_ACCOUNT_NAME
GUARDRAIL_NAME = config.guardrail_name
GUARDRAIL_BUCKET_NAME = config.bucket_name
GUARDRAIL_BUCKET_PREFIX = config.GUARDRAIL_BUCKET_PREFIX
GUARDRAILS_ENABLED = config.guardrail_enabled
NETWORK_ATTACHMENT = config.NETWORK_ATTACHMENT
DNS_PEERING_DOMAIN = config.DNS_PEERING_DOMAIN
DNS_PEERING_DOMAIN_TARGET_PROJECT = config.DNS_PEERING_DOMAIN_TARGET_PROJECT
DNS_PEERING_DOMAIN_TARGET_NETWORK = config.DNS_PEERING_DOMAIN_TARGET_NETWORK

# Arize observability configuration
ARIZE_SPACE_ID = config.arize_space_id_name
ARIZE_API_KEY = config.arize_api_key_name
ARIZE_ENDPOINT = config.arize_endpoint

# Check if guardrails are properly configured (all required values are present and not empty)
guardrails_configured = ( 
    GUARDRAIL_NAME and 
    GUARDRAIL_BUCKET_NAME and 
    GUARDRAIL_BUCKET_PREFIX
)

# Base OpenTelemetry environment variables for Arize observability
base_env_vars = {
    "OTEL_LOG_LEVEL": "DEBUG",
    "NO_PROXY": "otlp.arize.com",
    "OTEL_EXPORTER_OTLP_ENDPOINT": ARIZE_ENDPOINT,
    "OTEL_EXPORTER_OTLP_TIMEOUT": "60000",  # Optional, can prevent "context deadline exceeded" errors
}

requirements = [
    "google-cloud-aiplatform[agent_engines,langchain,langchain_google_vertexai,aiplatform,adk]>=1.141.0",
    "google-adk>=1.18.0",
    "arize-otel==0.9.0",
    "openinference-instrumentation-google-adk>=0.1.8",
    "requests>=2.31.0",
]

if guardrails_configured:
    logger.info("🛡️ Guardrails are enabled and configured. Adding guardrail environment variables.")
    env_vars_dict = {
        **base_env_vars,
        "GUARDRAILS_ENABLED": "true",
        "GUARDRAIL_NAME": GUARDRAIL_NAME,
        "GUARDRAIL_BUCKET_NAME": GUARDRAIL_BUCKET_NAME,
        "GUARDRAIL_BUCKET_PREFIX": GUARDRAIL_BUCKET_PREFIX,
    }
else:
    logger.info("ℹ️ Guardrails are disabled. Proceeding without guardrail environment variables.")
    env_vars_dict = base_env_vars.copy()


logger.info("🔧 Initializing Vertex AI SDK...")

client = vertexai.Client(
    project=PROJECT_ID,
    location=LOCATION,
)

agent_display_name = root_agent.name
agent_description = root_agent.description

# Wrap agent AdkApp is required 
logger.info(f"📦 Wrapping agent '{agent_display_name}' in AdkApp...")
app = agent_engines.AdkApp(
    agent=root_agent,
    enable_tracing=True,
)

vertexai.init(project=PROJECT_ID, location=LOCATION)

try:
    logger.info(f"🚀 Deploying agent to Vertex AI Agent Engine...")
    remote_agent = client.agent_engines.create(
        agent=app,
        config=dict(
            requirements=requirements,
            # Package the entire `root_agent` package so all modules (tools,
            # sub-agents, helpers) are available at runtime. Passing a single
            # file may break packaging; vertexai expects directories or
            # package paths.
            extra_packages=[
                "./root_agent",
            ],
            gcs_dir_name=agent_display_name.replace(" ", "_").lower(),
            display_name=agent_display_name,
            description=agent_description,
            env_vars=env_vars_dict,
            service_account=SERVICE_ACCOUNT,
            staging_bucket=STAGING_BUCKET,
            psc_interface_config={
                "network_attachment": NETWORK_ATTACHMENT,
                "dns_peering_configs": [
                    {
                        "domain": DNS_PEERING_DOMAIN,
                        "target_project": DNS_PEERING_DOMAIN_TARGET_PROJECT,
                        "target_network": DNS_PEERING_DOMAIN_TARGET_NETWORK,
                    },
                ],
            },
        ),
    )

    # remote_agent = client.agent_engines.create(
    #     display_name=agent_display_name,
    #     description=agent_description,
    #     agent_engine=app,
    #     requirements="requirements.txt",
    #     extra_packages=["./root_agent/content_filter"],
    #     gcs_dir_name=agent_display_name.replace(" ", "_").lower(),
    #     service_account=SERVICE_ACCOUNT,
    #     staging_bucket=STAGING_BUCKET
    # )

    logger.info(f"✅ Deployment finished!")

    # Write agent information for the next Cloud Build step
    logger.info(f"Agent created successfully!")
    
    # Extract agent information with robust error handling
    
    # Try to extract agent name from different sources
    agent_name = ""
    
    # Method 1: Try original logic - get name attribute directly
    if hasattr(remote_agent, 'name') and remote_agent.name:
        agent_name = str(remote_agent.name)
    
    # Method 2: Fallback - get from api_resource.name (known working method)
    elif hasattr(remote_agent, 'api_resource') and hasattr(remote_agent.api_resource, 'name'):
        agent_name = str(remote_agent.api_resource.name)
    
    # Store the full agent name as agent_alias_id
    agent_alias_id = agent_name if agent_name else ""

    # Extract agent base ID from the agent name
    agent_base_id = ""
    if agent_name and '/' in agent_name:
        parts = agent_name.split('/')
        # Look for reasoningEngines part in the path
        for i, part in enumerate(parts):
            if part == 'reasoningEngines' and i + 1 < len(parts):
                agent_base_id = parts[i + 1]
                break
        
        # If reasoningEngines not found, use the last part as fallback
        if not agent_base_id:
            agent_base_id = parts[-1]
    
    # Final fallback - use timestamp if extraction fails completely
    if not agent_base_id:
        import time
        agent_base_id = str(int(time.time()))
        logger.warning(f"Using fallback agent base ID: {agent_base_id}")
        agent_name = f"projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{agent_base_id}"
        agent_alias_id = agent_name  # Update alias_id with the fallback name too

    # Build the URL based on the extracted agent_base_id
    if agent_base_id:
        agent_url = (
            f"https://console.cloud.google.com/vertex-ai/agents/"
            f"locations/{LOCATION}/agent-engines/{agent_base_id}/"
            f"metrics?project={PROJECT_ID}"
        )
        logger.info(f"Built agent {agent_display_name} Successfully")
    else:
        agent_url = f"https://console.cloud.google.com/vertex-ai/agents?project={PROJECT_ID}"
        logger.info(f"Built fallback URL: {agent_url}")

    # Determine the agent display name to use
    final_agent_name = (getattr(remote_agent, 'display_name', None) or 
                       agent_display_name or 
                       "Unknown Agent")

    output_data = {
        "agent_base_id": agent_base_id,
        "agent_alias_id": agent_alias_id,
        "agent_url": agent_url,
        "agent_name": final_agent_name,
        "agent_full_name": str(getattr(remote_agent, 'name', '')),
        "model": MODEL_ID,
        "creation_successful": True
    }

    logger.info(f"Writing agent information to /workspace/agent_output.json")
    
    with open("/workspace/agent_output.json", "w") as f:
        json.dump(output_data, f)
    logger.info(f"Agent information written to /workspace/agent_output.json")
    
except Exception as e:
    logger.error(f"Failed to create agent: {e}")
    # Create a fallback output file with empty values
    output_data = {
        "agent_base_id": "",
        "agent_alias_id": "",
        "agent_url": f"https://console.cloud.google.com/vertex-ai/agents?project={PROJECT_ID}",
        "agent_name": agent_display_name,
        "agent_full_name": "",
        "creation_successful": False,
        "error": str(e)
    }
    with open("/workspace/agent_output.json", "w") as f:
        json.dump(output_data, f)
    logger.info(f"Error information written to /workspace/agent_output.json")
    raise Exception(e)
