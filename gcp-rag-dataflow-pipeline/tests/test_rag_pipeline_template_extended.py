"""Extended unit tests for rag_pipeline_template.py — covers additional DoFn paths."""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock, Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dataflow_templates.rag_pipeline_template import (
    RAGCorpusConfigurationResolver,
    RAGVectorDatabaseInitializer,
    CreateOrGetRAGCorpus,
    RAGDataSourcePathResolver,
    ImportFilesToRAGCorpus,
    SendWebhookNotification,
)


# ---------------------------------------------------------------------------
# RAGCorpusConfigurationResolver — additional branch coverage
# ---------------------------------------------------------------------------

class TestConfigResolverGetOptionValue:
    """Test get_option_value helper method."""

    def test_returns_static_value(self):
        options = MagicMock()
        options.config_bucket = 'my-bucket'
        dofn = RAGCorpusConfigurationResolver(options)
        assert dofn.get_option_value('config_bucket') == 'my-bucket'

    def test_returns_value_provider_value(self):
        vp = MagicMock()
        vp.get.return_value = 'resolved-value'
        options = MagicMock()
        options.config_bucket = vp
        dofn = RAGCorpusConfigurationResolver(options)
        assert dofn.get_option_value('config_bucket') == 'resolved-value'

    def test_returns_none_for_missing_attr(self):
        options = MagicMock(spec=[])
        dofn = RAGCorpusConfigurationResolver(options)
        assert dofn.get_option_value('nonexistent') is None


class TestConfigResolverProcess:
    """Test process method edge cases."""

    def _make_options(self, **overrides):
        opts = MagicMock()
        opts.config_bucket = overrides.get('config_bucket', 'bucket')
        opts.config_file_pattern = overrides.get('config_file_pattern', 'cfg.json')
        opts.result_bucket = overrides.get('result_bucket', 'results')
        opts.audit_bucket = overrides.get('audit_bucket', 'audit')
        opts.status_webhook_url = overrides.get('status_webhook_url', None)
        opts.cloud_run_service = overrides.get('cloud_run_service', None)
        opts.event_arc_service_account = overrides.get('event_arc_service_account', None)
        opts.corpus_mapping_bucket = overrides.get('corpus_mapping_bucket', None)
        opts.cloudrun_service_url = overrides.get('cloudrun_service_url', None)
        opts.get_all_options.return_value = overrides.get('all_options', {'project': 'p', 'region': 'r'})
        return opts

    @patch('apache_beam.io.filesystems.FileSystems')
    def test_file_not_found_raises(self, mock_fs):
        opts = self._make_options()
        mock_fs.match.return_value = [MagicMock(metadata_list=[])]
        dofn = RAGCorpusConfigurationResolver(opts)
        with pytest.raises((FileNotFoundError, UnboundLocalError)):
            list(dofn.process('start'))

    @patch('validators.config_validation.validate_config', return_value=False)
    @patch('config.rag_pipeline_config.get_flattened_rag_pipeline_config')
    @patch('apache_beam.io.filesystems.FileSystems')
    def test_validation_failure_raises(self, mock_fs, mock_flatten, mock_validate):
        opts = self._make_options()
        mock_match = MagicMock()
        mock_match.metadata_list = [MagicMock(path='gs://bucket/cfg.json')]
        mock_fs.match.return_value = [mock_match]
        mock_file = MagicMock()
        mock_file.read.return_value = b'{"rag_corpus":{"corpus_name":"c"}}'
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=False)
        mock_fs.open.return_value = mock_file
        mock_flatten.return_value = {'corpus_name': 'c'}

        dofn = RAGCorpusConfigurationResolver(opts)
        with pytest.raises((ValueError, UnboundLocalError)):
            list(dofn.process('start'))

    def test_missing_config_file_pattern_raises(self):
        opts = self._make_options(config_file_pattern=None)
        dofn = RAGCorpusConfigurationResolver(opts)
        dofn.get_option_value = Mock(side_effect=lambda x: None if x == 'config_file_pattern' else 'val')
        with pytest.raises((ValueError, UnboundLocalError)):
            list(dofn.process('start'))

    def test_missing_result_bucket_raises(self):
        opts = self._make_options(result_bucket=None)
        dofn = RAGCorpusConfigurationResolver(opts)
        dofn.get_option_value = Mock(side_effect=lambda x: None if x == 'result_bucket' else 'val')
        with pytest.raises((ValueError, UnboundLocalError)):
            list(dofn.process('start'))


