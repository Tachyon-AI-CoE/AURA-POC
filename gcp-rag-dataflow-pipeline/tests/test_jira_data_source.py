"""Unit tests for data_sources/jira_data_source.py."""

import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from data_sources.jira_data_source import validate_config


class TestJiraValidateConfig:
    """Test JIRA validate_config function."""

    def test_valid_config_with_projects(self):
        config = {
            'jira_server_uri': 'https://jira.example.com',
            'jira_email': 'user@example.com',
            'jira_api_secret_key': 'secret-key',
            'jira_projects': ['PROJ1', 'PROJ2'],
        }
        assert validate_config(config) is True

    def test_valid_config_with_custom_query(self):
        config = {
            'jira_server_uri': 'https://jira.example.com',
            'jira_email': 'user@example.com',
            'jira_api_secret_key': 'secret-key',
            'jira_custom_query': ['project = PROJ1'],
        }
        assert validate_config(config) is True

    def test_missing_server_uri(self):
        config = {
            'jira_email': 'user@example.com',
            'jira_api_secret_key': 'secret-key',
            'jira_projects': ['PROJ1'],
        }
        assert validate_config(config) is False

    def test_missing_email(self):
        config = {
            'jira_server_uri': 'https://jira.example.com',
            'jira_api_secret_key': 'secret-key',
            'jira_projects': ['PROJ1'],
        }
        assert validate_config(config) is False

    def test_missing_api_secret_key(self):
        config = {
            'jira_server_uri': 'https://jira.example.com',
            'jira_email': 'user@example.com',
            'jira_projects': ['PROJ1'],
        }
        assert validate_config(config) is False

    def test_missing_projects_and_custom_query(self):
        config = {
            'jira_server_uri': 'https://jira.example.com',
            'jira_email': 'user@example.com',
            'jira_api_secret_key': 'secret-key',
        }
        assert validate_config(config) is False

    def test_empty_config(self):
        assert validate_config({}) is False

    def test_empty_string_values(self):
        config = {
            'jira_server_uri': '',
            'jira_email': '',
            'jira_api_secret_key': '',
            'jira_projects': [],
        }
        assert validate_config(config) is False

    def test_none_values(self):
        config = {
            'jira_server_uri': None,
            'jira_email': None,
            'jira_api_secret_key': None,
        }
        assert validate_config(config) is False


class TestGetJiraRagSource:
    """Test get_jira_rag_source function."""

    @patch('data_sources.jira_data_source.rag')
    def test_valid_jira_source_creation(self, mock_rag):
        from data_sources.jira_data_source import get_jira_rag_source

        mock_jira_query = MagicMock()
        mock_rag.JiraQuery.return_value = mock_jira_query
        mock_jira_source = MagicMock()
        mock_rag.JiraSource.return_value = mock_jira_source

        config = {
            'jira_server_uri': 'https://jira.example.com',
            'jira_email': 'user@example.com',
            'jira_api_secret_key': 'secret-key',
            'jira_projects': ['PROJ1'],
            'jira_custom_query': [],
        }

        result = get_jira_rag_source(config)
        assert result == mock_jira_source
        mock_rag.JiraQuery.assert_called_once()
        mock_rag.JiraSource.assert_called_once()

    @patch('data_sources.jira_data_source.rag')
    def test_invalid_config_raises_error(self, mock_rag):
        from data_sources.jira_data_source import get_jira_rag_source
        import pytest

        config = {}
        with pytest.raises(ValueError, match="Invalid JIRA configuration"):
            get_jira_rag_source(config)

    @patch('data_sources.jira_data_source.rag')
    def test_jira_query_receives_correct_params(self, mock_rag):
        from data_sources.jira_data_source import get_jira_rag_source

        mock_rag.JiraQuery.return_value = MagicMock()
        mock_rag.JiraSource.return_value = MagicMock()

        config = {
            'jira_server_uri': 'https://jira.example.com',
            'jira_email': 'user@example.com',
            'jira_api_secret_key': 'secret-key',
            'jira_projects': ['PROJ1', 'PROJ2'],
            'jira_custom_query': ['query1'],
        }

        get_jira_rag_source(config)

        mock_rag.JiraQuery.assert_called_once_with(
            email='user@example.com',
            jira_projects=['PROJ1', 'PROJ2'],
            custom_queries=['query1'],
            api_key='secret-key',
            server_uri='https://jira.example.com',
        )
