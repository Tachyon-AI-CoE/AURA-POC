"""
Unit tests for webhook notifier module.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from webhooks.webhook_notifier import send_rag_status


class TestWebhookNotifier(unittest.TestCase):
    """Test webhook notification functionality."""
    
    def test_no_webhook_url_returns_none(self):
        """Test that missing webhook URL returns None."""
        result = send_rag_status(
            corpus_name='test-corpus',
            status='Ready',
            webhook_url=None
        )
        
        self.assertIsNone(result)
    
    @patch('webhooks.webhook_notifier.requests.put')
    def test_successful_webhook_call(self, mock_put):
        """Test successful webhook call."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'message': 'success'}
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_put.return_value = mock_response
        
        result = send_rag_status(
            corpus_name='test-corpus',
            status='Ready',
            webhook_url='https://test.webhook.com',
            corpus_resource_name='projects/test/locations/us-east4/ragCorpora/123',
            project_id='test-project',
            region='us-east4'
        )
        
        self.assertEqual(result['status'], 'success')
        
        # Verify PUT request was called correctly
        mock_put.assert_called_once()
        call_args = mock_put.call_args
        
        # Check URL
        self.assertEqual(call_args[0][0], 'https://test.webhook.com')
        
        # Check query params
        self.assertEqual(call_args[1]['params']['dataset_name'], 'test-corpus')
        
        # Check payload
        payload = call_args[1]['json']
        self.assertEqual(payload['status'], 'Ready')
        self.assertIn('vectorizedDatasetBaseId', payload)
        self.assertIn('vectorizedDatasetUrl', payload)
    
    @patch('webhooks.webhook_notifier.requests.put')
    def test_failed_status_webhook(self, mock_put):
        """Test webhook call with failed status."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'message': 'received'}
        mock_response.headers = {}
        mock_put.return_value = mock_response
        
        result = send_rag_status(
            corpus_name='test-corpus',
            status='Failed',
            error_message='Configuration validation failed',
            webhook_url='https://test.webhook.com',
            project_id='test-project',
            region='us-east4'
        )
        
        self.assertEqual(result['status'], 'success')
        
        # Verify error message in payload
        payload = mock_put.call_args[1]['json']
        self.assertEqual(payload['status'], 'Failed')
        self.assertIn('error_message', payload)
        self.assertEqual(payload['error_message'], 'Configuration validation failed')
    
    @patch('webhooks.webhook_notifier.requests.put')
    def test_http_error_handling(self, mock_put):
        """Test handling of HTTP errors."""
        import requests
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_response.json.return_value = {}
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError('HTTP 500')
        mock_put.return_value = mock_response
        
        result = send_rag_status(
            corpus_name='test-corpus',
            status='Ready',
            webhook_url='https://test.webhook.com'
        )
        
        self.assertEqual(result['status'], 'error')
        # Check that the error contains the status code or text
        self.assertTrue('500' in result['error'] or 'Internal Server Error' in result['error'])
    
    @patch('webhooks.webhook_notifier.requests.put')
    def test_console_url_construction(self, mock_put):
        """Test Vertex AI console URL construction."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'message': 'success'}
        mock_response.headers = {}
        mock_put.return_value = mock_response
        
        send_rag_status(
            corpus_name='test-corpus',
            status='Ready',
            webhook_url='https://test.webhook.com',
            corpus_resource_name='projects/my-project/locations/us-central1/ragCorpora/456',
            project_id='my-project',
            region='us-central1'
        )
        
        # Verify console URL was constructed correctly
        payload = mock_put.call_args[1]['json']
        expected_url = (
            'https://console.cloud.google.com/vertex-ai/rag/locations/us-central1/'
            'corpus/456/data?authuser=1&hl=en&project=my-project'
        )
        self.assertEqual(payload['vectorizedDatasetUrl'], expected_url)


if __name__ == '__main__':
    unittest.main()