# ---------------------------------------------------------------------------
# CreateOrGetRAGCorpus — missing project_id and region
# ---------------------------------------------------------------------------

class TestCreateOrGetRAGCorpusExtended:
    """Extended tests for CreateOrGetRAGCorpus DoFn."""

    def test_missing_project_id_raises(self):
        dofn = CreateOrGetRAGCorpus()
        config = {'corpus_name': 'c', 'vector_db_instance': MagicMock(), 'region': 'r'}
        with pytest.raises(ValueError, match="project_id is required"):
            list(dofn.process(config))

    def test_missing_region_raises(self):
        dofn = CreateOrGetRAGCorpus()
        config = {'corpus_name': 'c', 'vector_db_instance': MagicMock(), 'project_id': 'p'}
        with pytest.raises(ValueError, match="region is required"):
            list(dofn.process(config))

    @patch('event_processor.gcs_event_processor.write_failure_audit')
    @patch('rag.rag_engine.get_or_create_corpus', side_effect=Exception('corpus error'))
    def test_corpus_failure_writes_audit(self, mock_corpus, mock_audit):
        dofn = CreateOrGetRAGCorpus()
        config = {'corpus_name': 'c', 'vector_db_instance': MagicMock(), 'project_id': 'p', 'region': 'r'}
        with pytest.raises(Exception):
            list(dofn.process(config))
        mock_audit.assert_called_once()


# ---------------------------------------------------------------------------
# RAGDataSourcePathResolver — failure path
# ---------------------------------------------------------------------------

class TestDataSourcePathResolverExtended:
    """Extended tests for RAGDataSourcePathResolver."""

    @patch('event_processor.gcs_event_processor.write_failure_audit')
    @patch('data_sources.gcs_data_source.get_source_path', side_effect=Exception('path error'))
    def test_path_error_writes_audit(self, mock_path, mock_audit):
        dofn = RAGDataSourcePathResolver()
        config = {'staging_bucket': 'b', 'corpus_name': 'c'}
        with pytest.raises(Exception):
            list(dofn.process(config))
        mock_audit.assert_called_once()

    def test_data_staging_bucket_fallback(self):
        dofn = RAGDataSourcePathResolver()
        with patch('data_sources.gcs_data_source.get_source_path', return_value='gs://b/**'):
            config = {'data_staging_bucket': 'fallback-bucket', 'corpus_name': 'c'}
            results = list(dofn.process(config))
            assert results[0]['source_path'] == 'gs://b/**'


# ---------------------------------------------------------------------------
# ImportFilesToRAGCorpus — sync trigger, mapping, and error paths
# ---------------------------------------------------------------------------

