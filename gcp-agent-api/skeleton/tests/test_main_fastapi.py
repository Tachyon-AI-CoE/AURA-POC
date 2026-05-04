"""
Unit tests for main_fastapi.py
Tests FastAPI application initialization and endpoints
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

# Mock environment variables BEFORE imports
os.environ.setdefault('PROJECT_ID', 'test-project')
os.environ.setdefault('LOCATION', 'us-central1')
os.environ.setdefault('PROJECT_NUMBER', '123456789')
os.environ.setdefault('ARIZE_API_KEY', 'test-key')
os.environ.setdefault('ARIZE_SPACE_ID', 'test-space')
os.environ.setdefault('ARIZE_API_KEY_VALUE', 'test-key-value')
os.environ.setdefault('ARIZE_SPACE_ID_VALUE', 'test-space-value')

# Mock external dependencies
sys.modules['vertexai'] = MagicMock()
sys.modules['vertexai.agent_engines'] = MagicMock()
sys.modules['arize'] = MagicMock()
sys.modules['arize.otel'] = MagicMock()
sys.modules['opentelemetry'] = MagicMock()
sys.modules['opentelemetry.trace'] = MagicMock()
sys.modules['openinference'] = MagicMock()
sys.modules['openinference.instrumentation'] = MagicMock()
sys.modules['openinference.instrumentation.vertexai'] = MagicMock()
sys.modules['google.cloud.secretmanager'] = MagicMock()

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from main_fastapi import app  # type: ignore


class TestMainFastAPI:
    """Test suite for FastAPI application"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_app_initialization(self):
        """Test that FastAPI app initializes correctly"""
        assert app is not None
        assert app.title == "GCP Agent API"
        assert app.version == "1.0.0"
        assert app.docs_url == '/docs'
    
    def test_health_check_endpoint(self, client):
        """Test /health endpoint returns healthy status"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "GCP Agent API"
        assert "message" in data
    
    def test_root_endpoint(self, client):
        """Test root / endpoint returns API information"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "GCP Agent API"
        assert data["version"] == "1.0.0"
        assert "endpoints" in data
        assert "/invoke-agent" in str(data["endpoints"])
    
    def test_cors_middleware_enabled(self):
        """Test that CORS middleware is properly configured"""
        # Check middleware is in the app
        middleware_found = False
        for middleware in app.user_middleware:
            if 'CORSMiddleware' in str(middleware):
                middleware_found = True
                break
        assert middleware_found, "CORS middleware should be enabled"
    
    def test_openapi_docs_available(self, client):
        """Test that OpenAPI documentation is accessible"""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "GCP Agent API"
    
    def test_docs_ui_accessible(self, client):
        """Test that Swagger UI docs are accessible"""
        response = client.get("/docs")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_redoc_ui_accessible(self, client):
        """Test that ReDoc UI is accessible"""
        response = client.get("/redoc")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_router_included(self):
        """Test that agent router is included in the app"""
        # Check that agent router endpoints are registered
        routes = [route.path for route in app.routes]
        assert "/invoke-agent" in routes
        assert "/health" in routes
        assert "/" in routes
    
    def test_app_title_and_description(self):
        """Test app metadata"""
        assert app.title == "GCP Agent API"
        assert "Cloud Run" in app.description
        assert "FastAPI" in app.description
    
    def test_invalid_endpoint_returns_404(self, client):
        """Test that invalid endpoints return 404"""
        response = client.get("/nonexistent-endpoint")
        
        assert response.status_code == 404
    
    def test_health_check_returns_json(self, client):
        """Test health check returns valid JSON"""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data
        assert "service" in data
    
    def test_root_endpoint_structure(self, client):
        """Test root endpoint returns complete information"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check all required fields
        assert "service" in data
        assert "version" in data
        assert "description" in data
        assert "endpoints" in data
        
        # Check endpoints dict structure
        endpoints = data["endpoints"]
        assert isinstance(endpoints, dict)
        assert "invoke-agent" in endpoints
        assert "health" in endpoints
        assert "docs" in endpoints
