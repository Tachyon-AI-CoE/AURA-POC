"""Unit tests for doc_processor/summary_document_processor.py."""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock, Mock
import io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestExtractTextFromBlob:
    """Test extract_text_from_blob function."""

    def test_pdf_extraction(self):
        from doc_processor.summary_document_processor import extract_text_from_blob

        with patch('doc_processor.summary_document_processor.PdfReader') as mock_pdf:
            mock_blob = MagicMock()
            mock_blob.name = 'document.pdf'
            mock_blob.download_as_bytes.return_value = b'fake-pdf-bytes'

            mock_page = MagicMock()
            mock_page.extract_text.return_value = 'Page 1 content'
            mock_pdf.return_value.pages = [mock_page]

            result = extract_text_from_blob(mock_blob)
            assert result == 'Page 1 content'

    def test_docx_extraction(self):
        from doc_processor.summary_document_processor import extract_text_from_blob

        with patch('doc_processor.summary_document_processor.docx.Document') as mock_docx:
            mock_blob = MagicMock()
            mock_blob.name = 'document.docx'
            mock_blob.download_as_bytes.return_value = b'fake-docx-bytes'

            mock_para = MagicMock()
            mock_para.text = 'Paragraph 1'
            mock_docx.return_value.paragraphs = [mock_para]

            result = extract_text_from_blob(mock_blob)
            assert result == 'Paragraph 1'

    def test_csv_extraction(self):
        from doc_processor.summary_document_processor import extract_text_from_blob

        with patch('doc_processor.summary_document_processor.pd.read_csv') as mock_csv:
            mock_blob = MagicMock()
            mock_blob.name = 'data.csv'
            mock_blob.download_as_bytes.return_value = b'col1,col2\nval1,val2'

            mock_df = MagicMock()
            mock_df.to_string.return_value = 'col1 col2\nval1 val2'
            mock_csv.return_value = mock_df

            result = extract_text_from_blob(mock_blob)
            assert result == 'col1 col2\nval1 val2'

    def test_text_file_extraction(self):
        from doc_processor.summary_document_processor import extract_text_from_blob

        mock_blob = MagicMock()
        mock_blob.name = 'readme.txt'
        mock_blob.download_as_text.return_value = 'Hello world'

        result = extract_text_from_blob(mock_blob)
        assert result == 'Hello world'

    def test_unknown_file_type_uses_text(self):
        from doc_processor.summary_document_processor import extract_text_from_blob

        mock_blob = MagicMock()
        mock_blob.name = 'data.json'
        mock_blob.download_as_text.return_value = '{"key": "value"}'

        result = extract_text_from_blob(mock_blob)
        assert result == '{"key": "value"}'

    def test_extraction_error_returns_error_string(self):
        from doc_processor.summary_document_processor import extract_text_from_blob

        mock_blob = MagicMock()
        mock_blob.name = 'corrupt.pdf'
        mock_blob.download_as_bytes.side_effect = Exception("Download failed")

        result = extract_text_from_blob(mock_blob)
        assert '[Error reading corrupt.pdf' in result

    def test_pdf_with_multiple_pages(self):
        from doc_processor.summary_document_processor import extract_text_from_blob

        with patch('doc_processor.summary_document_processor.PdfReader') as mock_pdf:
            mock_blob = MagicMock()
            mock_blob.name = 'multipage.PDF'
            mock_blob.download_as_bytes.return_value = b'fake-pdf'

            page1 = MagicMock()
            page1.extract_text.return_value = 'Page 1'
            page2 = MagicMock()
            page2.extract_text.return_value = 'Page 2'
            mock_pdf.return_value.pages = [page1, page2]

            result = extract_text_from_blob(mock_blob)
            assert 'Page 1' in result
            assert 'Page 2' in result