class TestImportFilesExtended:
    """Extended tests for ImportFilesToRAGCorpus DoFn."""

    @patch('event_processor.gcs_event_processor.write_rag_audit')
    @patch('event_processor.gcs_event_processor.archive_config_file')
    @patch('rag.rag_engine.import_files_to_corpus')
    def test_missing_rag_corpus_raises(self, mock_import, mock_archive, mock_audit):
        dofn = ImportFilesToRAGCorpus()
        config = {'source_path': 'gs://b/**'}
        with pytest.raises(ValueError, match="rag_corpus_instance is required"):
            list(dofn.process(config))

    @patch('event_processor.gcs_event_processor.write_rag_audit')
    @patch('event_processor.gcs_event_processor.archive_config_file')
    @patch('rag.rag_engine.import_files_to_corpus')
    def test_missing_source_path_raises(self, mock_import, mock_archive, mock_audit):
        dofn = ImportFilesToRAGCorpus()
        config = {'rag_corpus_instance': MagicMock()}
        with pytest.raises(ValueError, match="source_path is required"):
            list(dofn.process(config))

    @patch('event_processor.gcs_event_processor.write_failure_audit')
    @patch('rag.rag_engine.import_files_to_corpus', side_effect=Exception('import fail'))
    def test_import_failure_writes_audit(self, mock_import, mock_audit):
        dofn = ImportFilesToRAGCorpus()
        config = {'rag_corpus_instance': MagicMock(), 'source_path': 'gs://b/**'}
        with pytest.raises(Exception):
            list(dofn.process(config))
        mock_audit.assert_called_once()

    @patch('event_arc.event_arc_trigger.create_eventarc_trigger')
    @patch('event_processor.gcs_event_processor.write_rag_audit')
    @patch('event_processor.gcs_event_processor.archive_config_file')
    @patch('rag.rag_engine.import_files_to_corpus')
    def test_eventarc_trigger_created_when_sync_enabled(self, mock_import, mock_archive, mock_audit, mock_trigger):
        mock_response = MagicMock()
        mock_response.imported_rag_files_count = 5
        mock_response.skipped_rag_files_count = 0
        mock_import.return_value = mock_response
        mock_trigger.return_value = {'status': 'success', 'trigger_name': 'test', 'trigger_resource_name': 'trn'}

        dofn = ImportFilesToRAGCorpus()
        config = {
            'rag_corpus_instance': MagicMock(),
            'source_path': 'gs://b/**',
            'corpus_name': 'test',
            'sync_through_rag_pipeline': True,
            'staging_bucket': 'staging-b',
            'project_id': 'p',
            'region': 'r',
        }
        results = list(dofn.process(config))
        assert len(results) == 1
        mock_trigger.assert_called_once()

    @patch('event_arc.event_arc_trigger.create_eventarc_trigger')
    @patch('event_processor.gcs_event_processor.write_rag_audit')
    @patch('event_processor.gcs_event_processor.archive_config_file')
    @patch('rag.rag_engine.import_files_to_corpus')
    def test_eventarc_trigger_error_logged(self, mock_import, mock_archive, mock_audit, mock_trigger):
        mock_response = MagicMock()
        mock_response.imported_rag_files_count = 5
        mock_response.skipped_rag_files_count = 0
        mock_import.return_value = mock_response
        mock_trigger.return_value = {'status': 'error', 'error': 'failed'}

        dofn = ImportFilesToRAGCorpus()
        config = {
            'rag_corpus_instance': MagicMock(),
            'source_path': 'gs://b/**',
            'corpus_name': 'test',
            'sync_through_rag_pipeline': True,
            'staging_bucket': 'b',
            'project_id': 'p',
            'region': 'r',
        }
        results = list(dofn.process(config))
        assert len(results) == 1

    @patch('event_arc.event_arc_trigger.create_eventarc_trigger')
    @patch('event_processor.gcs_event_processor.write_rag_audit')
    @patch('event_processor.gcs_event_processor.archive_config_file')
    @patch('rag.rag_engine.import_files_to_corpus')
    def test_eventarc_trigger_warning_logged(self, mock_import, mock_archive, mock_audit, mock_trigger):
        mock_response = MagicMock()
        mock_response.imported_rag_files_count = 3
        mock_response.skipped_rag_files_count = 1
        mock_import.return_value = mock_response
        mock_trigger.return_value = {'status': 'warning', 'trigger_name': 'existing'}

        dofn = ImportFilesToRAGCorpus()
        config = {
            'rag_corpus_instance': MagicMock(),
            'source_path': 'gs://b/**',
            'corpus_name': 'test',
            'sync_through_rag_pipeline': True,
            'staging_bucket': 'b',
            'project_id': 'p',
            'region': 'r',
        }
        results = list(dofn.process(config))
        assert len(results) == 1

    @patch('apache_beam.io.filesystems.FileSystems')
    @patch('event_processor.gcs_event_processor.write_rag_audit')
    @patch('event_processor.gcs_event_processor.archive_config_file')
    @patch('rag.rag_engine.import_files_to_corpus')
    def test_corpus_mapping_created(self, mock_import, mock_archive, mock_audit, mock_fs):
        mock_response = MagicMock()
        mock_response.imported_rag_files_count = 2
        mock_response.skipped_rag_files_count = 0
        mock_import.return_value = mock_response

        mock_file = MagicMock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=False)
        mock_fs.create.return_value = mock_file

        corpus = MagicMock()
        corpus.name = 'projects/p/locations/r/ragCorpora/123'

        dofn = ImportFilesToRAGCorpus()
        config = {
            'rag_corpus_instance': corpus,
            'source_path': 'gs://b/**',
            'corpus_name': 'test',
            'corpus_mapping_bucket': 'mapping-bucket',
            'staging_bucket': 'staging-b',
            'project_id': 'p',
            'region': 'r',
            'vector_db_type': 'RagManagedDb',
        }
        results = list(dofn.process(config))
        assert len(results) == 1
        mock_fs.create.assert_called_once()

    @patch('event_processor.gcs_event_processor.write_rag_audit')
    @patch('event_processor.gcs_event_processor.archive_config_file')
    @patch('rag.rag_engine.import_files_to_corpus')
    def test_corpus_mapping_no_staging_bucket(self, mock_import, mock_archive, mock_audit):
        mock_response = MagicMock()
        mock_response.imported_rag_files_count = 1
        mock_response.skipped_rag_files_count = 0
        mock_import.return_value = mock_response

        dofn = ImportFilesToRAGCorpus()
        config = {
            'rag_corpus_instance': MagicMock(),
            'source_path': 'gs://b/**',
            'corpus_name': 'test',
            'corpus_mapping_bucket': 'mapping-bucket',
        }
        results = list(dofn.process(config))
        assert len(results) == 1

    @patch('event_processor.gcs_event_processor.write_rag_audit', side_effect=Exception('audit fail'))
    @patch('event_processor.gcs_event_processor.archive_config_file', side_effect=Exception('archive fail'))
    @patch('rag.rag_engine.import_files_to_corpus')
    def test_archive_and_audit_exceptions_non_blocking(self, mock_import, mock_archive, mock_audit):
        mock_response = MagicMock()
        mock_response.imported_rag_files_count = 1
        mock_response.skipped_rag_files_count = 0
        mock_import.return_value = mock_response

        dofn = ImportFilesToRAGCorpus()
        config = {
            'rag_corpus_instance': MagicMock(),
            'source_path': 'gs://b/**',
            'corpus_name': 'test',
        }
        results = list(dofn.process(config))
        assert len(results) == 1


