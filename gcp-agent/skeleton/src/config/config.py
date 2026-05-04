"""Configuration management for GCP Vertex AI Agent."""

import os
from typing import Optional
import requests
from .config_reader import ConfigReader
from utils.log_helper import setup_logging
logger = setup_logging()

# Load configuration from JSON file using existing config_reader
config = ConfigReader(os.path.join(os.path.dirname(__file__), "..", "..", "config", "configuration.json"))

# Environment configuration
PROJECT_ID = config.get_value("PROJECT_ID")
DATA_APP_API_URL = os.getenv("DATA_APP_API_URL")
CLOUDRUN_SERVICE_URL = os.getenv("CLOUDRUN_SERVICE_URL")
SERVICE_ACCOUNT_NAME = os.getenv('SERVICE_ACCOUNT_NAME')
# Agent configuration from JSON
AGENT_DISPLAY_NAME = config.get_value("AGENT_DISPLAY_NAME")
SYSTEM_INSTRUCTION = config.get_value("SYSTEM_INSTRUCTION")
MODEL_NAME = config.get_value("MODEL_NAME")
REGION = config.get_value("REGION")

# Groundtruth configuration
ENABLE_GROUNDTRUTH = config.get_value("ENABLE_GROUNDTRUTH", False)
if isinstance(ENABLE_GROUNDTRUTH, str):
    ENABLE_GROUNDTRUTH = ENABLE_GROUNDTRUTH.strip().lower() == "true"
if ENABLE_GROUNDTRUTH:
    logger.info("✅ Ground Truth is enabled.")
    GROUNDTRUTH_NAME = config.get_value("GROUNDTRUTH_NAME", "")
else:
    logger.info("❌ Ground Truth is disabled.")
    GROUNDTRUTH_NAME = None

ENABLE_GENERAL_GROUNDTRUTH = config.get_value("ENABLE_GENERAL_GROUNDTRUTH", False)
if isinstance(ENABLE_GENERAL_GROUNDTRUTH, str):
    ENABLE_GENERAL_GROUNDTRUTH = ENABLE_GENERAL_GROUNDTRUTH.strip().lower() == "true"   
if ENABLE_GENERAL_GROUNDTRUTH:
    logger.info("✅ General Ground Truth is enabled.")
    GENERAL_GROUNDTRUTH_NAME = config.get_value("GENERAL_GROUNDTRUTH_NAME", "")
else:
    logger.info("❌ General Ground Truth is disabled.")
    GENERAL_GROUNDTRUTH_NAME = None

# Additional agent configuration
AGENT_DESCRIPTION = config.get_value("AGENT_DESCRIPTION", "")
LOCATION = config.get_value("LOCATION", REGION)
STAGING_BUCKET_NAME = config.get_value("STAGING_BUCKET_NAME", "")
STAGING_BUCKET = f"gs://{STAGING_BUCKET_NAME}" if STAGING_BUCKET_NAME else ""
AGENT_PROMPT = config.get_value("AGENT_PROMPT", "")
GENERAL_EVALUATION = config.get_value("GENERAL_EVALUATION", "false")
GENERAL_EVALUATION_FILE = config.get_value("GENERAL_EVALUATION_FILE", "")
RAGAS_EVALUATION = config.get_value("RAGAS_EVALUATION", "false")
RAGAS_EVALUATION_FILE = config.get_value("RAGAS_EVALUATION_FILE", "")

GUARDRAILS_ENABLED = config.get_value("GUARDRAILS_ENABLED", False)
if isinstance(GUARDRAILS_ENABLED, str):
    GUARDRAILS_ENABLED = GUARDRAILS_ENABLED.strip().lower() == "true"

if GUARDRAILS_ENABLED:
    logger.info("🛡️ Guardrail is enabled.")
    GUARDRAIL_NAME = config.get_value("GUARDRAIL_NAME")
    GUARDRAIL_URL = config.get_value("GUARDRAIL_URL") # E.g.: "https://storage.cloud.google.com/BUCKETNAME/FOLDER1/FOLDER2/guardrail.json"
    GUARDRAIL_BUCKET_NAME = GUARDRAIL_URL.split("/")[3] if GUARDRAIL_URL else None # E.g.: "BUCKETNAME"
    GUARDRAIL_BUCKET_PREFIX = "/".join(GUARDRAIL_URL.split("/")[4:-1]) if GUARDRAIL_URL else None # E.g.: "FOLDER1/FOLDER2"
    guardrail_file_name = GUARDRAIL_URL.split("/")[-1] if GUARDRAIL_URL else None # E.g.: "guardrail.json"
else:
    logger.info("❌ Guardrail is disabled.")
    GUARDRAIL_NAME = None
    GUARDRAIL_URL = None
    GUARDRAIL_BUCKET_NAME = None
    GUARDRAIL_BUCKET_PREFIX = None
    guardrail_file_name = None

# Arize configuration
ARIZE_SPACE_ID_NAME = config.get_value("ARIZE_SPACE_ID_NAME", "")
ARIZE_API_KEY_NAME = config.get_value("ARIZE_API_KEY_NAME", "")
ARIZE_ENDPOINT = config.get_value("ARIZE_ENDPOINT", "")
GCP_SECRET_MANAGER_PROJECT = config.get_value("GCP_SECRET_MANAGER_PROJECT", "")

MCP_SERVER_URL = config.get_value("MCP_SERVER_URL", "")

NETWORK_ATTACHMENT = os.getenv("NETWORK_ATTACHMENT")
DNS_PEERING_DOMAIN = os.getenv("DNS_PEERING_DOMAIN")
DNS_PEERING_DOMAIN_TARGET_PROJECT = os.getenv("DNS_PEERING_DOMAIN_TARGET_PROJECT")
DNS_PEERING_DOMAIN_TARGET_NETWORK = os.getenv("DNS_PEERING_DOMAIN_TARGET_NETWORK")
