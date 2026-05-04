"""Tests for root_agent/agent.py — fetch_arize_secrets."""

import sys
import os
import ast
import textwrap

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import pytest
from unittest.mock import patch, MagicMock


class TestFetchArizeSecrets:
    """Test fetch_arize_secrets by loading it with mocked dependencies."""

    def _get_fetch_fn(self):
        """Load agent.py source and extract fetch_arize_secrets with mocked deps."""
        src_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../src/root_agent/agent.py")
        )
        with open(src_path, "r", encoding="utf-8") as f:
            source = f.read()

        ns = {
            "__name__": "test_agent_module",
            "__file__": src_path,
            "os": os,
        }
        mock_config = MagicMock()
        ns["config"] = mock_config

        mock_logger = MagicMock()
        ns["logger"] = mock_logger

        mock_secretmanager = MagicMock()
        ns["secretmanager"] = mock_secretmanager

        tree = ast.parse(source)
        func_source = None
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "fetch_arize_secrets":
                func_source = ast.get_source_segment(source, node)
                break

        if func_source:
            exec(compile(ast.parse(func_source), "<test>", "exec"), ns)

        return ns.get("fetch_arize_secrets"), mock_config, mock_secretmanager, mock_logger

    def test_secrets_not_configured(self):
        fn, mock_config, mock_sm, mock_logger = self._get_fetch_fn()
        mock_config.arize_space_id_name = None
        mock_config.arize_api_key_name = None
        result = fn()
        assert result == (None, None)

    def test_secrets_retrieved_successfully(self):
        fn, mock_config, mock_sm, mock_logger = self._get_fetch_fn()
        mock_config.gcp_secret_manager_project = "proj"
        mock_config.arize_space_id_name = "space_secret"
        mock_config.arize_api_key_name = "key_secret"

        mock_client = MagicMock()
        mock_sm.SecretManagerServiceClient.return_value = mock_client

        mock_resp1 = MagicMock()
        mock_resp1.payload.data.decode.return_value = "space123"
        mock_resp2 = MagicMock()
        mock_resp2.payload.data.decode.return_value = "key456"
        mock_client.access_secret_version.side_effect = [mock_resp1, mock_resp2]

        space_id, api_key = fn()
        assert space_id == "space123"
        assert api_key == "key456"

    def test_space_id_retrieval_fails(self):
        fn, mock_config, mock_sm, mock_logger = self._get_fetch_fn()
        mock_config.gcp_secret_manager_project = "proj"
        mock_config.arize_space_id_name = "s"
        mock_config.arize_api_key_name = "k"

        mock_client = MagicMock()
        mock_sm.SecretManagerServiceClient.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.payload.data.decode.return_value = "key456"
        mock_client.access_secret_version.side_effect = [Exception("fail"), mock_resp]

        space_id, api_key = fn()
        assert space_id is None
        assert api_key == "key456"

    def test_outer_exception(self):
        fn, mock_config, mock_sm, mock_logger = self._get_fetch_fn()
        mock_config.gcp_secret_manager_project = "proj"
        mock_config.arize_space_id_name = "s"
        mock_config.arize_api_key_name = "k"
        mock_sm.SecretManagerServiceClient.side_effect = Exception("total fail")

        result = fn()
        assert result == (None, None)
