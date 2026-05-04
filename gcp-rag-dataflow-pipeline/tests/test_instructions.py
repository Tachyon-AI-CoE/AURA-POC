"""Unit tests for agents/summariser_agent/instuctions.py."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'agents', 'summariser_agent'))

from instuctions import get_batch_summary_instructions


class TestGetBatchSummaryInstructions:
    """Test get_batch_summary_instructions function."""

    def test_single_file_included_in_output(self):
        files = {'report.txt': 'Some report content'}
        result = get_batch_summary_instructions(files)
        assert 'report.txt' in result

    def test_multiple_files_included(self):
        files = {'file1.txt': 'Content 1', 'file2.pdf': 'Content 2'}
        result = get_batch_summary_instructions(files)
        assert 'file1.txt' in result
        assert 'file2.pdf' in result

    def test_file_content_included(self):
        files = {'data.csv': 'col1,col2\nval1,val2'}
        result = get_batch_summary_instructions(files)
        assert 'col1,col2' in result

    def test_custom_prompt_included(self):
        files = {'f.txt': 'content'}
        result = get_batch_summary_instructions(files, 'Use bullet points only')
        assert 'Use bullet points only' in result

    def test_empty_custom_prompt(self):
        files = {'f.txt': 'content'}
        result = get_batch_summary_instructions(files, '')
        assert 'Document Summarizer' in result

    def test_file_delimiters_present(self):
        files = {'test.txt': 'Hello'}
        result = get_batch_summary_instructions(files)
        assert '=== FILE: test.txt ===' in result
        assert '=== END OF test.txt ===' in result

    def test_empty_files_map(self):
        result = get_batch_summary_instructions({})
        assert 'Document Summarizer' in result

    def test_chain_of_thought_mentioned(self):
        files = {'f.txt': 'c'}
        result = get_batch_summary_instructions(files)
        assert 'Chain-of-Thought' in result

    def test_output_format_instructions(self):
        files = {'f.txt': 'c'}
        result = get_batch_summary_instructions(files)
        assert 'SUMMARY FOR' in result

    def test_returns_string(self):
        files = {'f.txt': 'c'}
        result = get_batch_summary_instructions(files)
        assert isinstance(result, str)
