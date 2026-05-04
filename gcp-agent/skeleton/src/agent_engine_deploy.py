import vertexai
import os
import dotenv
from dotenv import dotenv_values
dotenv.load_dotenv()
from vertexai import agent_engines
from config.config import (
    # Values from configuration.json
    PROJECT_ID,
    AGENT_DISPLAY_NAME,
    AGENT_DESCRIPTION,
    MODEL_NAME,
    SYSTEM_INSTRUCTION,
    LOCATION,
    STAGING_BUCKET,
    AGENT_PROMPT,
    GUARDRAIL_NAME,
    GUARDRAIL_BUCKET_NAME,
    GUARDRAIL_BUCKET_PREFIX,
    NETWORK_ATTACHMENT,
    DNS_PEERING_DOMAIN,
    DNS_PEERING_DOMAIN_TARGET_PROJECT,
    DNS_PEERING_DOMAIN_TARGET_NETWORK,
    ARIZE_ENDPOINT,
    SERVICE_ACCOUNT_NAME,
    MCP_SERVER_URL
)
# Set env var from config so agent.py/load_mcp_tools.py can use os.getenv()
if MCP_SERVER_URL:
    os.environ.setdefault("MCP_SERVER_URL", MCP_SERVER_URL)
from agent import app
agent_display_name = AGENT_DISPLAY_NAME
agent_description = AGENT_DESCRIPTION
model = MODEL_NAME
system_instruction = SYSTEM_INSTRUCTION
prompt = AGENT_PROMPT
from utils.log_helper import setup_logging
logger = setup_logging()
vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)
 
 
 
remote_agent = None
# Now preparing the agent for deployment to the agent engine.
requirements = [
    "google-cloud-aiplatform[agent_engines,langchain,langchain_google_vertexai,aiplatform,adk]>=1.141.0",
    "google-adk>=1.18.0",
    "arize-otel==0.9.0",
    "openinference-instrumentation-google-adk>=0.1.8",
    "requests>=2.31.0",
]
#extra_packages="agent.py",
extra_packages=[
                        "./agent.py", # a single file
                        "./content_filter", # a directory
                    ],
# Check if guardrails are properly configured (all required values are present and not empty)
guardrails_configured = (
    GUARDRAIL_NAME and
    GUARDRAIL_BUCKET_NAME and
    GUARDRAIL_BUCKET_PREFIX
)
 
if guardrails_configured:
    logger.info("🛡️ Guardrails are enabled and configured. Adding guardrail environment variables.")
    env_vars_dict = {
        "GUARDRAILS_ENABLED": "true",
        "GUARDRAIL_NAME": GUARDRAIL_NAME,
        "GUARDRAIL_BUCKET_NAME": GUARDRAIL_BUCKET_NAME,
        "GUARDRAIL_BUCKET_PREFIX": GUARDRAIL_BUCKET_PREFIX,
        "OTEL_LOG_LEVEL": "DEBUG",
        "NO_PROXY": "otlp.arize.com",
        "OTEL_EXPORTER_OTLP_ENDPOINT": ARIZE_ENDPOINT,
        "OTEL_EXPORTER_OTLP_TIMEOUT": "60000", #Optional, can prevent "context deadline exceeded" errors
    }
else:
    logger.info("ℹ️ Guardrails are disabled. Proceeding without guardrail environment variables.")
    env_vars_dict = {
        "OTEL_LOG_LEVEL": "DEBUG",
        "NO_PROXY": "otlp.arize.com",
        "OTEL_EXPORTER_OTLP_ENDPOINT": ARIZE_ENDPOINT,
        "OTEL_EXPORTER_OTLP_TIMEOUT": "60000", #Optional, can prevent "context deadline exceeded" errors
    }

# Only add MCP_SERVER_URL if it's configured and not empty
if MCP_SERVER_URL and MCP_SERVER_URL.strip():
    env_vars_dict["MCP_SERVER_URL"] = MCP_SERVER_URL
    logger.info("✅ MCP_SERVER_URL added to environment variables")
 
try:
    import json
    client = vertexai.Client(
        project=PROJECT_ID,
        location=LOCATION,
    )
 
    logger.info(f"🚀 Deploying agent to Vertex AI Agent Engine...")
    remote_agent = client.agent_engines.create(
        agent=app,
       
        # config={
        #     "requirements": requirements,
        #     "extra_packages": extra_packages,
        #     "gcs_dir_name": agent_display_name.replace(" ", "_").lower(),
        #     "display_name": agent_display_name,
        #     "description": agent_description,
        #     "env_vars": env_vars_dict,
        #     "service_account":SERVICE_ACCOUNT_NAME,
        #     "staging_bucket": STAGING_BUCKET,
        #     "psc_interface_config": {
        #         "network_attachment": NETWORK_ATTACHMENT,
        #         "dns_peering_configs": [
        #             {
        #                 "domain": DNS_PEERING_DOMAIN,
        #                 "target_project": DNS_PEERING_DOMAIN_TARGET_PROJECT,
        #                 "target_network": DNS_PEERING_DOMAIN_TARGET_NETWORK,
        #             },
        #         ],
        #     },
        # },
        config=dict(
                    requirements=requirements,
                    extra_packages=[
                        "./agent.py",
                        "./load_mcp_tools.py",
                        "./load_rag_corpora.py",
                        "./utils",
                        "./content_filter",
                    ],
                    gcs_dir_name=agent_display_name.replace(" ", "_").lower(),
                    display_name=agent_display_name,
                    description=agent_description,
                    env_vars=env_vars_dict,
                    service_account=SERVICE_ACCOUNT_NAME,
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
    # remote_agent = agent_engines.create(
       
    #     agent_engine=app ,#agent_engines.ModuleAgent(module_name="adk_agent", agent_name="app", register_operations=_TEST_REGISTER_OPERATIONS),
    #     requirements=[
    #         "google-cloud-aiplatform[agent_engines,adk]",
    #         "arize-otel",
    #         "openinference-instrumentation-google-adk",
    #     ],
    #     extra_packages=["agent.py"],
    #     env_vars={
    #         "OTEL_LOG_LEVEL": "DEBUG",
    #         "NO_PROXY": "otlp.arize.com",
    #         "OTEL_EXPORTER_OTLP_ENDPOINT": "https://otlp.arize.com/v1",
    #         "OTEL_EXPORTER_OTLP_TIMEOUT": "60000", #Optional, can prevent "context deadline exceeded" errors
    #     },
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
   
    if MODEL_NAME:
        gcp_gemini_endpoint = (
            f"https://aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/"
            f"locations/{LOCATION}/publishers/google/models/{MODEL_NAME}"
        )
        logger.info(f"Built GCP Gemini Endpoint: {gcp_gemini_endpoint}")
    else:
        logger.info("Failed to Create gcp-gemini-endpoint")
        gcp_gemini_endpoint = None  
 
    # Build the URL based on the extracted agent_base_id
    if agent_base_id:
        agent_url = (
            f"https://console.cloud.google.com/vertex-ai/agents/"
            f"locations/{LOCATION}/agent-engines/{agent_base_id}/"
            f"metrics?project={PROJECT_ID}"
        )
        logger.info(f"Built agent URL: {agent_url}")
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
        "model": model,
        "gcp_gemini_endpoint": gcp_gemini_endpoint,
        "creation_successful": True
    }
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
        "creation_successful": False,
        "error": str(e)
    }
    with open("/workspace/agent_output.json", "w") as f:
        json.dump(output_data, f)
    logger.info(f"Error information written to /workspace/agent_output.json")
    raise Exception(e)