"""
Unit tests for data_update.py
Tests Portal API integration for agent status updates
"""
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

# Mock ALL required environment variables BEFORE importing modules
os.environ.setdefault('DATA_APP_API_URL', 'https://test-api.example.com')
os.environ.setdefault('CLOUDRUN_SERVICE_URL', 'https://test-cloudrun.example.com')
os.environ.setdefault('PROJECT_ID', 'test-project')
os.environ.setdefault('REGION', 'us-central1')
os.environ.setdefault('AGENT_DISPLAY_NAME', 'test-agent')

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Import functions at module level (after env vars are set)
from data_update import (  # type: ignore
    _get_id_token,
    update_data,
    update_agent,
    main
)


class TestDataUpdate:
    """Test suite for data_update.py functions"""
    
    @patch('data_update.id_token.fetch_id_token')
    def test_get_id_token_success(self, mock_fetch_token):
        """Test successful ID token retrieval"""
        mock_fetch_token.return_value = "test-token-67890"
        
        token = _get_id_token("https://test-service.run.app")
        
        assert token == "test-token-67890"
        mock_fetch_token.assert_called_once()
    
    @patch('data_update.id_token.fetch_id_token')
    def test_get_id_token_failure(self, mock_fetch_token):
        """Test ID token retrieval failure"""
        mock_fetch_token.side_effect = Exception("Auth failed")
        
        token = _get_id_token("https://test-service.run.app")
        
        assert token is None
    
    @patch('data_update.requests.put')
    @patch('data_update._get_id_token')
    def test_update_data_with_authentication(self, mock_get_token, mock_put):
        """Test making authenticated PUT request"""
        mock_get_token.return_value = "test-token"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "updated": True}
        mock_response.headers = {}
        mock_put.return_value = mock_response
        
        result = update_data(
            querystringparameters={"agent_name": "test-agent"},
            data={"status": "Ready"},
            path="/updateagent/"
        )
        
        assert result == {"success": True, "updated": True}
        
        # Verify request was made with correct parameters
        mock_put.assert_called_once()
        call_kwargs = mock_put.call_args.kwargs
        assert call_kwargs['params'] == {"agent_name": "test-agent"}
        assert call_kwargs['json'] == {"status": "Ready"}
        assert call_kwargs['headers']['Authorization'] == "Bearer test-token"
    
    @patch('data_update.requests.put')
    @patch('data_update._get_id_token')
    def test_update_data_without_token(self, mock_get_token, mock_put):
        """Test making PUT request when token is unavailable"""
        mock_get_token.return_value = None
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.headers = {}
        mock_put.return_value = mock_response
        
        result = update_data(
            querystringparameters={},
            data={"status": "Ready"},
            path="/updateagent/"
        )
        
        assert result == {"success": True}
        
        # Verify Authorization header was not added
        call_kwargs = mock_put.call_args.kwargs
        assert 'Authorization' not in call_kwargs['headers']
    
    @patch('data_update.requests.put')
    @patch('data_update._get_id_token')
    def test_update_data_with_http_error(self, mock_get_token, mock_put):
        """Test handling of HTTP errors"""
        mock_get_token.return_value = "test-token"
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("Not found")
        mock_put.return_value = mock_response
        
        with pytest.raises(Exception) as exc_info:
            update_data(
                querystringparameters={},
                data={},
                path="/updateagent/"
            )
        
        assert "Not found" in str(exc_info.value)
    
    @patch('data_update.update_data')
    def test_update_agent_with_all_parameters(self, mock_update_data):
        """Test updating agent with all parameters"""
        mock_update_data.return_value = {"success": True}
        
        result = update_agent(
            agent_name="test-agent",
            agent_base_id="12345",
            agent_alias_id="projects/test/locations/us-central1/reasoningEngines/12345",
            agent_url="https://console.cloud.google.com/vertex-ai/agents/...",
            status="Ready"
        )
        
        assert result == {"success": True}
        
        # Verify update_data was called with correct structure
        mock_update_data.assert_called_once()
        call_args = mock_update_data.call_args
        
        data_payload = call_args.kwargs['data']
        assert data_payload['agentName'] == "test-agent"
        assert data_payload['agentBaseId'] == "12345"
        assert data_payload['agentAliasId'] == "projects/test/locations/us-central1/reasoningEngines/12345"
        assert data_payload['agentUrl'] == "https://console.cloud.google.com/vertex-ai/agents/..."
        assert data_payload['status'] == "Ready"
        
        # Verify query parameters
        assert call_args.kwargs['querystringparameters'] == {"agent_name": "test-agent"}
        assert call_args.kwargs['path'] == "/updateagent/"
    
    @patch('data_update.update_agent')
    def test_main_update_agent_command(self, mock_update_agent):
        """Test main function with update_agent command"""
        mock_update_agent.return_value = {"success": True}
        
        main([
            "update_agent",
            "agent-base-123",
            "agent-alias-456",
            "https://console.cloud.google.com",
            "Ready"
        ])
        
        # Verify update_agent was called with correct parameters
        mock_update_agent.assert_called_once()
        call_args = mock_update_agent.call_args[0]
        
        # First arg is agent_name (from config)
        assert call_args[1] == "agent-base-123"
        assert call_args[2] == "agent-alias-456"
        assert call_args[3] == "https://console.cloud.google.com"
        assert call_args[4] == "Ready"
    
    @patch('data_update.update_agent')
    def test_main_reads_from_json_file(self, mock_update_agent, monkeypatch, tmp_path):
        """Test that main function reads placeholder values from JSON file"""
        # Create mock JSON file with agent data (using correct key names!)
        output_file = tmp_path / "agent_output.json"
        agent_data = {
            "agent_base_id": "real-base-id-123",
            "agent_alias_id": "real-alias-id-456",
            "agent_url": "https://real-url.example.com"
        }
        with open(output_file, 'w') as f:
            json.dump(agent_data, f)
        
        # Mock open to return our test file
        original_open = open
        def mock_open_func(path, *args, **kwargs):
            if '/workspace/agent_output.json' in str(path):
                return original_open(str(output_file), *args, **kwargs)
            return original_open(path, *args, **kwargs)
        
        monkeypatch.setattr('builtins.open', mock_open_func)
        
        mock_update_agent.return_value = {"success": True}
        
        main([
            "update_agent",
            "AGENT_BASE_ID",
            "AGENT_ALIAS_ID",
            "AGENT_URL",
            "Ready"
        ])
        
        # Verify real values from JSON were used
        call_args = mock_update_agent.call_args[0]
        assert call_args[1] == "real-base-id-123"
        assert call_args[2] == "real-alias-id-456"
        assert call_args[3] == "https://real-url.example.com"
    
    @patch('data_update.update_agent')
    def test_main_handles_missing_json_file(self, mock_update_agent, monkeypatch):
        """Test main function handles missing JSON file gracefully"""
        # Mock FileNotFoundError
        original_open = open
        def mock_open_func(path, *args, **kwargs):
            if '/workspace/agent_output.json' in str(path):
                raise FileNotFoundError("File not found")
            return original_open(path, *args, **kwargs)
        
        monkeypatch.setattr('builtins.open', mock_open_func)
        
        mock_update_agent.return_value = {"success": True}
        
        main([
            "update_agent",
            "AGENT_BASE_ID",
            "AGENT_ALIAS_ID",
            "AGENT_URL",
            "Ready"
        ])
        
        # Verify placeholders were used
        call_args = mock_update_agent.call_args[0]
        assert call_args[1] == "AGENT_BASE_ID"
        assert call_args[2] == "AGENT_ALIAS_ID"
        assert call_args[3] == "AGENT_URL"
    
    def test_main_with_invalid_subcommand(self):
        """Test main function with invalid subcommand"""
        with pytest.raises(SystemExit):
            main(["invalid_command"])
    
    def test_main_with_missing_arguments(self):
        """Test main function with missing required arguments"""
        with pytest.raises(SystemExit):
            main(["update_agent"])  # Missing required positional arguments
    
    @patch('data_update.update_data')
    def test_update_agent_builds_correct_url(self, mock_update_data):
        """Test that update_agent uses correct API endpoint"""
        mock_update_data.return_value = {"success": True}
        
        update_agent(
            agent_name="test-agent",
            agent_base_id="123",
            agent_alias_id="456",
            agent_url="https://test.com",
            status="Ready"
        )
        
        call_args = mock_update_data.call_args
        assert call_args.kwargs['path'] == "/updateagent/"
        assert call_args.kwargs['querystringparameters'] == {"agent_name": "test-agent"}
    
    @patch('data_update.update_data')
    def test_update_agent_with_different_statuses(self, mock_update_data):
        """Test updating agent with different status values"""
        mock_update_data.return_value = {"success": True}
        
        test_statuses = ["Ready", "In Progress", "Failed", "Deploying"]
        
        for status in test_statuses:
            update_agent(
                agent_name="test-agent",
                agent_base_id="123",
                agent_alias_id="456",
                agent_url="https://test.com",
                status=status
            )
            
            call_args = mock_update_data.call_args
            data_payload = call_args.kwargs['data']
            assert data_payload['status'] == status
    
    @patch('data_update.requests.put')
    @patch('data_update._get_id_token')
    def test_update_data_logs_response_correctly(self, mock_get_token, mock_put):
        """Test that response is logged for debugging"""
        mock_get_token.return_value = "test-token"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = '{"success": true}'
        mock_put.return_value = mock_response
        
        result = update_data(
            querystringparameters={},
            data={"status": "Ready"},
            path="/updateagent/"
        )
        
        assert result == {"success": True}
