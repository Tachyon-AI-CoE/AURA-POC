"""Unit tests for doc_processor/run_agent.py."""

import sys
import os
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestRunAgent:
    """Test run_agent function."""

    @patch('doc_processor.run_agent.Runner')
    @patch('doc_processor.run_agent.InMemorySessionService')
    @patch('doc_processor.run_agent.create_and_initialize_agent')
    def test_run_agent_returns_responses(self, mock_create_agent, mock_session_svc, mock_runner_cls):
        from doc_processor.run_agent import run_agent

        mock_agent = MagicMock()
        mock_container = {'filenames': ['summary.txt']}
        mock_create_agent.return_value = (mock_agent, mock_container)

        mock_session = MagicMock()
        mock_session.id = 'session-123'
        mock_svc_instance = MagicMock()
        mock_svc_instance.create_session = AsyncMock(return_value=mock_session)
        mock_session_svc.return_value = mock_svc_instance

        mock_event = MagicMock()
        mock_event.content.parts = [MagicMock(text='Summary result')]
        mock_runner = MagicMock()

        async def mock_run_async(**kwargs):
            yield mock_event

        mock_runner.run_async = mock_run_async
        mock_runner_cls.return_value = mock_runner

        config = {
            'STORAGE': {'RAG_BUCKETS': {'SOURCE': 'bucket'}},
            'AGENT': {'SUMMARY_BUCKET': 'summary'},
        }

        responses, filenames = asyncio.run(run_agent(config))

        assert len(responses) == 1
        assert responses[0] == 'Summary result'
        assert filenames == ['summary.txt']

    @patch('doc_processor.run_agent.Runner')
    @patch('doc_processor.run_agent.InMemorySessionService')
    @patch('doc_processor.run_agent.create_and_initialize_agent')
    def test_run_agent_handles_no_content(self, mock_create_agent, mock_session_svc, mock_runner_cls):
        from doc_processor.run_agent import run_agent

        mock_create_agent.return_value = (MagicMock(), {'filenames': []})

        mock_session = MagicMock()
        mock_session.id = 'session-123'
        mock_svc_instance = MagicMock()
        mock_svc_instance.create_session = AsyncMock(return_value=mock_session)
        mock_session_svc.return_value = mock_svc_instance

        mock_event = MagicMock()
        mock_event.content = None
        mock_runner = MagicMock()

        async def mock_run_async(**kwargs):
            yield mock_event

        mock_runner.run_async = mock_run_async
        mock_runner_cls.return_value = mock_runner

        responses, filenames = asyncio.run(run_agent({}))
        assert responses[0] == '[No content]'


class TestTriggerAgent:
    """Test trigger_agent function."""

    @patch('doc_processor.run_agent.run_agent')
    def test_trigger_agent_delegates_to_run_agent(self, mock_run):
        from doc_processor.run_agent import trigger_agent

        mock_run.return_value = (['response'], ['file.txt'])

        async def run_test():
            return await trigger_agent({'key': 'value'})

        responses, files = asyncio.run(run_test())
        assert responses == ['response']
        mock_run.assert_called_once_with({'key': 'value'})
