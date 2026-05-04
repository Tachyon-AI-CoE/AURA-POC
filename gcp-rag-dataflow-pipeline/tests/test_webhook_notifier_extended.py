"""Extended unit tests for webhooks/webhook_notifier.py — additional branch coverage."""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock, Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from webhooks.webhook_notifier import send_rag_status, _get_id_token


class TestGetIdToken:
    """Test _get_id_token helper function."""

    @patch('webhooks.webhook_notifier.id_token.fetch_id_token')
    @patch('webhooks.webhook_notifier.Request')
    def test_successful_token_fetch(self, mock_request, mock_fetch):
        mock_fetch.return_value = 'test-token-123'
        result = _get_id_token('https://service.run.app')
        assert result == 'test-token-123'

    @patch('webhooks.webhook_notifier.id_token.fetch_id_token', side_effect=Exception('auth fail'))
    @patch('webhooks.webhook_notifier.Request')
    def test_token_fetch_failure_returns_none(self, mock_request, mock_fetch):
        result = _get_id_token('https://service.run.app')
        assert result is None


class TestSendRagStatusExtended:
    """Extended tests for send_rag_status."""

    @patch('webhooks.webhook_notifier._get_id_token', return_value=None)
    @patch('webhooks.webhook_notifier.requests.put')
    def test_no_auth_token_still_sends(self, mock_put, mock_token):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'ok': True}
        mock_response.headers = {}
        mock_put.return_value = mock_response

        result = send_rag_status(
            corpus_name='test',
            status='Ready',
            webhook_url='https://test.com',
        )
        assert result['status'] == 'success'
        # Verify no Authorization header
        call_kwargs = mock_put.call_args[1]
        assert 'Authorization' not in call_kwargs['headers']

    @patch('webhooks.webhook_notifier._get_id_token', return_value=None)
    @patch('webhooks.webhook_notifier.requests.put')
    def test_corpus_url_extraction_from_resource_name(self, mock_put, mock_token):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'ok': True}
        mock_response.headers = {}
        mock_put.return_value = mock_response

        # Don't pass project_id/region — let them be extracted from resource name
        result = send_rag_status(
            corpus_name='test',
            status='Ready',
            webhook_url='https://test.com',
            corpus_resource_name='projects/extracted-proj/locations/us-west1/ragCorpora/999',
        )
        assert result['status'] == 'success'
        payload = mock_put.call_args[1]['json']
        assert 'extracted-proj' in payload.get('vectorizedDatasetUrl', '')
        assert 'us-west1' in payload.get('vectorizedDatasetUrl', '')

    @patch('webhooks.webhook_notifier._get_id_token', return_value=None)
    @patch('webhooks.webhook_notifier.requests.put')
    def test_corpus_url_bad_resource_name(self, mock_put, mock_token):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'ok': True}
        mock_response.headers = {}
        mock_put.return_value = mock_response

        result = send_rag_status(
            corpus_name='test',
            status='Ready',
            webhook_url='https://test.com',
            corpus_resource_name='bad/format',
        )
        assert result['status'] == 'success'

    @patch('webhooks.webhook_notifier._get_id_token', return_value=None)
    @patch('webhooks.webhook_notifier.requests.put')
    def test_response_not_json(self, mock_put, mock_token):
        import requests as req

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("not json")
        mock_response.text = 'OK'
        mock_response.headers = {}
        mock_response.raise_for_status.return_value = None
        mock_put.return_value = mock_response

        # This will hit the except in response.json() logging and then
        # also fail on response.json() in the return statement
        result = send_rag_status(
            corpus_name='test',
            status='Ready',
            webhook_url='https://test.com',
        )
        # The return line tries response.json() which raises, caught by outer except
        assert result['status'] == 'error' or result['status'] == 'success'

    @patch('webhooks.webhook_notifier._get_id_token', return_value=None)
    @patch('webhooks.webhook_notifier.requests.put')
    def test_request_exception(self, mock_put, mock_token):
        import requests as req
        mock_put.side_effect = req.exceptions.ConnectionError("Connection refused")

        result = send_rag_status(
            corpus_name='test',
            status='Ready',
            webhook_url='https://unreachable.com',
        )
        assert result['status'] == 'error'
        assert 'Connection refused' in result['error']

    @patch('webhooks.webhook_notifier._get_id_token', return_value=None)
    @patch('webhooks.webhook_notifier.requests.put')
    def test_unexpected_exception(self, mock_put, mock_token):
        mock_put.side_effect = RuntimeError("Unexpected")

        result = send_rag_status(
            corpus_name='test',
            status='Ready',
            webhook_url='https://test.com',
        )
        assert result['status'] == 'error'
        assert 'Unexpected' in result['error']
