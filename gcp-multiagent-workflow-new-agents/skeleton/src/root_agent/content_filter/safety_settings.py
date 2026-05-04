"""Module for reading guardrail configuration from GCS and constructing safety settings."""

import json
import logging
import os
from typing import Dict, List, Optional

from google.adk.models import LlmResponse, LlmRequest

from google.adk.agents.callback_context import CallbackContext
from google.cloud import storage
from google.genai.types import GenerateContentConfig, SafetySetting, Content

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(asctime)s %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)
# Ensure this logger uses INFO level even if root logger is set differently
logger.setLevel(logging.INFO)

def read_guardrail_from_gcs(
    bucket_name: str, file_name: str = "guardrail.json"
) -> Optional[Dict]:
    """Read guardrail configuration from GCS bucket."""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_name)

        if not blob.exists():
            logger.error(
                f"❌ Guardrail file {file_name} not found in bucket {bucket_name}"
            )
            return None

        content = blob.download_as_text()
        guardrail_config = json.loads(content)
        logger.info(
            f"✅ Successfully loaded guardrail configuration from gs://{bucket_name}/{file_name}"
        )
        return guardrail_config

    except Exception as e:
        logger.error(f"❌ Error reading guardrail from GCS: {str(e)}")
        return None


def construct_safety_settings(guardrail_config: Dict) -> List[SafetySetting]:
    """Construct safety_settings list from guardrail configuration."""
    safety_settings = []

    try:
        # Navigate to the safety_settings in the guardrail structure
        content_filters = guardrail_config.get("content_filters", {})
        configurable_filters = content_filters.get("configurable_filters", {})
        safety_settings_config = configurable_filters.get("safety_settings", [])

        # Convert each safety setting to SafetySetting object
        for setting in safety_settings_config:
            category = setting.get("category")
            threshold = setting.get("threshold")

            if category and threshold:
                # Create SafetySetting object
                safety_setting = SafetySetting(category=category, threshold=threshold)
                safety_settings.append(safety_setting)
                logger.debug(f"🔒 Added safety setting: {category} -> {threshold}")

        logger.info(f"✅ Constructed {len(safety_settings)} safety settings")

    except Exception as e:
        logger.error(f"❌ Error constructing safety settings: {str(e)}")
        return []

    return safety_settings


def get_safety_settings_from_gcs(
    bucket_name: Optional[str] = None, file_name: str = "guardrail.json"
) -> List[SafetySetting]:
    """Read guardrail configuration from GCS and return safety_settings."""
    # Use environment variable if bucket_name not provided
    if bucket_name is None:
        bucket_name = os.getenv("GUARDRAIL_BUCKET")

    if not bucket_name:
        logger.warning(
            "⚠️ No guardrail bucket specified. Returning empty safety settings."
        )
        return []

    # Check if guardrails are enabled
    guardrails_enabled = os.getenv("GUARDRAILS_ENABLED", "false").lower() == "true"
    if not guardrails_enabled:
        logger.info("ℹ️ Guardrails are disabled. Returning empty safety settings.")
        return []

    # Read guardrail configuration
    guardrail_config = read_guardrail_from_gcs(bucket_name, file_name)

    if guardrail_config is None:
        logger.warning(
            "⚠️ Failed to read guardrail configuration. Returning empty safety settings."
        )
        return []

    # Construct and return safety settings
    return construct_safety_settings(guardrail_config)


def get_safety_settings_from_file(file_path: str) -> List[SafetySetting]:
    """Read guardrail configuration from local file and return safety_settings."""
    try:
        with open(file_path, "r") as f:
            guardrail_config = json.load(f)

        logger.info(f"✅ Successfully loaded guardrail configuration from {file_path}")
        return construct_safety_settings(guardrail_config)

    except FileNotFoundError:
        logger.error(f"❌ Guardrail file not found: {file_path}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"❌ Error parsing JSON from {file_path}: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"❌ Error reading guardrail from file: {str(e)}")
        return []


def save_guardrail_to_file(
    guardrail_config: Dict, file_path: str = "guardrail.json", indent: int = 2
) -> bool:
    """Save guardrail configuration to a local file."""
    try:
        with open(file_path, "w") as f:
            json.dump(guardrail_config, f, indent=indent)

        logger.info(f"✅ Successfully saved guardrail configuration to {file_path}")
        return True

    except Exception as e:
        logger.error(f"❌ Error saving guardrail to file: {str(e)}")
        return False


def safety_settings_download_callback(
    callback_context: CallbackContext,
) -> Optional[Content]:
    """Download guardrail configuration from GCS and save it locally."""
    try:
        logger.info("🔄 Starting guardrail download callback")
        # Check if guardrails are enabled first
        guardrails_enabled = os.getenv("GUARDRAILS_ENABLED", "false").lower() == "true"
        if not guardrails_enabled:
            logger.info("ℹ️ Guardrails are disabled, skipping download")
            return None

        user_error_msg = "Unexpected error in applying guardrails"
        # Then check for bucket configuration
        bucket_name = os.getenv("GUARDRAIL_BUCKET_NAME")
        if not bucket_name:
            logger.error("⚠️ GUARDRAIL_BUCKET_NAME environment variable not set")
            return Content(parts=[{"text": user_error_msg}], role="user")

        file_name = os.getenv("GUARDRAIL_FILE", "guardrail.json")
        local_path = os.path.join(os.getcwd(), file_name)

        bucket_prefix = os.getenv("GUARDRAIL_BUCKET_PREFIX")
        if bucket_prefix:
            file_path = f"{bucket_prefix}/{file_name}"

        logger.info(f"📥 Downloading from gs://{bucket_name}/{file_path}")

        guardrail_config = read_guardrail_from_gcs(bucket_name, file_path)

        if guardrail_config is None:
            error_msg = f"❌ Failed to fetch guardrail configuration"
            logger.error(error_msg)
            return Content(parts=[{"text": user_error_msg}], role="user")

        success = save_guardrail_to_file(guardrail_config, local_path)

        if success:
            success_msg = f"✅ Guardrail saved to {local_path}"
            logger.info(success_msg)
            return None
        else:
            error_msg = f"❌ Failed to save guardrail configuration"
            logger.error(error_msg)
            return Content(parts=[{"text": user_error_msg}], role="user")

    except Exception as e:
        error_msg = f"❌ Error in safety settings loader callback: {str(e)}"
        logger.error(error_msg)
        return Content(parts=[{"text": user_error_msg}], role="user")


def safety_settings_model_callback(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> None:
    """Apply safety settings from local file to LLM request config."""
    try:
        logger.info("🔄 Starting guardrail model callback")
        guardrails_enabled = os.getenv("GUARDRAILS_ENABLED", "false").lower() == "true"
        if not guardrails_enabled:
            logger.info("ℹ️ Guardrails are disabled")
            return None

        file_name = os.getenv("GUARDRAIL_FILE", "guardrail.json")
        local_path = os.path.join(os.getcwd(), file_name)

        if not os.path.exists(local_path):
            logger.error(f"⚠️ Guardrail file not found: {local_path}")
            return None

        logger.info(f"📖 Loading safety settings from {local_path}")

        safety_settings = get_safety_settings_from_file(local_path)

        if not safety_settings:
            logger.warning("⚠️ No safety settings loaded")
            return None

        llm_request.config.safety_settings = safety_settings
        logger.info(f"🔒 Applied {len(safety_settings)} safety settings")
        return None

    except Exception as e:
        logger.error(f"❌ Error in safety settings model callback: {str(e)}")
        return None
