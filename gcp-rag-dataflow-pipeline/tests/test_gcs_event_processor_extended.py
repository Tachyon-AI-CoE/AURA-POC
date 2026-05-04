"""Extended unit tests for event_processor/gcs_event_processor.py — additional branch coverage."""

import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock, Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from event_processor.gcs_event_processor import write_rag_audit, write_failure_audit, archive_config_file


class TestWriteRagAuditExtended:
    """Extended tests for write_rag_audit."""

    @patch('event_processor.gcs_event_processor.FileSystems')
    def test_completed_status_uses_success_prefix(self, mock_fs):
        mock_file = MagicMock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=False)
        mock_fs.create.return_value = mock_file

        config = {'corpus_name': 'test', 'audit_bucket': 'bucket'}
        write_rag_audit(config, 'corpus_creation_completed')

        call_path = mock_fs.create.call_args[0][0]
        assert 'success' in call_path

    @patch('event_processor.gcs_event_processor.FileSystems')
    def test_failed_status_uses_failure_prefix(self, mock_fs):
        mock_file = MagicMock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=False)
        mock_fs.create.return_value = mock_file

        config = {'corpus_name': 'test', 'audit_bucket': 'bucket'}
        write_rag_audit(config, 'vector_db_failed', 'error msg')

        call_path = mock_fs.create.call_args[0][0]
        assert 'failure' in call_path

    @patch('event_processor.gcs_event_processor.FileSystems')
    def test_message_field_included(self, mock_fs):
        mock_file = MagicMock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=False)
        mock_fs.create.return_value = mock_file

        config = {'corpus_name': 'test', 'audit_bucket': 'bucket', 'message': 'Import completed'}
        write_rag_audit(config, 'completed')

        written = json.loads(mock_file.write.call_args[0][0].decode('utf-8'))
        assert written['message'] == 'Import completed'

    @patch('event_processor.gcs_event_processor.FileSystems')
    def test_non_serializable_values_handled(self, mock_fs):
        mock_file = MagicMock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=False)
        mock_fs.create.return_value = mock_file

        obj_with_name = MagicMock()
        obj_with_name.name = 'corpus-resource-name'
        config = {
            'corpus_name': 'test',
            'audit_bucket': 'bucket',
            'rag_corpus_instance': MagicMock(),  # Should be skipped (_instance suffix)
            'some_object': obj_with_name,
        }
        write_rag_audit(config, 'completed')

        written = json.loads(mock_file.write.call_args[0][0].decode('utf-8'))
        # _instance fields are skipped
        assert 'rag_corpus_instance' not in written.get('pipeline_config', {})

    @patch('event_processor.gcs_event_processor.FileSystems')
    def test_gcs_write_failure_logged_not_raised(self, mock_fs):
        mock_fs.create.side_effect = Exception("GCS error")

        config = {'corpus_name': 'test', 'audit_bucket': 'bucket'}
        # Should not raise
        write_rag_audit(config, 'completed')


class TestWriteFailureAuditExtended:
    """Extended tests for write_failure_audit."""

    @patch('webhooks.webhook_notifier.send_rag_status')
    @patch('event_processor.gcs_event_processor.write_rag_audit')
    def test_webhook_with_corpus_instance(self, mock_audit, mock_webhook):
        mock_webhook.return_value = {'status': 'success'}
        corpus = MagicMock()
        corpus.name = 'projects/p/locations/r/ragCorpora/123'

        config = {
            'corpus_name': 'test',
            'status_webhook_url': 'https://test.com',
            'audit_bucket': 'bucket',
            'rag_corpus_instance': corpus,
            'project_id': 'p',
            'region': 'r',
        }
        write_failure_audit(config, 'test_failure', Exception('err'))

        call_kwargs = mock_webhook.call_args[1]
        assert call_kwargs['corpus_resource_name'] == 'projects/p/locations/r/ragCorpora/123'

    @patch('webhooks.webhook_notifier.send_rag_status')
    @patch('event_processor.gcs_event_processor.write_rag_audit')
    def test_webhook_failure_logged_not_raised(self, mock_audit, mock_webhook):
        mock_webhook.side_effect = Exception('webhook crash')

        config = {
            'corpus_name': 'test',
            'status_webhook_url': 'https://test.com',
            'audit_bucket': 'bucket',
        }
        # Should not raise
        write_failure_audit(config, 'test_failure', Exception('err'))

    @patch('webhooks.webhook_notifier.send_rag_status')
    @patch('event_processor.gcs_event_processor.write_rag_audit')
    def test_webhook_returns_error_status(self, mock_audit, mock_webhook):
        mock_webhook.return_value = {'status': 'error', 'error': 'timeout'}

        config = {
            'corpus_name': 'test',
            'status_webhook_url': 'https://test.com',
            'audit_bucket': 'bucket',
        }
        write_failure_audit(config, 'test_failure', Exception('err'))

    @patch('event_processor.gcs_event_processor.write_rag_audit', side_effect=Exception('audit crash'))
    def test_audit_write_failure_still_tries_webhook(self, mock_audit):
        with patch('webhooks.webhook_notifier.send_rag_status') as mock_webhook:
            mock_webhook.return_value = {'status': 'success'}
            config = {
                'corpus_name': 'test',
                'status_webhook_url': 'https://test.com',
            }
            write_failure_audit(config, 'test_failure', Exception('err'))
            mock_webhook.assert_called_once()


class TestArchiveConfigFileExtended:
    """Extended tests for archive_config_file."""

    def test_non_gcs_path_skipped(self):
        config = {'_config_file': '/local/path/file.json'}
        result = archive_config_file(config)
        assert result['status'] == 'skipped'

    def test_none_config_file_skipped(self):
        config = {'_config_file': None}
        result = archive_config_file(config)
        assert result['status'] == 'skipped'
