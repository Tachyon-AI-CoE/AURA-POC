"""Unit tests for agents/summariser_agent/summarizer_agent.py."""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'agents', 'summariser_agent'))


class TestCreateSummarizerAgent:
    """Test create_summarizer_agent function."""

    @patch('summarizer_agent.LlmAgent')
    @patch('summarizer_agent.get_batch_summary_instructions')
    def test_creates_agent_with_content(self, mock_instructions, mock_llm_agent):
        from summarizer_agent import create_summarizer_agent

        mock_instructions.return_value = 'Generated instructions'
        mock_agent = MagicMock()
        mock_llm_agent.return_value = mock_agent

        files = {'file1.txt': 'content1', 'file2.txt': 'content2'}
        result = create_summarizer_agent(files)

        assert result == mock_agent
        mock_instructions.assert_called_once_with(files, '')
        mock_llm_agent.assert_called_once()

    @patch('summarizer_agent.LlmAgent')
    @patch('summarizer_agent.get_batch_summary_instructions')
    def test_creates_agent_with_custom_prompt(self, mock_instructions, mock_llm_agent):
        from summarizer_agent import create_summarizer_agent

        mock_instructions.return_value = 'Custom instructions'
        mock_llm_agent.return_value = MagicMock()

        files = {'file1.txt': 'content'}
        create_summarizer_agent(files, custom_prompt='Summarize in bullets')

        mock_instructions.assert_called_once_with(files, 'Summarize in bullets')

    @patch('summarizer_agent.LlmAgent')
    @patch('summarizer_agent.get_batch_summary_instructions')
    def test_creates_agent_with_callback(self, mock_instructions, mock_llm_agent):
        from summarizer_agent import create_summarizer_agent

        mock_instructions.return_value = 'instructions'
        mock_llm_agent.return_value = MagicMock()

        callback = MagicMock()
        files = {'file1.txt': 'content'}
        create_summarizer_agent(files, callback_func=callback)

        call_kwargs = mock_llm_agent.call_args[1]
        assert call_kwargs['after_model_callback'] == callback

    def test_empty_files_raises_error(self):
        with pytest.raises(ValueError, match="files_content_map cannot be empty"):
            from summarizer_agent import create_summarizer_agent
            create_summarizer_agent({})

    @patch('summarizer_agent.LlmAgent')
    @patch('summarizer_agent.get_batch_summary_instructions')
    def test_agent_uses_gemini_model(self, mock_instructions, mock_llm_agent):
        from summarizer_agent import create_summarizer_agent

        mock_instructions.return_value = 'instructions'
        mock_llm_agent.return_value = MagicMock()

        create_summarizer_agent({'f.txt': 'c'})

        call_kwargs = mock_llm_agent.call_args[1]
        assert call_kwargs['model'] == 'gemini-2.0-flash'
        assert call_kwargs['name'] == 'summariser_agent'
