"""
Pytest configuration and fixtures for GCP Agent tests
"""
import sys
import os
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# Add src directory to Python path for imports
# This allows tests to import modules from src/ directory
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture
def mock_config():
    """Mock configuration values to avoid loading actual config files"""
    config_values = {
        "PROJECT_ID": "test-project-123",
        "AGENT_DISPLAY_NAME": "test-agent",
        "AGENT_DESCRIPTION": "Test agent description",
        "MODEL_NAME": "gemini-2.0-flash-001",
        "SYSTEM_INSTRUCTION": "You are a helpful assistant",
        "LOCATION": "us-central1",
        "AGENT_PROMPT": "Test prompt",
        "GENERAL_EVALUATION": True,
        "RAGAS_EVALUATION": True,
        "ARIZE_SPACE_ID_NAME": "arize-space-id-secret",
        "ARIZE_API_KEY_NAME": "arize-api-key-secret",
        "GCP_SECRET_MANAGER_PROJECT": "123456789",
        "STAGING_BUCKET": "gs://test-staging-bucket",
        "DATA_APP_API_URL": "https://test-api.example.com",
        "CLOUDRUN_SERVICE_URL": "https://test-service.run.app",
        "REGION": "us-central1",
        "GUARDRAIL_NAME": "test-guardrail",
        "GUARDRAIL_BUCKET_NAME": "gs://test-guardrail-bucket",
        "GUARDRAIL_BUCKET_PREFIX": "guardrails/",
        "GROUNDTRUTH_NAME": "test-rag-groundtruth",
        "GENERAL_GROUNDTRUTH_NAME": "test-general-groundtruth",
        "NETWORK_ATTACHMENT": "projects/test/regions/us-central1/networkAttachments/test",
        "DNS_PEERING_DOMAIN": "test.internal",
        "DNS_PEERING_DOMAIN_TARGET_PROJECT": "network-project",
        "DNS_PEERING_DOMAIN_TARGET_NETWORK": "shared-vpc",
        "ARIZE_ENDPOINT": "https://otlp.arize.com/v1",
        "SERVICE_ACCOUNT_NAME": "test-sa@test-project.iam.gserviceaccount.com"
    }
    
    with patch.dict('sys.modules', {
        'config.config': MagicMock(**config_values)
    }):
        yield config_values


@pytest.fixture
def mock_secret_manager():
    """Mock Google Cloud Secret Manager client"""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.payload.data.decode.return_value = "test-secret-value"
    mock_client.access_secret_version.return_value = mock_response
    
    with patch('google.cloud.secretmanager.SecretManagerServiceClient', return_value=mock_client):
        yield mock_client


@pytest.fixture
def mock_vertexai():
    """Mock Vertex AI SDK"""
    with patch('vertexai.init') as mock_init, \
         patch('vertexai.Client') as mock_client:
        yield {
            'init': mock_init,
            'client': mock_client
        }


@pytest.fixture
def mock_agent():
    """Mock ADK Agent"""
    mock_agent_instance = MagicMock()
    mock_agent_instance.name = "test-agent"
    
    with patch('google.adk.agents.Agent', return_value=mock_agent_instance):
        yield mock_agent_instance


@pytest.fixture
def mock_agent_engines():
    """Mock Vertex AI Agent Engines"""
    mock_app = MagicMock()
    mock_remote_agent = MagicMock()
    mock_remote_agent.name = "projects/test-project/locations/us-central1/reasoningEngines/12345"
    mock_remote_agent.api_resource.name = "projects/test-project/locations/us-central1/reasoningEngines/12345"
    mock_remote_agent.display_name = "test-agent"
    
    with patch('vertexai.agent_engines.AdkApp', return_value=mock_app) as mock_adk_app, \
         patch('vertexai.Client') as mock_client_class:
        
        mock_client = MagicMock()
        mock_client.agent_engines.create.return_value = mock_remote_agent
        mock_client_class.return_value = mock_client
        
        yield {
            'adk_app': mock_adk_app,
            'client': mock_client,
            'remote_agent': mock_remote_agent
        }


