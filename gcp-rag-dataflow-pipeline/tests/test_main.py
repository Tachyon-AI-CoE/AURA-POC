"""Unit tests for main.py — Cloud Function handler."""

import sys
import os
import json
import base64
import types
import pytest
from unittest.mock import patch, MagicMock, Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def _import_main():
    """Import main module with all missing dependencies mocked."""
    # main.py does top-level imports that may not exist:
    #   from config.config import load_config
    #   from event_processor.gcs_event_processor import validate_gcs_eventfile
    #   from rag.rag_pipeline import run_pipeline
    # We need to mock these before import.

    # Mock config.config.load_config
    import config.config as cfg_mod
    if not hasattr(cfg_mod, 'load_config'):
        cfg_mod.load_config = MagicMock()

    # Mock event_processor.gcs_event_processor.validate_gcs_eventfile
    import event_processor.gcs_event_processor as ep_mod
    if not hasattr(ep_mod, 'validate_gcs_eventfile'):
        ep_mod.validate_gcs_eventfile = MagicMock()

    # Mock rag.rag_pipeline module
    if 'rag.rag_pipeline' not in sys.modules:
        rp_mod = types.ModuleType('rag.rag_pipeline')
        rp_mod.run_pipeline = MagicMock()
        sys.modules['rag.rag_pipeline'] = rp_mod

    # Now import main
    if 'main' in sys.modules:
        import importlib
        return importlib.reload(sys.modules['main'])
    import main
    return main


class TestRagPipelineHandler:
    """Test rag_pipeline_handler Cloud Function."""

    def test_gcs_event_processed(self):
        main_mod = _import_main()

        with patch.object(main_mod, 'executor') as mock_executor, \
             patch.object(main_mod, 'validate_gcs_eventfile', return_value={'corpus_name': 'test-corpus'}), \
             patch.object(main_mod, 'storage') as mock_storage, \
             patch.object(main_mod, 'make_response') as mock_response:

            mock_resp = MagicMock()
            mock_response.return_value = mock_resp

            cloud_event = MagicMock()
            cloud_event.data = {'bucket': 'test-bucket', 'name': 'config.json'}

            result = main_mod.rag_pipeline_handler(cloud_event)

            assert result == mock_resp
            mock_executor.submit.assert_called_once()

    def test_pubsub_event_processed(self):
        main_mod = _import_main()

        message_data = base64.b64encode(json.dumps({'rag_corpus': {'corpus_name': 'test'}}).encode()).decode()

        with patch.object(main_mod, 'executor') as mock_executor, \
             patch.object(main_mod, 'get_flattened_rag_pipeline_config', return_value={'corpus_name': 'test'}), \
             patch.object(main_mod, 'convert_string_to_json', return_value={'rag_corpus': {'corpus_name': 'test'}}), \
             patch.object(main_mod, 'storage'), \
             patch.object(main_mod, 'make_response') as mock_response:

            mock_resp = MagicMock()
            mock_response.return_value = mock_resp

            cloud_event = MagicMock()
            cloud_event.data = {'message': {'data': message_data}}

            result = main_mod.rag_pipeline_handler(cloud_event)

            assert result == mock_resp
            mock_executor.submit.assert_called_once()

    def test_unknown_event_type(self):
        main_mod = _import_main()

        with patch.object(main_mod, 'make_response') as mock_response:
            mock_resp = MagicMock()
            mock_response.return_value = mock_resp

            cloud_event = MagicMock()
            cloud_event.data = {'unknown_field': 'value'}

            main_mod.rag_pipeline_handler(cloud_event)
            mock_response.assert_called_with("Unknown event type", 400)

    def test_missing_bucket_in_gcs_event(self):
        main_mod = _import_main()

        with patch.object(main_mod, 'make_response') as mock_response:
            mock_resp = MagicMock()
            mock_response.return_value = mock_resp

            cloud_event = MagicMock()
            cloud_event.data = {'bucket': '', 'name': 'config.json'}

            main_mod.rag_pipeline_handler(cloud_event)
            mock_response.assert_called_with("Missing bucket or eventfile_name", 400)

    def test_missing_message_data_in_pubsub(self):
        main_mod = _import_main()

        with patch.object(main_mod, 'make_response') as mock_response:
            mock_resp = MagicMock()
            mock_response.return_value = mock_resp

            cloud_event = MagicMock()
            cloud_event.data = {'message': {}}

            main_mod.rag_pipeline_handler(cloud_event)
            mock_response.assert_called_with("Missing message data", 400)

    def test_exception_returns_500(self):
        main_mod = _import_main()

        with patch.object(main_mod, 'make_response') as mock_response:
            mock_resp = MagicMock()
            mock_response.return_value = mock_resp

            cloud_event = MagicMock()
            cloud_event.data = None  # Will cause exception when checking 'bucket' in data

            main_mod.rag_pipeline_handler(cloud_event)
            mock_response.assert_called_with("Internal server error", 500)

    def test_bytes_data_decoded(self):
        main_mod = _import_main()

        with patch.object(main_mod, 'executor') as mock_executor, \
             patch.object(main_mod, 'validate_gcs_eventfile', return_value={'corpus_name': 'test'}), \
             patch.object(main_mod, 'storage'), \
             patch.object(main_mod, 'make_response') as mock_response:

            mock_resp = MagicMock()
            mock_response.return_value = mock_resp

            cloud_event = MagicMock()
            cloud_event.data = json.dumps({'bucket': 'b', 'name': 'n'}).encode('utf-8')

            main_mod.rag_pipeline_handler(cloud_event)
            assert main_mod.validate_gcs_eventfile.called
