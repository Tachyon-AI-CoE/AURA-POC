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

# ── FIX 1: Output path — use AGENT_OUTPUT_PATH env var, fallback to local ────
# Cloud Build sets /workspace/agent_output.json
# Local deploy sets AGENT_OUTPUT_PATH in base_env
AGENT_OUTPUT_PATH = os.environ.get(
    "AGENT_OUTPUT_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agent_output.json")
)

# Check if guardrails are properly configured
guardrails_configured = (
    GUARDRAIL_NAME and
    GUARDRAIL_BUCKET_NAME and
    GUARDRAIL_BUCKET_PREFIX
)

# ── FIX 2: Only include OTEL env vars that are not None ───────────────────────
# Vertex AI rejects env_vars with None values — skip any that are null/empty
base_env_vars = {}
otel_vars = {
    "OTEL_LOG_LEVEL": "DEBUG",
    "NO_PROXY": "otlp.arize.com",
    "OTEL_EXPORTER_OTLP_ENDPOINT": ARIZE_ENDPOINT,
    "OTEL_EXPORTER_OTLP_TIMEOUT": "60000",
}
for k, v in otel_vars.items():
    if v is not None and v != "":
        base_env_vars[k] = v

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

logger.info(f"📦 Wrapping agent '{agent_display_name}' in AdkApp...")
app = agent_engines.AdkApp(
    agent=root_agent,
    enable_tracing=True,
)

vertexai.init(project=PROJECT_ID, location=LOCATION)

try:
    logger.info(f"🚀 Deploying agent to Vertex AI Agent Engine...")
    # Build deploy config — only include psc_interface_config if NETWORK_ATTACHMENT is set
    # (required for VPC-peered production environments, not needed for local testing)
    deploy_config = dict(
        requirements=requirements,
        extra_packages=[
            "./root_agent/content_filter",
            "./root_agent/agent.py",
        ],
        gcs_dir_name=agent_display_name.replace(" ", "_").lower(),
        display_name=agent_display_name,
        description=agent_description,
        env_vars=env_vars_dict,
        service_account=SERVICE_ACCOUNT,
        staging_bucket=STAGING_BUCKET,
    )

    if NETWORK_ATTACHMENT:
        deploy_config["psc_interface_config"] = {
            "network_attachment": NETWORK_ATTACHMENT,
            "dns_peering_configs": [
                {
                    "domain": DNS_PEERING_DOMAIN,
                    "target_project": DNS_PEERING_DOMAIN_TARGET_PROJECT,
                    "target_network": DNS_PEERING_DOMAIN_TARGET_NETWORK,
                },
            ],
        }

    remote_agent = client.agent_engines.create(
        agent=app,
        config=deploy_config,
    )

    logger.info(f"✅ Deployment finished!")
    logger.info(f"Agent created successfully!")

    agent_name = ""
    if hasattr(remote_agent, 'name') and remote_agent.name:
        agent_name = str(remote_agent.name)
    elif hasattr(remote_agent, 'api_resource') and hasattr(remote_agent.api_resource, 'name'):
        agent_name = str(remote_agent.api_resource.name)

    agent_alias_id = agent_name if agent_name else ""

    agent_base_id = ""
    if agent_name and '/' in agent_name:
        parts = agent_name.split('/')
        for i, part in enumerate(parts):
            if part == 'reasoningEngines' and i + 1 < len(parts):
                agent_base_id = parts[i + 1]
                break
        if not agent_base_id:
            agent_base_id = parts[-1]

    if not agent_base_id:
        import time
        agent_base_id = str(int(time.time()))
        logger.warning(f"Using fallback agent base ID: {agent_base_id}")
        agent_name = f"projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{agent_base_id}"
        agent_alias_id = agent_name

    if agent_base_id:
        agent_url = (
            f"https://console.cloud.google.com/vertex-ai/agents/"
            f"locations/{LOCATION}/agent-engines/{agent_base_id}/"
            f"metrics?project={PROJECT_ID}"
        )
    else:
        agent_url = f"https://console.cloud.google.com/vertex-ai/agents?project={PROJECT_ID}"

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

    logger.info(f"Agent Engine created. To use it in another session:")
    logger.info(f"agent_engine=client.agent_engines.get(name='{agent_alias_id}')")
    logger.info(f"✅ Deployment finished!")
    logger.info(f"Agent created successfully!")
    logger.info(f"Built GCP Gemini Endpoint: https://aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{MODEL_ID}")
    logger.info(f"Built agent URL: {agent_url}")
    logger.info(f"Agent information written to {AGENT_OUTPUT_PATH}")

    os.makedirs(os.path.dirname(AGENT_OUTPUT_PATH) if os.path.dirname(AGENT_OUTPUT_PATH) else ".", exist_ok=True)
    with open(AGENT_OUTPUT_PATH, "w") as f:
        json.dump(output_data, f)

except Exception as e:
    logger.error(f"Failed to create agent: {e}")
    output_data = {
        "agent_base_id": "",
        "agent_alias_id": "",
        "agent_url": f"https://console.cloud.google.com/vertex-ai/agents?project={PROJECT_ID}",
        "agent_name": agent_display_name,
        "agent_full_name": "",
        "creation_successful": False,
        "error": str(e)
    }
    os.makedirs(os.path.dirname(AGENT_OUTPUT_PATH) if os.path.dirname(AGENT_OUTPUT_PATH) else ".", exist_ok=True)
    with open(AGENT_OUTPUT_PATH, "w") as f:
        json.dump(output_data, f)
    logger.info(f"Error information written to {AGENT_OUTPUT_PATH}")
    raise Exception(e)

