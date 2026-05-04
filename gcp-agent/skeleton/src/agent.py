import os
import vertexai
import dotenv

from dotenv import dotenv_values
dotenv.load_dotenv()
from config.config import (
    # Values from configuration.json
    PROJECT_ID,
    AGENT_DISPLAY_NAME,
    AGENT_DESCRIPTION,
    MODEL_NAME,
    SYSTEM_INSTRUCTION,
    LOCATION,
    AGENT_PROMPT,
    GENERAL_EVALUATION,
    RAGAS_EVALUATION,
    ARIZE_SPACE_ID_NAME,
    ARIZE_API_KEY_NAME,
    GCP_SECRET_MANAGER_PROJECT
)

from utils.log_helper import setup_logging
logger = setup_logging()

from google.cloud.aiplatform import initializer
from google.genai import types
from google.adk.agents import Agent
from vertexai import agent_engines
from google.cloud import secretmanager

from load_rag_corpora import get_corpus_as_tools
from load_mcp_tools import load_mcp_toolset
from content_filter.safety_settings import safety_settings_download_callback, safety_settings_model_callback
from arize.otel import register
from openinference.instrumentation.google_adk import GoogleADKInstrumentor

# Extract values from configuration
agent_display_name = AGENT_DISPLAY_NAME
agent_description = AGENT_DESCRIPTION
model = MODEL_NAME
system_instruction = SYSTEM_INSTRUCTION
prompt = AGENT_PROMPT


def fetch_arize_secrets():
    """
    Fetch Arize credentials from Google Cloud Secret Manager.
    Returns a tuple of (space_id, api_key).
    """
    try:
        if not ARIZE_SPACE_ID_NAME or not ARIZE_API_KEY_NAME:
            logger.warning("⚠️ Arize secret names not configured in config")
            return None, None
        
        # Create a SecretManager client
        client = secretmanager.SecretManagerServiceClient()
        
        # Retrieve ARIZE_SPACE_ID
        try:
            space_id_path = f"projects/{GCP_SECRET_MANAGER_PROJECT}/secrets/{ARIZE_SPACE_ID_NAME}/versions/latest"
            response = client.access_secret_version(request={"name": space_id_path})
            arize_space_id = response.payload.data.decode("UTF-8")
            logger.info(f"✅ Arize Space ID retrieved from Secret Manager")
        except Exception as e:
            logger.warning(f"⚠️ Failed to retrieve Arize Space ID from Secret Manager: {e}")
            arize_space_id = None
        
        # Retrieve ARIZE_API_KEY
        try:
            api_key_path = f"projects/{GCP_SECRET_MANAGER_PROJECT}/secrets/{ARIZE_API_KEY_NAME}/versions/latest"
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
            project_name=f"{agent_display_name}_1_TracingProject",  # Project name in Arize
        )
        GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
        logger.info("✅ Arize instrumentation configured successfully")
    else:
        logger.warning("⚠️ Arize credentials not available, skipping instrumentation")
except Exception as e:
    logger.warning(f"⚠️ Failed to configure Arize instrumentation: {e}")
    logger.warning("Continuing without Arize observability...")


logger.info(f"Value of GENERAL_EVALUATION: {GENERAL_EVALUATION}")
logger.info(f"Value of RAGAS_EVALUATION: {RAGAS_EVALUATION}")

# Initialize Vertex AI SDK
logger.info("🔧 Initializing Vertex AI SDK...")
vertexai.init(project=PROJECT_ID, location=LOCATION)

final_tools = []
final_tools.extend(get_corpus_as_tools("rag_configuration.json"))

# Load MCP toolset if configured
mcp_toolset = load_mcp_toolset()
if mcp_toolset is not None:
    final_tools.append(mcp_toolset)

# Define the agent.
# provide the model name, the tools either functional or rag,
# and the instruction and prompts.
agent = None

llm_config = {
    "config_list": [{
        "project_id":       PROJECT_ID,
        "location":         LOCATION,
        "model":            model,
        "api_type":         "google",
    }]
}
generate_content_config = types.GenerateContentConfig(
    temperature=0.28,
    max_output_tokens=1000,
    top_p=0.95,
)
agent = Agent(
    model=model,                                      # Required.
    name=agent_display_name,                   # Required.
    generate_content_config=generate_content_config,  # Optional.
    tools=final_tools,
    before_agent_callback=safety_settings_download_callback,
    before_model_callback=safety_settings_model_callback,
    instruction=system_instruction,
)

# Wrap agent in AdkApp (required for deployment)
logger.info(f"📦 Wrapping agent '{agent_display_name}' in AdkApp...")
app = agent_engines.AdkApp(
    agent=agent,
    enable_tracing=True,
)

