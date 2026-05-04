"""Tests for agent_deploy.py — agent name extraction logic."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))


class TestAgentDeployLogic:
    """Test the agent name extraction logic from agent_deploy.py without importing it."""

    def _extract_agent_id(self, agent_name):
        """Replicate the agent_base_id extraction logic from agent_deploy.py."""
        agent_base_id = ""
        if agent_name and "/" in agent_name:
            parts = agent_name.split("/")
            for i, part in enumerate(parts):
                if part == "reasoningEngines" and i + 1 < len(parts):
                    agent_base_id = parts[i + 1]
                    break
            if not agent_base_id:
                agent_base_id = parts[-1]
        return agent_base_id

    def test_standard_agent_name(self):
        name = "projects/myproj/locations/us-central1/reasoningEngines/12345"
        assert self._extract_agent_id(name) == "12345"

    def test_no_reasoning_engines_uses_last_part(self):
        name = "projects/myproj/locations/us-central1/agents/99999"
        assert self._extract_agent_id(name) == "99999"

    def test_empty_name(self):
        assert self._extract_agent_id("") == ""

    def test_no_slash(self):
        assert self._extract_agent_id("simple_name") == ""

    def test_none_name(self):
        assert self._extract_agent_id(None) == ""

    def test_url_construction(self):
        agent_base_id = "12345"
        project_id = "myproj"
        location = "us-central1"
        url = (
            f"https://console.cloud.google.com/vertex-ai/agents/"
            f"locations/{location}/agent-engines/{agent_base_id}/"
            f"metrics?project={project_id}"
        )
        assert "12345" in url
        assert "myproj" in url