@pytest.fixture
def mock_requests():
    """Mock requests library for API calls"""
    with patch('requests.post') as mock_post, \
         patch('requests.put') as mock_put:
        
        # Setup successful responses
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "agentid": 123,
            "rag_run_id": 456,
            "general_run_id": 789,
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
        mock_response.headers = {}
        
        mock_post.return_value = mock_response
        mock_put.return_value = mock_response
        
        yield {
            'post': mock_post,
            'put': mock_put,
            'response': mock_response
        }


@pytest.fixture
def mock_id_token():
    """Mock Google ID token generation"""
    with patch('google.oauth2.id_token.fetch_id_token', return_value="test-token-12345"):
        yield


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary configuration JSON file"""
    config_data = {
        "PROJECT_ID": "test-project",
        "AGENT_DISPLAY_NAME": "test-agent",
        "MODEL_NAME": "gemini-2.0-flash-001",
        "SYSTEM_INSTRUCTION": "Test instruction",
        "REGION": "us-central1"
    }
    
    config_file = tmp_path / "configuration.json"
    with open(config_file, 'w') as f:
        json.dump(config_data, f)
    
    return config_file


@pytest.fixture
def temp_rag_config_file(tmp_path):
    """Create a temporary RAG configuration JSON file"""
    rag_config = [
        {
            "rag_details": {
                "value": {
                    "datasetname": "test-knowledge-base",
                    "vectorizeddatasetbaseid": "projects/test/ragCorpora/12345"
                }
            }
        }
    ]
    
    rag_file = tmp_path / "rag_configuration.json"
    with open(rag_file, 'w') as f:
        json.dump(rag_config, f)
    
    return rag_file


@pytest.fixture
def temp_mcp_config_file(tmp_path):
    """Create a temporary MCP tools configuration JSON file"""
    mcp_config = {
        "mcpServers": {
            "test-server": {
                "command": "python",
                "args": ["-m", "mcp_server"],
                "env": {}
            }
        }
    }
    
    mcp_file = tmp_path / "tools_configuration.json"
    with open(mcp_file, 'w') as f:
        json.dump(mcp_config, f)
    
    return mcp_file


@pytest.fixture
def mock_workspace_files(tmp_path, monkeypatch):
    """Mock workspace files for Cloud Build pipeline"""
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    
    # Create agent_output.json
    agent_output = {
        "agent_base_id": "12345",
        "agent_alias_id": "projects/test/locations/us-central1/reasoningEngines/12345",
        "agent_url": "https://console.cloud.google.com/vertex-ai/agents/...",
        "agent_name": "test-agent"
    }
    with open(workspace_dir / "agent_output.json", 'w') as f:
        json.dump(agent_output, f)
    
    # Create agent_data_create.json
    agent_data = {
        "agent_id": 123,
        "rag_run_id": 456,
        "general_run_id": 789
    }
    with open(workspace_dir / "agent_data_create.json", 'w') as f:
        json.dump(agent_data, f)
    
    # Create groundtruth_output.json
    groundtruth_data = {
        "rag_groundtruth_gcs_path": "gs://test-bucket/rag-gt.csv",
        "general_groundtruth_gcs_path": "gs://test-bucket/general-gt.csv"
    }
    with open(workspace_dir / "groundtruth_output.json", 'w') as f:
        json.dump(groundtruth_data, f)
    
    # Mock /workspace/ path
    monkeypatch.setattr('builtins.open', lambda path, *args, **kwargs: 
        open(str(workspace_dir / Path(path).name) if '/workspace/' in str(path) else path, *args, **kwargs))
    
    return workspace_dir


@pytest.fixture
def mock_arize():
    """Mock Arize instrumentation"""
    with patch('arize.otel.register') as mock_register, \
         patch('openinference.instrumentation.google_adk.GoogleADKInstrumentor') as mock_instrumentor:
        
        mock_tracer = MagicMock()
        mock_register.return_value = mock_tracer
        
        yield {
            'register': mock_register,
            'instrumentor': mock_instrumentor,
            'tracer': mock_tracer
        }


@pytest.fixture
def mock_logger():
    """Mock logger to avoid log output during tests"""
    with patch('utils.log_helper.setup_logging') as mock_setup:
        mock_log = MagicMock()
        mock_setup.return_value = mock_log
        yield mock_log
