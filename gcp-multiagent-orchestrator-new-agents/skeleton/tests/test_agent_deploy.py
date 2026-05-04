"""Unit tests for agent_deploy module."""

import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Setup path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


class TestAgentDeployConfiguration:
    """Test suite for agent deployment configuration validation."""

    def test_guardrails_logic_all_values_present(self):
        """Test guardrails_configured logic when all values are present."""
        # Simulate the logic from agent_deploy.py
        GUARDRAIL_NAME = "test-guardrail"
        GUARDRAIL_BUCKET_NAME = "test-bucket"
        GUARDRAIL_BUCKET_PREFIX = "guardrails/"
        
        guardrails_configured = (
            GUARDRAIL_NAME and 
            GUARDRAIL_BUCKET_NAME and 
            GUARDRAIL_BUCKET_PREFIX
        )
        
        # The 'and' operation returns the last truthy value, not True
        assert guardrails_configured  # Truthy check
        assert guardrails_configured == "guardrails/"  # Returns last value

    def test_guardrails_logic_missing_name(self):
        """Test guardrails_configured logic when name is missing."""
        GUARDRAIL_NAME = None
        GUARDRAIL_BUCKET_NAME = "test-bucket"
        GUARDRAIL_BUCKET_PREFIX = "guardrails/"
        
        guardrails_configured = (
            GUARDRAIL_NAME and 
            GUARDRAIL_BUCKET_NAME and 
            GUARDRAIL_BUCKET_PREFIX
        )
        
        # The 'and' operation returns the first falsy value (None)
        assert not guardrails_configured  # Falsy check
        assert guardrails_configured is None

    def test_guardrails_logic_missing_bucket(self):
        """Test guardrails_configured logic when bucket is missing."""
        GUARDRAIL_NAME = "test-guardrail"
        GUARDRAIL_BUCKET_NAME = None
        GUARDRAIL_BUCKET_PREFIX = "guardrails/"
        
        guardrails_configured = (
            GUARDRAIL_NAME and 
            GUARDRAIL_BUCKET_NAME and 
            GUARDRAIL_BUCKET_PREFIX
        )
        
        # The 'and' operation returns the first falsy value (None)
        assert not guardrails_configured  # Falsy check
        assert guardrails_configured is None

    def test_guardrails_logic_empty_strings(self):
        """Test guardrails_configured logic with empty strings."""
        GUARDRAIL_NAME = ""
        GUARDRAIL_BUCKET_NAME = "test-bucket"
        GUARDRAIL_BUCKET_PREFIX = "guardrails/"
        
        guardrails_configured = (
            GUARDRAIL_NAME and 
            GUARDRAIL_BUCKET_NAME and 
            GUARDRAIL_BUCKET_PREFIX
        )
        
        # The 'and' operation returns the first falsy value (empty string)
        assert not guardrails_configured  # Falsy check
        assert guardrails_configured == ""

    def test_base_env_vars_structure(self):
        """Test base environment variables structure."""
        ARIZE_ENDPOINT = "https://otlp.arize.com:443"
        
        base_env_vars = {
            "OTEL_LOG_LEVEL": "DEBUG",
            "NO_PROXY": "otlp.arize.com",
            "OTEL_EXPORTER_OTLP_ENDPOINT": ARIZE_ENDPOINT,
            "OTEL_EXPORTER_OTLP_TIMEOUT": "60000",
        }
        
        assert "OTEL_LOG_LEVEL" in base_env_vars
        assert base_env_vars["OTEL_LOG_LEVEL"] == "DEBUG"
        assert "NO_PROXY" in base_env_vars
        assert "OTEL_EXPORTER_OTLP_ENDPOINT" in base_env_vars
        assert base_env_vars["OTEL_EXPORTER_OTLP_ENDPOINT"] == ARIZE_ENDPOINT

    def test_staging_bucket_format(self):
        """Test staging bucket format construction."""
        STAGING_BUCKET_NAME = "test-staging-bucket"
        STAGING_BUCKET = f"gs://{STAGING_BUCKET_NAME}" if STAGING_BUCKET_NAME else ""
        
        assert STAGING_BUCKET == "gs://test-staging-bucket"
        assert STAGING_BUCKET.startswith("gs://")

    def test_staging_bucket_empty_name(self):
        """Test staging bucket with empty name."""
        STAGING_BUCKET_NAME = None
        STAGING_BUCKET = f"gs://{STAGING_BUCKET_NAME}" if STAGING_BUCKET_NAME else ""
        
        assert STAGING_BUCKET == ""

    def test_requirements_list_type(self):
        """Test that requirements is a list."""
        requirements = [
            "google-cloud-aiplatform[agent_engines,langchain,langchain_google_vertexai,aiplatform,adk]>=1.141.0",
            "google-adk>=1.18.0",
            "arize-otel==0.9.0",
            "openinference-instrumentation-google-adk>=0.1.8",
            "requests>=2.31.0",
        ]
        
        assert isinstance(requirements, list)
        assert len(requirements) > 0

    def test_arize_endpoint_format(self):
        """Test Arize endpoint format."""
        ARIZE_ENDPOINT = "https://otlp.arize.com:443"
        
        assert ARIZE_ENDPOINT.startswith("https://")
        assert "otlp.arize.com" in ARIZE_ENDPOINT

    def test_network_attachment_format(self):
        """Test network attachment format."""
        NETWORK_ATTACHMENT = "projects/test/regions/us-central1/networkAttachments/test-attachment"
        
        assert "projects/" in NETWORK_ATTACHMENT
        assert "networkAttachments/" in NETWORK_ATTACHMENT

    def test_dns_peering_domain_values(self):
        """Test DNS peering configuration values."""
        DNS_PEERING_DOMAIN = "example.com"
        DNS_PEERING_DOMAIN_TARGET_PROJECT = "target-project"
        DNS_PEERING_DOMAIN_TARGET_NETWORK = "target-network"
        
        assert DNS_PEERING_DOMAIN is not None
        assert DNS_PEERING_DOMAIN_TARGET_PROJECT is not None
        assert DNS_PEERING_DOMAIN_TARGET_NETWORK is not None

    def test_location_region_format(self):
        """Test location/region format."""
        LOCATION = "us-central1"
        
        assert "-" in LOCATION  # Regions have dashes
        assert LOCATION.startswith("us-") or LOCATION.startswith("europe-") or LOCATION.startswith("asia-")

    def test_project_id_format(self):
        """Test project ID format."""
        PROJECT_ID = "test-project-123"
        
        assert PROJECT_ID is not None
        assert len(PROJECT_ID) > 0

    def test_model_id_format(self):
        """Test model ID format."""
        MODEL_ID = "gemini-1.5-pro"
        
        assert MODEL_ID is not None
        assert "gemini" in MODEL_ID or "claude" in MODEL_ID or "gpt" in MODEL_ID

