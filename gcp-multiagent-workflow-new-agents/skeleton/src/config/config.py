"""Configuration management for GCP project settings."""

import os
from typing import Optional

import requests
from dotenv import load_dotenv
from .config_reader import ConfigReader
from utils.log_helper import setup_logging

load_dotenv()
logger = setup_logging()

config = ConfigReader(os.path.join(os.path.dirname(__file__), "root-agent-config.yaml"))



# Environment configuration
ENVIRONMENT = os.getenv("ENVIRONMENT")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
SERVICE_ACCOUNT_NAME = os.getenv("SERVICE_ACCOUNT_NAME")
STAGING_BUCKET_NAME = os.getenv("STAGING_BUCKET_NAME")
STAGING_BUCKET = f"gs://{STAGING_BUCKET_NAME}" if STAGING_BUCKET_NAME else ""

DATA_APP_API_URL = os.getenv("DATA_APP_API_URL")
CLOUDRUN_SERVICE_URL = os.getenv("CLOUDRUN_SERVICE_URL")
# Root agent configuration
root_agent = config.get_value("root_agent", {})
PROJECT_ID = root_agent.get("project_id")
LOCATION = root_agent.get("region")
agent_display_name = root_agent.get("agent_display_name")
agent_class = root_agent.get("agent_class")
multiagent = root_agent.get("multiagent")
model_id = root_agent.get("model_id")
description = root_agent.get("description")


guardrail_enabled = root_agent.get("guardrail_enabled", False)
if isinstance(guardrail_enabled, str):
    guardrail_enabled = guardrail_enabled.strip().lower() == "true"

if guardrail_enabled:
    logger.info("🛡️ Guardrail is enabled.")
    guardrail_name = root_agent.get("guardrail_name")
    guardrail_url = root_agent.get("guardrail_url") # E.g.: "https://storage.cloud.google.com/BUCKETNAME/FOLDER1/FOLDER2/guardrail.json"
    bucket_name = guardrail_url.split("/")[3] if guardrail_url else None # E.g.: "BUCKETNAME"
    GUARDRAIL_BUCKET_PREFIX = "/".join(guardrail_url.split("/")[4:-1]) if guardrail_url else None # E.g.: "FOLDER1/FOLDER2"
    guardrail_file_name = guardrail_url.split("/")[-1] if guardrail_url else None # E.g.: "guardrail.json"
else:
    logger.info("❌ Guardrail is disabled.")
    guardrail_name = None
    guardrail_url = None
    bucket_name = None
    GUARDRAIL_BUCKET_PREFIX = None
    guardrail_file_name = None

global_instruction = root_agent.get("global_instruction")
instruction = root_agent.get("instruction")

# Ground Truth Configuration
enable_groundtruth = root_agent.get("enable_groundtruth", False)
if isinstance(enable_groundtruth, str):
    enable_groundtruth = enable_groundtruth.strip().lower() == "true"
if enable_groundtruth:
    logger.info("✅ Ground Truth is enabled ")
    groundtruth_name = root_agent.get("groundtruth_name", "")
else:
    logger.info("❌ Ground Truth is disabled ")
    groundtruth_name = None

# General Ground Truth Configuration
enable_general_groundtruth = root_agent.get("enable_general_groundtruth", False)
if isinstance(enable_general_groundtruth, str):
    enable_general_groundtruth = enable_general_groundtruth.strip().lower() == "true"
if enable_general_groundtruth:
    logger.info("✅ General Ground Truth is enabled ")
    general_groundtruth_name = root_agent.get("general_groundtruth_name", "")
else:
    logger.info("❌ General Ground Truth is disabled ")
    general_groundtruth_name = None

# dataset name for root agent - not used right now.
dataset_name = root_agent.get("dataset_name", "")

NETWORK_ATTACHMENT = os.getenv("NETWORK_ATTACHMENT")
DNS_PEERING_DOMAIN = os.getenv("DNS_PEERING_DOMAIN")
DNS_PEERING_DOMAIN_TARGET_PROJECT = os.getenv("DNS_PEERING_DOMAIN_TARGET_PROJECT")
DNS_PEERING_DOMAIN_TARGET_NETWORK = os.getenv("DNS_PEERING_DOMAIN_TARGET_NETWORK")

# Arize observability configuration
arize_space_id_name = root_agent.get("arize_space_id_name")
arize_api_key_name = root_agent.get("arize_api_key_name")
arize_endpoint = root_agent.get("arize_endpoint")
gcp_secret_manager_project = root_agent.get("gcp_secret_manager_project")
