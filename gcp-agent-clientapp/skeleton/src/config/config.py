"""Configuration management for GCP Vertex AI Agent."""

import os
from typing import Optional
from .config_reader import ConfigReader

from utils.log_helper import setup_logging
logger = setup_logging()

# Load configuration from JSON file using existing config_reader
config = ConfigReader(os.path.join(os.path.dirname(__file__), "..", "..", "config", "configuration.json"))

# Environment configuration
PROJECT_ID = config.get_value("PROJECT_ID")
REGION = config.get_value("REGION")
AGENT_ID = config.get_value("AGENT_ID")
PROJECT_NUMBER = config.get_value("PROJECT_NUMBER")
AGENT_URL = f"projects/{PROJECT_NUMBER}/locations/{REGION}/reasoningEngines/{AGENT_ID}"
NAME = config.get_value("NAME")
DESCRIPTION = config.get_value("DESCRIPTION")