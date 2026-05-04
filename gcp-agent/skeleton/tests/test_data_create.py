"""
Unit tests for data_create.py
Tests Portal API integration for agent creation
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
os.environ.setdefault('SYSTEM_INSTRUCTION', 'Test instruction')
os.environ.setdefault('MODEL_NAME', 'gemini-2.0-flash-001')
os.environ.setdefault('GUARDRAIL_NAME', '')
os.environ.setdefault('GROUNDTRUTH_NAME', '')
os.environ.setdefault('GENERAL_GROUNDTRUTH_NAME', '')

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Import functions at module level (after env vars are set)
from data_create import (  # type: ignore
    _get_dataset_name,
    _extract_and_store_gcspaths,
    _get_id_token,
    create_data,
    create_agent,
    main
)


class TestDataCreate:
    """Test suite for data_create.py functions"""
    
    def test_get_dataset_name_with_valid_config(self, temp_rag_config_file):
        """Test extracting dataset name from valid RAG config"""
        dataset_name = _get_dataset_name(str(temp_rag_config_file))
        
        assert dataset_name == "test-knowledge-base"
    
    def test_get_dataset_name_with_nonexistent_file(self):
        """Test behavior when RAG config file doesn't exist"""
        dataset_name = _get_dataset_name("nonexistent_file.json")
        
        assert dataset_name == ""
    
    def test_get_dataset_name_with_missing_fields(self, tmp_path):
        """Test handling of malformed RAG config"""
        invalid_config = [{"some_field": "value"}]
        
        config_file = tmp_path / "invalid_rag.json"
        with open(config_file, 'w') as f:
            json.dump(invalid_config, f)
        
        dataset_name = _get_dataset_name(str(config_file))
        
        assert dataset_name == ""
    
    def test_extract_and_store_gcspaths_with_complete_response(self, tmp_path):
        """Test extracting GCS paths from API response"""
        response_data = {
            "raggroundtruthdatasetnames": [
                {
                    "versions": [
                        {"s3path": "gs://test-bucket/rag-gt.csv"}
                    ]
                }
            ],
            "generalgroundtruthdatasetnames": [
                {"s3path": "gs://test-bucket/general-gt.csv"}
            ]
        }
        
        mock_file = mock_open()
        
        with patch('builtins.open', mock_file):
            _extract_and_store_gcspaths(response_data)
            
            # Verify open was called with correct path
            mock_file.assert_called_once_with("/workspace/groundtruth_output.json", "w")
            
            # Verify the JSON data was written
            handle = mock_file()
            written_data = ''.join(call.args[0] for call in handle.write.call_args_list)
            data = json.loads(written_data)
            
            assert data["rag_groundtruth_gcs_path"] == "gs://test-bucket/rag-gt.csv"
            assert data["general_groundtruth_gcs_path"] == "gs://test-bucket/general-gt.csv"
    
    def test_extract_and_store_gcspaths_with_partial_response(self, tmp_path):
        """Test handling of response with only general ground truth"""
        response_data = {
            "raggroundtruthdatasetnames": [],
            "generalgroundtruthdatasetnames": [
                {"s3path": "gs://test-bucket/general-gt.csv"}
            ]
        }
        
        mock_file = mock_open()
        
        with patch('builtins.open', mock_file):
            _extract_and_store_gcspaths(response_data)
            
            # Verify the JSON data was written
            handle = mock_file()
            written_data = ''.join(call.args[0] for call in handle.write.call_args_list)
            data = json.loads(written_data)
            
            assert data["rag_groundtruth_gcs_path"] == ""
            assert data["general_groundtruth_gcs_path"] == "gs://test-bucket/general-gt.csv"
    
    @patch('data_create.id_token.fetch_id_token')
    def test_get_id_token_success(self, mock_fetch_token):
        """Test successful ID token retrieval"""
        mock_fetch_token.return_value = "test-token-12345"
        
        token = _get_id_token("https://test-service.run.app")
        
        assert token == "test-token-12345"
        mock_fetch_token.assert_called_once()
    
    @patch('data_create.id_token.fetch_id_token')
    def test_get_id_token_failure(self, mock_fetch_token):
        """Test ID token retrieval failure"""
        mock_fetch_token.side_effect = Exception("Auth failed")
        
        token = _get_id_token("https://test-service.run.app")
        
        assert token is None
    
    @patch('data_create.requests.post')
    @patch('data_create._get_id_token')
    def test_create_data_with_authentication(self, mock_get_token, mock_post):
        """Test making authenticated POST request"""
        mock_get_token.return_value = "test-token"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.headers = {}
        mock_post.return_value = mock_response
        
        result = create_data(
            querystringparameters={"param": "value"},
            data={"field": "data"},
            path="/test/"
        )
        
        assert result == {"success": True}
        
        # Verify request was made with correct parameters
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs['params'] == {"param": "value"}
        assert call_kwargs['json'] == {"field": "data"}
        assert call_kwargs['headers']['Authorization'] == "Bearer test-token"
    
    @patch('data_create.requests.post')
    @patch('data_create._get_id_token')
    def test_create_data_without_token(self, mock_get_token, mock_post):
        """Test making POST request when token is unavailable"""
        mock_get_token.return_value = None
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.headers = {}
        mock_post.return_value = mock_response
        
        result = create_data(
            querystringparameters={},
            data={"field": "data"},
            path="/test/"
        )
        
        assert result == {"success": True}
        
        # Verify Authorization header was not added
        call_kwargs = mock_post.call_args.kwargs
        assert 'Authorization' not in call_kwargs['headers']
    
    @patch('data_create.requests.post')
    @patch('data_create._get_id_token')
    def test_create_data_with_http_error(self, mock_get_token, mock_post):
        """Test handling of HTTP errors"""
        mock_get_token.return_value = "test-token"
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Server error")
        mock_post.return_value = mock_response
        
        with pytest.raises(Exception) as exc_info:
            create_data(
                querystringparameters={},
                data={},
                path="/test/"
            )
        
        assert "Server error" in str(exc_info.value)
    
    @patch('data_create.create_data')
    def test_create_agent_with_all_parameters(self, mock_create_data):
        """Test creating agent with all parameters"""
        mock_create_data.return_value = {"agentid": 123}
        
        result = create_agent(
            agent_name="test-agent",
            agent_instruction="Test instruction",
            model_name="gemini-2.0-flash-001",
            region_name="us-central1",
            dataset_name="test-dataset",
            guardrail_name="test-guardrail",
            groundtruth_names=["gt1"],
            general_groundtruth_names=[{"name": "general-gt"}],
            rag_groundtruth_names=[{"name": "rag-gt"}],
            action_groups=[],
            agent_status="In Progress",
            provider_id=3
        )
        
        assert result == {"agentid": 123}
        
        # Verify create_data was called with correct structure
        mock_create_data.assert_called_once()
        call_args = mock_create_data.call_args
        
        data_payload = call_args.kwargs['data']
        assert data_payload['agent_name'] == "test-agent"
        assert data_payload['modelname'] == "gemini-2.0-flash-001"
        assert data_payload['region_name'] == "us-central1"
        assert data_payload['datasetname'] == "test-dataset"
        assert 'guardrail' in data_payload
        assert data_payload['guardrail']['name'] == "test-guardrail"
    
    @patch('data_create.create_data')
    @patch('data_create.groundtruth_name', '')
    @patch('data_create.general_groundtruth_name', '')
    def test_create_agent_with_minimal_parameters(self, mock_create_data):
        """Test creating agent with only required parameters"""
        mock_create_data.return_value = {"agentid": 456}
        
        result = create_agent(
            agent_name="minimal-agent",
            agent_instruction="Do things",
            model_name="gemini-2.0-flash-001",
            region_name="us-central1"
        )
        
        assert result == {"agentid": 456}
        
        # Verify defaults were applied
        call_args = mock_create_data.call_args
        data_payload = call_args.kwargs['data']
        
        assert data_payload['agent_name'] == "minimal-agent"
        assert data_payload['groundtruthnames'] == []
        assert data_payload['generalgroundtruthnames'] == []
        assert data_payload['raggroundtruthnames'] == []
        assert data_payload['toolname'] == ""
        assert data_payload['actiongroupname'] == ""
    
    @patch('data_create.create_agent')
    @patch('data_create._extract_and_store_gcspaths')
    def test_main_create_agent_command(self, mock_extract, mock_create_agent, tmp_path):
        """Test main function with create_agent command"""
        # Mock the response
        mock_response = {
            "agentid": 123,
            "rag_run_id": 456,
            "general_run_id": 789,
            "raggroundtruthdatasetnames": [],
            "generalgroundtruthdatasetnames": []
        }
        mock_create_agent.return_value = mock_response
        
        # Mock file operations
        mock_file = mock_open()
        
        with patch('builtins.open', mock_file):
            main(["create_agent"])
        
        # Verify agent was created
        mock_create_agent.assert_called_once()
        
        # Verify GCS paths extraction was called
        mock_extract.assert_called_once_with(mock_response)
        
        # Verify file write was called
        mock_file.assert_called_with("/workspace/agent_data_create.json", "w")
    
    def test_main_with_invalid_subcommand(self):
        """Test main function with invalid subcommand"""
        with pytest.raises(SystemExit):
            main(["invalid_command"])
    
    @patch('data_create.create_data')
    @patch('data_create.groundtruth_name', '')
    @patch('data_create.general_groundtruth_name', '')
    def test_create_agent_with_guardrail(self, mock_create_data):
        """Test that guardrail is properly formatted in request"""
        mock_create_data.return_value = {"agentid": 123}
        
        create_agent(
            agent_name="test",
            agent_instruction="test",
            model_name="gemini-2.0-flash-001",
            region_name="us-central1",
            guardrail_name="my-guardrail"
        )
        
        call_args = mock_create_data.call_args
        data_payload = call_args.kwargs['data']
        
        assert 'guardrail' in data_payload
        assert isinstance(data_payload['guardrail'], dict)
        assert data_payload['guardrail']['name'] == "my-guardrail"
    
    @patch('data_create.create_data')
    def test_create_agent_builds_correct_url(self, mock_create_data):
        """Test that create_agent uses correct API endpoint"""
        mock_create_data.return_value = {"agentid": 123}
        
        create_agent(
            agent_name="test",
            agent_instruction="test",
            model_name="gemini-2.0-flash-001",
            region_name="us-central1"
        )
        
        call_args = mock_create_data.call_args
        assert call_args.kwargs['path'] == "/agent/"
        assert call_args.kwargs['querystringparameters'] == {}
