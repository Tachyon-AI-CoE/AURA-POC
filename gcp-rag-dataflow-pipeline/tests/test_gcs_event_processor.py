"""
Unit tests for GCS event processor.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
import json
from datetime import datetime

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from event_processor.gcs_event_processor import (
    write_rag_audit,
    write_failure_audit,
    archive_config_file
)


class TestWriteRagAudit(unittest.TestCase):
    """Test write_rag_audit function."""
    
    @patch('event_processor.gcs_event_processor.FileSystems')
    @patch('event_processor.gcs_event_processor.datetime')
    def test_successful_audit_write(self, mock_datetime, mock_fs):
        """Test successful audit record writing."""
        mock_datetime.now.return_value.strftime.return_value = '20231201-120000'
        
        mock_file = Mock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=False)
        mock_fs.create.return_value = mock_file
        
        pipeline_config = {
            'corpus_name': 'test-corpus',
            'audit_bucket': 'test-audit-bucket',
            'project_id': 'test-project',
            'region': 'us-east4'
        }
        
        write_rag_audit(pipeline_config, 'corpus_creation_completed')
        
        # Verify file was created with correct path
        mock_fs.create.assert_called_once()
        call_args = mock_fs.create.call_args[0][0]
        self.assertIn('test-audit-bucket', call_args)
        self.assertIn('test-corpus', call_args)
        self.assertIn('success', call_args)
        
        # Verify JSON content was written
        mock_file.write.assert_called_once()
        written_data = json.loads(mock_file.write.call_args[0][0].decode('utf-8'))
        self.assertEqual(written_data['corpus_name'], 'test-corpus')
        self.assertEqual(written_data['status'], 'corpus_creation_completed')
    
    @patch('event_processor.gcs_event_processor.FileSystems')
    def test_audit_write_with_error(self, mock_fs):
        """Test audit write with error message."""
        mock_file = Mock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=False)
        mock_fs.create.return_value = mock_file
        
        pipeline_config = {
            'corpus_name': 'test-corpus',
            'audit_bucket': 'test-audit-bucket'
        }
        
        write_rag_audit(pipeline_config, 'corpus_creation_failed', 'Test error message')
        
        # Verify error was included in audit
        written_data = json.loads(mock_file.write.call_args[0][0].decode('utf-8'))
        self.assertIn('error', written_data)
        self.assertEqual(written_data['error'], 'Test error message')
    
    def test_missing_audit_bucket(self):
        """Test that missing audit_bucket is handled gracefully."""
        pipeline_config = {
            'corpus_name': 'test-corpus'
        }
        
        # Should not raise exception
        write_rag_audit(pipeline_config, 'test_status')


class TestWriteFailureAudit(unittest.TestCase):
    """Test write_failure_audit function."""
    
    @patch('webhooks.webhook_notifier.send_rag_status')
    @patch('event_processor.gcs_event_processor.write_rag_audit')
    def test_failure_audit_with_webhook(self, mock_audit, mock_webhook):
        """Test failure audit with webhook notification."""
        mock_webhook.return_value = {'status': 'success'}
        
        config = {
            'corpus_name': 'test-corpus',
            'status_webhook_url': 'https://test.webhook.com',
            'audit_bucket': 'test-audit',
            'project_id': 'test-project',
            'region': 'us-east4'
        }
        
        error = Exception('Test error')
        
        write_failure_audit(config, 'test_failure', error)
        
        # Verify audit was written
        mock_audit.assert_called_once_with(config, 'test_failure', 'Test error')
        
        # Verify webhook was called
        mock_webhook.assert_called_once()
        call_args = mock_webhook.call_args[1]
        self.assertEqual(call_args['corpus_name'], 'test-corpus')
        self.assertEqual(call_args['status'], 'Failed')
        self.assertIn('test_failure', call_args['error_message'])
    
    @patch('webhooks.webhook_notifier.send_rag_status')
    @patch('event_processor.gcs_event_processor.write_rag_audit')
    def test_failure_audit_without_webhook(self, mock_audit, mock_webhook):
        """Test failure audit without webhook URL."""
        config = {
            'corpus_name': 'test-corpus',
            'audit_bucket': 'test-audit'
        }
        
        error = Exception('Test error')
        
        write_failure_audit(config, 'test_failure', error)
        
        # Verify audit was written
        mock_audit.assert_called_once()
        
        # Verify webhook was NOT called
        mock_webhook.assert_not_called()


class TestArchiveConfigFile(unittest.TestCase):
    """Test archive_config_file function."""
    
    @patch('apache_beam.io.filesystems.FileSystems')
    def test_successful_archive(self, mock_fs):
        """Test successful config file archival."""
        # Mock successful deletion
        mock_fs.delete.return_value = None
        
        pipeline_config = {
            '_config_file': 'gs://test-bucket/config.json'
        }
        
        result = archive_config_file(pipeline_config)
        
        self.assertEqual(result['status'], 'archived')
        self.assertEqual(result['config_file'], 'gs://test-bucket/config.json')
        mock_fs.delete.assert_called_once_with(['gs://test-bucket/config.json'])
    
    def test_missing_config_file(self):
        """Test archive with missing config file path."""
        pipeline_config = {}
        
        result = archive_config_file(pipeline_config)
        
        self.assertEqual(result['status'], 'skipped')
    
    @patch('apache_beam.io.filesystems.FileSystems')
    def test_archive_failure(self, mock_fs):
        """Test archive failure handling."""
        mock_fs.delete.side_effect = Exception('Delete failed')
        
        pipeline_config = {
            '_config_file': 'gs://test-bucket/config.json'
        }
        
        result = archive_config_file(pipeline_config)
        
        self.assertEqual(result['status'], 'failed')
        self.assertIn('error', result)


if __name__ == '__main__':
    unittest.main()