class TestCreateSummaryUploadCallback:
    """Test create_summary_upload_callback function."""

    def test_returns_callback_and_container(self):
        from doc_processor.summary_document_processor import create_summary_upload_callback

        config = {'AGENT': {'SUMMARY_BUCKET': 'test-bucket'}}
        callback, container = create_summary_upload_callback(config)

        assert callable(callback)
        assert isinstance(container, dict)
        assert container['filename'] is None

    @patch('doc_processor.summary_document_processor.storage.Client')
    def test_callback_uploads_combined_summary(self, mock_storage_client):
        from doc_processor.summary_document_processor import create_summary_upload_callback

        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_storage_client.return_value.bucket.return_value = mock_bucket

        config = {'AGENT': {'SUMMARY_BUCKET': 'test-bucket'}}
        callback, container = create_summary_upload_callback(config)

        # Simulate LlmResponse
        mock_context = MagicMock()
        mock_context.agent_name = 'summariser_agent'

        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.text = 'This is a combined summary.'
        mock_part.function_call = None
        mock_response.content.parts = [mock_part]
        mock_response.error_message = None

        callback(mock_context, mock_response)
        mock_blob.upload_from_string.assert_called_once()

    @patch('doc_processor.summary_document_processor.storage.Client')
    def test_callback_splits_individual_summaries(self, mock_storage_client):
        from doc_processor.summary_document_processor import create_summary_upload_callback

        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_storage_client.return_value.bucket.return_value = mock_bucket

        config = {'AGENT': {'SUMMARY_BUCKET': 'test-bucket'}}
        callback, container = create_summary_upload_callback(config)

        mock_context = MagicMock()
        mock_context.agent_name = 'summariser_agent'

        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.text = '**SUMMARY FOR file1.txt:**\nContent 1\n**SUMMARY FOR file2.txt:**\nContent 2'
        mock_part.function_call = None
        mock_response.content.parts = [mock_part]
        mock_response.error_message = None

        callback(mock_context, mock_response)
        assert mock_blob.upload_from_string.call_count == 2

    def test_callback_no_bucket_skips_upload(self):
        from doc_processor.summary_document_processor import create_summary_upload_callback

        config = {'AGENT': {}}
        callback, container = create_summary_upload_callback(config)

        mock_context = MagicMock()
        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.text = 'summary'
        mock_part.function_call = None
        mock_response.content.parts = [mock_part]
        mock_response.error_message = None

        result = callback(mock_context, mock_response)
        assert result is None

    def test_callback_error_response(self):
        from doc_processor.summary_document_processor import create_summary_upload_callback

        config = {'AGENT': {}}
        callback, container = create_summary_upload_callback(config)

        mock_context = MagicMock()
        mock_response = MagicMock()
        mock_response.content = None
        mock_response.error_message = 'Something went wrong'

        result = callback(mock_context, mock_response)
        assert result is None

    def test_callback_empty_response(self):
        from doc_processor.summary_document_processor import create_summary_upload_callback

        config = {'AGENT': {}}
        callback, container = create_summary_upload_callback(config)

        mock_context = MagicMock()
        mock_response = MagicMock()
        mock_response.content = None
        mock_response.error_message = None

        result = callback(mock_context, mock_response)
        assert result is None


class TestCreateAndInitializeAgent:
    """Test create_and_initialize_agent function."""

    @patch('doc_processor.summary_document_processor.create_summary_upload_callback')
    @patch('doc_processor.summary_document_processor.extract_text_from_blob')
    @patch('doc_processor.summary_document_processor.storage.Client')
    def test_successful_initialization(self, mock_storage, mock_extract, mock_callback):
        from doc_processor.summary_document_processor import create_and_initialize_agent

        # Mock storage
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.name = 'test.txt'
        mock_bucket.list_blobs.return_value = [mock_blob]
        mock_storage.return_value.bucket.return_value = mock_bucket

        mock_extract.return_value = 'test content'

        mock_agent = MagicMock()
        mock_callback.return_value = (MagicMock(), {'filename': None})

        config = {
            'STORAGE': {'RAG_BUCKETS': {'SOURCE': 'source-bucket'}},
            'AGENT': {
                'SUMMARY_BUCKET': 'summary-bucket',
                'custom_summerization_prompt_instructions': 'test prompt',
            },
        }

        # create_summarizer_agent is imported inside the function via local sys.path append
        with patch('summarizer_agent.create_summarizer_agent', return_value=mock_agent):
            agent, container = create_and_initialize_agent(config)
            assert agent == mock_agent

    def test_missing_source_bucket_raises_error(self):
        from doc_processor.summary_document_processor import create_and_initialize_agent

        config = {'STORAGE': {'RAG_BUCKETS': {}}, 'AGENT': {}}

        with pytest.raises(ValueError, match="SOURCE bucket not found"):
            create_and_initialize_agent(config)

    @patch('doc_processor.summary_document_processor.create_summary_upload_callback')
    @patch('doc_processor.summary_document_processor.extract_text_from_blob')
    @patch('doc_processor.summary_document_processor.storage.Client')
    def test_uses_default_config_when_none(self, mock_storage, mock_extract, mock_callback):
        from doc_processor.summary_document_processor import create_and_initialize_agent

        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.name = 'test.txt'
        mock_bucket.list_blobs.return_value = [mock_blob]
        mock_storage.return_value.bucket.return_value = mock_bucket

        mock_extract.return_value = 'content'
        mock_callback.return_value = (MagicMock(), {'filename': None})

        with patch('summarizer_agent.create_summarizer_agent', return_value=MagicMock()):
            agent, container = create_and_initialize_agent(None)
            assert agent is not None