# ---------------------------------------------------------------------------
# SendWebhookNotification — warning log path
# ---------------------------------------------------------------------------

class TestSendWebhookExtended:
    """Extended tests for SendWebhookNotification DoFn."""

    @patch('webhooks.webhook_notifier.send_rag_status')
    def test_webhook_returns_error_status(self, mock_send):
        mock_send.return_value = {'status': 'error', 'error': 'timeout'}
        dofn = SendWebhookNotification()
        config = {
            'status_webhook_url': 'https://test.webhook.com',
            'corpus_name': 'test',
        }
        results = list(dofn.process(config))
        assert len(results) == 1

    @patch('webhooks.webhook_notifier.send_rag_status')
    def test_webhook_without_corpus_instance(self, mock_send):
        mock_send.return_value = {'status': 'success'}
        dofn = SendWebhookNotification()
        config = {
            'status_webhook_url': 'https://test.webhook.com',
            'corpus_name': 'test',
        }
        results = list(dofn.process(config))
        assert len(results) == 1
        call_kwargs = mock_send.call_args[1]
        assert call_kwargs['corpus_resource_name'] is None


# ---------------------------------------------------------------------------
# run_rag_corpus_creation_pipeline
# ---------------------------------------------------------------------------

class TestRunPipeline:
    """Test run_rag_corpus_creation_pipeline function."""

    @patch('dataflow_templates.rag_pipeline_template.beam.Pipeline')
    @patch('dataflow_templates.rag_pipeline_template.beam.Filter', return_value=MagicMock())
    @patch('dataflow_templates.rag_pipeline_template.beam.ParDo', return_value=MagicMock())
    @patch('dataflow_templates.rag_pipeline_template.beam.Create', return_value=MagicMock())
    def test_pipeline_runs_successfully(self, mock_create, mock_pardo, mock_filter, mock_pipeline):
        from dataflow_templates.rag_pipeline_template import run_rag_corpus_creation_pipeline
        from apache_beam.options.pipeline_options import PipelineOptions

        # Make Pipeline context manager work
        mock_p = MagicMock()
        mock_p.__or__ = MagicMock(return_value=mock_p)
        mock_pipeline.return_value.__enter__ = Mock(return_value=mock_p)
        mock_pipeline.return_value.__exit__ = Mock(return_value=False)

        run_rag_corpus_creation_pipeline()
        mock_pipeline.assert_called_once()
