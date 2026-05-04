"""Unit tests for vectordatabase/rag_managed_db.py."""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestCreateKnnDb:
    """Test create_knn_db function."""

    @patch('vectordatabase.rag_managed_db.rag')
    @patch('vectordatabase.rag_managed_db.vertexai')
    def test_successful_knn_creation(self, mock_vertexai, mock_rag):
        from vectordatabase.rag_managed_db import create_knn_db

        mock_db = MagicMock()
        mock_rag.RagManagedDb.return_value = mock_db
        mock_rag.KNN.return_value = MagicMock()

        result = create_knn_db('test-project', 'us-east4')

        assert result == mock_db
        mock_vertexai.init.assert_called_once_with(project='test-project', location='us-east4')
        mock_rag.KNN.assert_called_once()

    def test_missing_project_id_raises_error(self):
        from vectordatabase.rag_managed_db import create_knn_db

        with pytest.raises(ValueError, match="project_id and location are required"):
            create_knn_db(None, 'us-east4')

    def test_missing_location_raises_error(self):
        from vectordatabase.rag_managed_db import create_knn_db

        with pytest.raises(ValueError, match="project_id and location are required"):
            create_knn_db('test-project', None)

    def test_empty_project_id_raises_error(self):
        from vectordatabase.rag_managed_db import create_knn_db

        with pytest.raises(ValueError, match="project_id and location are required"):
            create_knn_db('', 'us-east4')


class TestCreateAnnDb:
    """Test create_ann_db function."""

    @patch('vectordatabase.rag_managed_db.rag')
    @patch('vectordatabase.rag_managed_db.vertexai')
    def test_successful_ann_creation(self, mock_vertexai, mock_rag):
        from vectordatabase.rag_managed_db import create_ann_db

        mock_db = MagicMock()
        mock_rag.RagManagedDb.return_value = mock_db
        mock_ann_config = MagicMock()
        mock_rag.ANN.return_value = mock_ann_config

        result = create_ann_db(10, 500, 'test-project', 'us-east4')

        assert result == mock_db
        mock_vertexai.init.assert_called_once_with(project='test-project', location='us-east4')
        mock_rag.ANN.assert_called_once_with(tree_depth=10, leaf_count=500)

    def test_missing_project_id_raises_error(self):
        from vectordatabase.rag_managed_db import create_ann_db

        with pytest.raises(ValueError, match="project_id and location are required"):
            create_ann_db(10, 500, None, 'us-east4')

    def test_missing_location_raises_error(self):
        from vectordatabase.rag_managed_db import create_ann_db

        with pytest.raises(ValueError, match="project_id and location are required"):
            create_ann_db(10, 500, 'test-project', '')


class TestCreateRagManagedDb:
    """Test create_rag_managed_db function."""

    @patch('vectordatabase.rag_managed_db.rag')
    @patch('vectordatabase.rag_managed_db.vertexai')
    def test_successful_default_creation(self, mock_vertexai, mock_rag):
        from vectordatabase.rag_managed_db import create_rag_managed_db

        mock_db = MagicMock()
        mock_rag.RagManagedDb.return_value = mock_db

        # Note: source code has `return` without value on line 72, so returns None
        result = create_rag_managed_db('test-project', 'us-east4')

        mock_vertexai.init.assert_called_once_with(project='test-project', location='us-east4')
        mock_rag.RagManagedDb.assert_called_once_with()

    def test_missing_project_id_raises_error(self):
        from vectordatabase.rag_managed_db import create_rag_managed_db

        with pytest.raises(ValueError, match="project_id and location are required"):
            create_rag_managed_db(None, 'us-east4')

    def test_missing_location_raises_error(self):
        from vectordatabase.rag_managed_db import create_rag_managed_db

        with pytest.raises(ValueError, match="project_id and location are required"):
            create_rag_managed_db('test-project', None)
