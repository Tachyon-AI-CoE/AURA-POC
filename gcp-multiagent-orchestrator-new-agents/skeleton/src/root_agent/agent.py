"""Root agent initialization module."""

import os

from google.adk.agents import LlmAgent
from google.cloud import secretmanager

from root_agent.multi_agent_builder import MultiAgentBuilder
from root_agent.content_filter.safety_settings import safety_settings_download_callback
from config import config

from utils.log_helper import setup_logging

logger = setup_logging()

# Import Arize observability components
from arize.otel import register
from openinference.instrumentation.google_adk import GoogleADKInstrumentor


def fetch_arize_secrets():
    """
    Fetch Arize credentials from Google Cloud Secret Manager.
    Returns a tuple of (space_id, api_key).
    """
    try:
        gcp_secret_manager_project = config.gcp_secret_manager_project
        space_id_secret_name = config.arize_space_id_name
        api_key_secret_name = config.arize_api_key_name
        
        if not space_id_secret_name or not api_key_secret_name:
            logger.warning("⚠️ Arize secret names not configured in config")
            return None, None
        
        # Create a SecretManager client
        client = secretmanager.SecretManagerServiceClient()
        
        # Retrieve ARIZE_SPACE_ID
        try:
            space_id_path = f"projects/{gcp_secret_manager_project}/secrets/{space_id_secret_name}/versions/latest"
            response = client.access_secret_version(request={"name": space_id_path})
            arize_space_id = response.payload.data.decode("UTF-8")
            logger.info(f"✅ Arize Space ID retrieved from Secret Manager")
        except Exception as e:
            logger.warning(f"⚠️ Failed to retrieve Arize Space ID from Secret Manager: {e}")
            arize_space_id = None
        
        # Retrieve ARIZE_API_KEY
        try:
            api_key_path = f"projects/{gcp_secret_manager_project}/secrets/{api_key_secret_name}/versions/latest"
            response = client.access_secret_version(request={"name": api_key_path})
            arize_api_key = response.payload.data.decode("UTF-8")
            logger.info(f"✅ Arize API Key retrieved from Secret Manager")
        except Exception as e:
            logger.warning(f"⚠️ Failed to retrieve Arize API Key from Secret Manager: {e}")
            arize_api_key = None
        
        return arize_space_id, arize_api_key
    except Exception as e:
        logger.warning(f"⚠️ Arize secret initialization failed: {e}")
        return None, None


# Configure Arize instrumentation for observability
logger.info("🔭 Setting up Arize observability instrumentation...")
arize_space_id, arize_api_key = fetch_arize_secrets()

try:
    if arize_space_id and arize_api_key:
        tracer_provider = register(
            space_id=arize_space_id,  # Arize space ID from Secret Manager
            api_key=arize_api_key,     # Arize API key from Secret Manager
            project_name=f"{config.agent_display_name}_1_TracingProject",  # Project name in Arize
        )
        GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
        logger.info("✅ Arize instrumentation configured successfully")
    else:
        logger.warning("⚠️ Arize credentials not available, skipping instrumentation")
except Exception as e:
    logger.warning(f"⚠️ Failed to configure Arize instrumentation: {e}")
    logger.warning("Continuing without Arize observability...")

config_path = os.path.join(
    os.path.dirname(__file__), "..", "config", "agent-config.yaml"
)
builder = MultiAgentBuilder(config_path)


def build_root_agent() -> LlmAgent:
    """Build the root agent with dynamic safety settings via before_agent_callback."""
    logger.info("🏗️ Building root agent with dynamic safety settings...")

    builder.validate_config()
    agent = builder.build_root_agent(include_sub_agents=True)

    # Add before_agent_callback to download and save guardrail configuration
    agent.before_agent_callback = safety_settings_download_callback

    logger.info("✅ Root agent built with safety settings and dynamic reload callback")
    return agent


root_agent = build_root_agent()
