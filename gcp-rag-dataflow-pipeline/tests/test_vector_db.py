"""Unit tests for vectordatabase/vector_db.py."""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock, Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestInitializeVectorDb:
    """Test initialize_vector_db function."""

    @patch('vectordatabase.vector_db.create_vertex_vector_search')
    @patch('vectordatabase.vector_db.deploy_index_if_needed')
    @patch('vectordatabase.vector_db.get_or_create_endpoint')
    @patch('vectordatabase.vector_db.get_or_create_index')
    def test_vertexvectorsearch_success(self, mock_index, mock_endpoint, mock_deploy, mock_create_vvs):
        from vectordatabase.vector_db import initialize_vector_db

        mock_idx = MagicMock()
        mock_idx.resource_name = 'projects/p/locations/r/indexes/123'
        mock_index.return_value = mock_idx

        mock_ep = MagicMock()
        mock_ep.resource_name = 'projects/p/locations/r/indexEndpoints/456'
        mock_endpoint.return_value = mock_ep

        mock_deploy.return_value = 'test-corpus_deployed_index'
        mock_create_vvs.return_value = MagicMock()

        config = {
            'vector_db_type': 'VertexVectorSearch',
            'corpus_name': 'test-corpus',
            'project_id': 'test-project',
            'region': 'us-east4',
        }

        result = initialize_vector_db(config)
        assert result is not None
        mock_index.assert_called_once()
        mock_endpoint.assert_called_once()
        mock_deploy.assert_called_once()
        mock_create_vvs.assert_called_once_with(mock_idx.resource_name, mock_ep.resource_name)

    @patch('vectordatabase.vector_db.deploy_index_if_needed')
    @patch('vectordatabase.vector_db.get_or_create_endpoint')
    @patch('vectordatabase.vector_db.get_or_create_index')
    def test_vertexvectorsearch_deploy_failure(self, mock_index, mock_endpoint, mock_deploy):
        from vectordatabase.vector_db import initialize_vector_db

        mock_index.return_value = MagicMock()
        mock_endpoint.return_value = MagicMock()
        mock_deploy.return_value = None  # Deployment failed

        config = {
            'vector_db_type': 'VertexVectorSearch',
            'corpus_name': 'test-corpus',
            'project_id': 'test-project',
            'region': 'us-east4',
        }

        with pytest.raises(Exception, match="Failed to deploy index"):
            initialize_vector_db(config)

    def test_vertexvectorsearch_missing_project_id(self):
        from vectordatabase.vector_db import initialize_vector_db

        config = {
            'vector_db_type': 'VertexVectorSearch',
            'corpus_name': 'test-corpus',
            'region': 'us-east4',
        }

        with pytest.raises(ValueError, match="project_id is required"):
            initialize_vector_db(config)

    def test_vertexvectorsearch_missing_region(self):
        from vectordatabase.vector_db import initialize_vector_db

        config = {
            'vector_db_type': 'VertexVectorSearch',
            'corpus_name': 'test-corpus',
            'project_id': 'test-project',
        }

        with pytest.raises(ValueError, match="region is required"):
            initialize_vector_db(config)

    @patch('vectordatabase.vector_db.create_ann_db')
    def test_ragmanageddb_ann_strategy(self, mock_ann):
        from vectordatabase.vector_db import initialize_vector_db

        mock_ann.return_value = MagicMock()

        config = {
            'vector_db_type': 'RagManagedDb',
            'corpus_name': 'test-corpus',
            'project_id': 'test-project',
            'region': 'us-east4',
            'retrieval_strategy': 'ANN',
        }

        result = initialize_vector_db(config)
        assert result is not None
        mock_ann.assert_called_once_with(10, 500, 'test-project', 'us-east4')

    @patch('vectordatabase.vector_db.create_knn_db')
    def test_ragmanageddb_knn_strategy(self, mock_knn):
        from vectordatabase.vector_db import initialize_vector_db

        mock_knn.return_value = MagicMock()

        config = {
            'vector_db_type': 'RagManagedDb',
            'corpus_name': 'test-corpus',
            'project_id': 'test-project',
            'region': 'us-east4',
            'retrieval_strategy': 'KNN',
        }

        result = initialize_vector_db(config)
        assert result is not None
        mock_knn.assert_called_once_with('test-project', 'us-east4')

    @patch('vectordatabase.vector_db.create_rag_managed_db')
    def test_ragmanageddb_default_strategy(self, mock_default):
        from vectordatabase.vector_db import initialize_vector_db

        mock_default.return_value = MagicMock()

        config = {
            'vector_db_type': 'RagManagedDb',
            'corpus_name': 'test-corpus',
            'project_id': 'test-project',
            'region': 'us-east4',
            'retrieval_strategy': '',
        }

        initialize_vector_db(config)
        mock_default.assert_called_once_with('test-project', 'us-east4')

    def test_ragmanageddb_unsupported_strategy(self):
        from vectordatabase.vector_db import initialize_vector_db

        config = {
            'vector_db_type': 'RagManagedDb',
            'corpus_name': 'test-corpus',
            'project_id': 'test-project',
            'region': 'us-east4',
            'retrieval_strategy': 'INVALID',
        }

        with pytest.raises(ValueError, match="Unsupported retrieval strategy"):
            initialize_vector_db(config)

    def test_ragmanageddb_missing_project_id(self):
        from vectordatabase.vector_db import initialize_vector_db

        config = {
            'vector_db_type': 'RagManagedDb',
            'corpus_name': 'test-corpus',
            'region': 'us-east4',
            'retrieval_strategy': 'KNN',
        }

        with pytest.raises(ValueError, match="project_id is required"):
            initialize_vector_db(config)

    def test_unsupported_db_type(self):
        from vectordatabase.vector_db import initialize_vector_db

        config = {
            'vector_db_type': 'UnknownDB',
            'corpus_name': 'test-corpus',
            'project_id': 'test-project',
            'region': 'us-east4',
        }

        with pytest.raises(ValueError, match="Unsupported db_type"):
            initialize_vector_db(config)

    def test_missing_db_type(self):
        from vectordatabase.vector_db import initialize_vector_db

        config = {'corpus_name': 'test-corpus'}

        with pytest.raises(ValueError, match="Unsupported db_type"):
            initialize_vector_db(config)

    def test_empty_db_type(self):
        from vectordatabase.vector_db import initialize_vector_db

        config = {'vector_db_type': '', 'corpus_name': 'test-corpus'}

        with pytest.raises(ValueError, match="Unsupported db_type"):
            initialize_vector_db(config)

    def test_none_db_type(self):
        from vectordatabase.vector_db import initialize_vector_db

        config = {'vector_db_type': None, 'corpus_name': 'test-corpus'}

        with pytest.raises(ValueError, match="Unsupported db_type"):
            initialize_vector_db(config)
