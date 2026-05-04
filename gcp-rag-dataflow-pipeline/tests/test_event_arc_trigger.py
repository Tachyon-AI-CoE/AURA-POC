"""Unit tests for event_arc/event_arc_trigger.py."""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock, Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestCreateEventarcTrigger:
    """Test create_eventarc_trigger function."""

    @patch('event_arc.event_arc_trigger.eventarc_v1.EventarcClient')
    @patch('event_arc.event_arc_trigger.eventarc_v1.Trigger')
    @patch('event_arc.event_arc_trigger.eventarc_v1.EventFilter')
    @patch('event_arc.event_arc_trigger.eventarc_v1.Destination')
    @patch('event_arc.event_arc_trigger.eventarc_v1.CloudRun')
    def test_successful_trigger_creation(self, mock_cr, mock_dest, mock_filter, mock_trigger, mock_client_cls):
        from event_arc.event_arc_trigger import create_eventarc_trigger

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_operation = MagicMock()
        mock_result = MagicMock()
        mock_result.name = 'projects/p/locations/r/triggers/test-trigger'
        mock_operation.result.return_value = mock_result
        mock_client.create_trigger.return_value = mock_operation

        result = create_eventarc_trigger(
            trigger_name='test-trigger',
            bucket_name='test-bucket',
            project_id='test-project',
            location='us-east4',
            cloud_run_service='my-service',
            event_arc_service_account='sa@project.iam.gserviceaccount.com',
        )

        assert result['status'] == 'success'
        assert result['trigger_name'] == 'test-trigger'
        assert result['trigger_resource_name'] == 'projects/p/locations/r/triggers/test-trigger'

    @patch('event_arc.event_arc_trigger.eventarc_v1.EventarcClient')
    @patch('event_arc.event_arc_trigger.eventarc_v1.Trigger')
    @patch('event_arc.event_arc_trigger.eventarc_v1.EventFilter')
    @patch('event_arc.event_arc_trigger.eventarc_v1.Destination')
    @patch('event_arc.event_arc_trigger.eventarc_v1.CloudRun')
    def test_already_exists_returns_warning(self, mock_cr, mock_dest, mock_filter, mock_trigger, mock_client_cls):
        from event_arc.event_arc_trigger import create_eventarc_trigger
        from google.api_core import exceptions

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.create_trigger.side_effect = exceptions.AlreadyExists("Trigger exists")

        result = create_eventarc_trigger(
            trigger_name='existing-trigger',
            bucket_name='test-bucket',
            project_id='test-project',
            location='us-east4',
            cloud_run_service='my-service',
            event_arc_service_account='sa@project.iam.gserviceaccount.com',
        )

        assert result['status'] == 'warning'
        assert result['trigger_name'] == 'existing-trigger'

    @patch('event_arc.event_arc_trigger.eventarc_v1.EventarcClient')
    @patch('event_arc.event_arc_trigger.eventarc_v1.Trigger')
    @patch('event_arc.event_arc_trigger.eventarc_v1.EventFilter')
    @patch('event_arc.event_arc_trigger.eventarc_v1.Destination')
    @patch('event_arc.event_arc_trigger.eventarc_v1.CloudRun')
    def test_general_exception_returns_error(self, mock_cr, mock_dest, mock_filter, mock_trigger, mock_client_cls):
        from event_arc.event_arc_trigger import create_eventarc_trigger

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.create_trigger.side_effect = Exception("Network error")

        result = create_eventarc_trigger(
            trigger_name='fail-trigger',
            bucket_name='test-bucket',
            project_id='test-project',
            location='us-east4',
            cloud_run_service='my-service',
            event_arc_service_account='sa@project.iam.gserviceaccount.com',
        )

        assert result['status'] == 'error'
        assert 'Network error' in result['error']
