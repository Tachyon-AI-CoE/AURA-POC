"""Unit tests for rag/rag_engine.py."""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestGetOrCreateCorpus:
    """Test get_or_create_corpus function."""

    @patch('rag.rag_engine.rag')
    @patch('rag.rag_engine.vertexai')
    def test_returns_existing_corpus(self, mock_vertexai, mock_rag):
        from rag.rag_engine import get_or_create_corpus

        mock_corpus = MagicMock()
        mock_corpus.display_name = 'test-corpus'
        mock_corpus.name = 'projects/p/locations/r/ragCorpora/123'
        mock_rag.list_corpora.return_value = [mock_corpus]

        result = get_or_create_corpus(MagicMock(), 'test-corpus', 'test-proj', 'us-east4')

        assert result == mock_corpus
        mock_rag.create_corpus.assert_not_called()

    @patch('rag.rag_engine.rag')
    @patch('rag.rag_engine.vertexai')
    def test_creates_new_corpus(self, mock_vertexai, mock_rag):
        from rag.rag_engine import get_or_create_corpus

        mock_rag.list_corpora.return_value = []
        mock_new_corpus = MagicMock()
        mock_new_corpus.name = 'projects/p/locations/r/ragCorpora/456'
        mock_rag.create_corpus.return_value = mock_new_corpus

        result = get_or_create_corpus(MagicMock(), 'new-corpus', 'test-proj', 'us-east4')

        assert result == mock_new_corpus
        mock_rag.create_corpus.assert_called_once()

    @patch('rag.rag_engine.rag')
    @patch('rag.rag_engine.vertexai')
    def test_handles_race_condition(self, mock_vertexai, mock_rag):
        from rag.rag_engine import get_or_create_corpus

        mock_rag.list_corpora.side_effect = [
            [],  # First call: no corpus
            [MagicMock(display_name='race-corpus', name='projects/p/locations/r/ragCorpora/789')],
        ]
        mock_rag.create_corpus.side_effect = Exception("already exists")

        result = get_or_create_corpus(MagicMock(), 'race-corpus', 'test-proj', 'us-east4')
        assert result.display_name == 'race-corpus'

    @patch('rag.rag_engine.rag')
    @patch('rag.rag_engine.vertexai')
    def test_raises_on_non_duplicate_error(self, mock_vertexai, mock_rag):
        from rag.rag_engine import get_or_create_corpus

        mock_rag.list_corpora.return_value = []
        mock_rag.create_corpus.side_effect = Exception("permission denied")

        with pytest.raises(Exception, match="permission denied"):
            get_or_create_corpus(MagicMock(), 'fail-corpus', 'test-proj', 'us-east4')

    def test_missing_project_id_raises_error(self):
        from rag.rag_engine import get_or_create_corpus

        with pytest.raises(ValueError, match="project_id and region are required"):
            get_or_create_corpus(MagicMock(), 'test', None, 'us-east4')

    def test_missing_region_raises_error(self):
        from rag.rag_engine import get_or_create_corpus

        with pytest.raises(ValueError, match="project_id and region are required"):
            get_or_create_corpus(MagicMock(), 'test', 'proj', None)


class TestGetResultPath:
    """Test get_result_path function."""

    @patch('rag.rag_engine.datetime')
    def test_result_path_with_corpus_name(self, mock_dt):
        from rag.rag_engine import get_result_path

        mock_dt.now.return_value.strftime.return_value = '20231201-120000'

        config = {
            'corpus_name': 'test-corpus',
            'result_bucket': 'results-bucket',
        }

        result = get_result_path(config)
        assert result == 'gs://results-bucket/test-corpus/rag_results-20231201-120000.ndjson'

    @patch('rag.rag_engine.datetime')
    def test_result_path_without_corpus_name(self, mock_dt):
        from rag.rag_engine import get_result_path

        mock_dt.now.return_value.strftime.return_value = '20231201-120000'

        config = {'result_bucket': 'results-bucket'}
        result = get_result_path(config)
        assert result == 'gs://results-bucket/rag_results-20231201-120000.ndjson'

    def test_missing_result_bucket_raises_error(self):
        from rag.rag_engine import get_result_path

        with pytest.raises(ValueError, match="result_bucket is required"):
            get_result_path({'corpus_name': 'test'})


class TestImportFilesToCorpus:
    """Test import_files_to_corpus function."""

    @patch('rag.rag_engine.get_result_path', return_value='gs://bucket/results.ndjson')
    @patch('rag.rag_engine.rag')
    def test_gcs_import_success(self, mock_rag, mock_result_path):
        from rag.rag_engine import import_files_to_corpus

        mock_response = MagicMock()
        mock_response.imported_rag_files_count = 10
        mock_response.skipped_rag_files_count = 2
        mock_rag.import_files.return_value = mock_response

        config = {
            'data_source_type': 'gcs',
            'result_bucket': 'results-bucket',
            'chunk_size': 512,
            'chunk_overlap': 100,
        }
        mock_corpus = MagicMock()
        mock_corpus.name = 'projects/p/locations/r/ragCorpora/123'

        result = import_files_to_corpus(config, mock_corpus, 'gs://source-bucket/**')

        assert result == mock_response
        mock_rag.import_files.assert_called_once()

    @patch('rag.rag_engine.get_result_path', return_value='gs://bucket/results.ndjson')
    @patch('rag.rag_engine.rag')
    def test_non_gcs_import_uses_source_param(self, mock_rag, mock_result_path):
        from rag.rag_engine import import_files_to_corpus

        mock_response = MagicMock()
        mock_response.imported_rag_files_count = 5
        mock_response.skipped_rag_files_count = 0
        mock_rag.import_files.return_value = mock_response

        config = {
            'data_source_type': 'jira',
            'result_bucket': 'results-bucket',
        }
        mock_corpus = MagicMock()
        mock_corpus.name = 'projects/p/locations/r/ragCorpora/123'
        mock_jira_source = MagicMock()

        result = import_files_to_corpus(config, mock_corpus, mock_jira_source)

        assert result == mock_response
        # Verify 'source' keyword used instead of 'paths'
        call_kwargs = mock_rag.import_files.call_args[1]
        assert 'source' in call_kwargs

    @patch('rag.rag_engine.get_result_path', return_value='gs://bucket/results.ndjson')
    @patch('rag.rag_engine.rag')
    def test_gcs_import_failure_raises(self, mock_rag, mock_result_path):
        from rag.rag_engine import import_files_to_corpus

        mock_rag.import_files.side_effect = Exception("Import failed")

        config = {
            'data_source_type': 'gcs',
            'result_bucket': 'results-bucket',
        }

        with pytest.raises(Exception, match="Import failed"):
            import_files_to_corpus(config, MagicMock(), 'gs://bucket/**')

    @patch('rag.rag_engine.get_result_path', return_value='gs://bucket/results.ndjson')
    @patch('rag.rag_engine.rag')
    def test_non_gcs_import_failure_raises(self, mock_rag, mock_result_path):
        from rag.rag_engine import import_files_to_corpus

        mock_rag.import_files.side_effect = Exception("JIRA import failed")

        config = {
            'data_source_type': 'jira',
            'result_bucket': 'results-bucket',
        }

        with pytest.raises(Exception, match="JIRA import failed"):
            import_files_to_corpus(config, MagicMock(), MagicMock())
