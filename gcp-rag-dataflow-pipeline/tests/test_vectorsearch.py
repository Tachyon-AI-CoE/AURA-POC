"""Unit tests for vectordatabase/vectorsearch.py."""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock, Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestGetOrCreateIndex:
    """Test get_or_create_index function."""

    @patch('vectordatabase.vectorsearch.aiplatform.MatchingEngineIndex')
    def test_returns_existing_index(self, mock_index_cls):
        from vectordatabase.vectorsearch import get_or_create_index

        mock_existing = MagicMock()
        mock_existing.resource_name = 'projects/p/locations/r/indexes/123'
        mock_index_cls.list.return_value = [mock_existing]

        config = {'project_id': 'test-proj', 'region': 'us-east4'}
        result = get_or_create_index('test_index', config)

        assert result == mock_existing
        mock_index_cls.list.assert_called_once()

    @patch('vectordatabase.vectorsearch.config')
    @patch('vectordatabase.vectorsearch.aiplatform.MatchingEngineIndex')
    def test_creates_new_index_when_none_exists(self, mock_index_cls, mock_config):
        from vectordatabase.vectorsearch import get_or_create_index

        mock_index_cls.list.return_value = []
        mock_new_index = MagicMock()
        mock_new_index.resource_name = 'projects/p/locations/r/indexes/new'
        mock_index_cls.create_tree_ah_index.return_value = mock_new_index

        mock_config.LEAF_NODE_EMBEDDING_COUNT = 500
        mock_config.LEAF_NODES_TO_SEARCH_PERCENT = 7
        mock_config.FEATURE_NORM_TYPE = "UNIT_L2_NORM"
        mock_config.INDEX_UPDATE_METHOD = "STREAM_UPDATE"

        config = {
            'project_id': 'test-proj',
            'region': 'us-east4',
            'vector_db_dimensions': 768,
            'approximate_neighbours_count': 100,
            'distance_measure_type': 'DOT_PRODUCT_DISTANCE',
            'corpus_description': 'Test corpus',
        }

        result = get_or_create_index('test_index', config)
        assert result == mock_new_index
        mock_index_cls.create_tree_ah_index.assert_called_once()

    def test_missing_project_id_raises_error(self):
        from vectordatabase.vectorsearch import get_or_create_index

        config = {'region': 'us-east4'}
        with pytest.raises(ValueError, match="project_id is required"):
            get_or_create_index('test_index', config)

    def test_missing_region_raises_error(self):
        from vectordatabase.vectorsearch import get_or_create_index

        config = {'project_id': 'test-proj'}
        with pytest.raises(ValueError, match="region is required"):
            get_or_create_index('test_index', config)


class TestGetOrCreateEndpoint:
    """Test get_or_create_endpoint function."""

    @patch('vectordatabase.vectorsearch.aiplatform.MatchingEngineIndexEndpoint')
    def test_returns_existing_endpoint(self, mock_ep_cls):
        from vectordatabase.vectorsearch import get_or_create_endpoint

        mock_existing = MagicMock()
        mock_existing.resource_name = 'projects/p/locations/r/indexEndpoints/456'
        mock_ep_cls.list.return_value = [mock_existing]

        config = {'project_id': 'test-proj', 'region': 'us-east4'}
        result = get_or_create_endpoint('test_endpoint', config)

        assert result == mock_existing

    @patch('vectordatabase.vectorsearch.aiplatform.MatchingEngineIndexEndpoint')
    def test_creates_new_endpoint_when_none_exists(self, mock_ep_cls):
        from vectordatabase.vectorsearch import get_or_create_endpoint

        mock_ep_cls.list.return_value = []
        mock_new_ep = MagicMock()
        mock_ep_cls.create.return_value = mock_new_ep

        config = {'project_id': 'test-proj', 'region': 'us-east4'}
        result = get_or_create_endpoint('test_endpoint', config)

        assert result == mock_new_ep
        mock_ep_cls.create.assert_called_once()

    def test_missing_project_id_raises_error(self):
        from vectordatabase.vectorsearch import get_or_create_endpoint

        config = {'region': 'us-east4'}
        with pytest.raises(ValueError, match="project_id is required"):
            get_or_create_endpoint('test_endpoint', config)

    def test_missing_region_raises_error(self):
        from vectordatabase.vectorsearch import get_or_create_endpoint

        config = {'project_id': 'test-proj'}
        with pytest.raises(ValueError, match="region is required"):
            get_or_create_endpoint('test_endpoint', config)


class TestDeployIndexIfNeeded:
    """Test deploy_index_if_needed function."""

    def test_already_deployed_returns_id(self):
        from vectordatabase.vectorsearch import deploy_index_if_needed

        mock_deployed = MagicMock()
        mock_deployed.id = 'test_deployed_index'
        mock_endpoint = MagicMock()
        mock_endpoint.deployed_indexes = [mock_deployed]

        result = deploy_index_if_needed(mock_endpoint, MagicMock(), 'test_deployed_index')
        assert result == 'test_deployed_index'

    @patch('vectordatabase.vectorsearch.time.sleep')
    def test_deploys_new_index_and_polls(self, mock_sleep):
        from vectordatabase.vectorsearch import deploy_index_if_needed
        from unittest.mock import PropertyMock

        mock_deployed = MagicMock()
        mock_deployed.id = 'new_index'

        mock_endpoint = MagicMock()
        # PropertyMock to simulate: 1st access=[] (not deployed, enters deploy branch),
        # 2nd access=[] (while loop poll), 3rd access=[mock_deployed] (found)
        pm = PropertyMock(side_effect=[[], [], [mock_deployed]])
        type(mock_endpoint).deployed_indexes = pm

        result = deploy_index_if_needed(mock_endpoint, MagicMock(), 'new_index')
        assert result == 'new_index'

    def test_deploy_exception_returns_none(self):
        from vectordatabase.vectorsearch import deploy_index_if_needed
        from unittest.mock import PropertyMock

        mock_endpoint = MagicMock()
        pm = PropertyMock(side_effect=Exception("fail"))
        type(mock_endpoint).deployed_indexes = pm

        result = deploy_index_if_needed(mock_endpoint, MagicMock(), 'test_id')
        assert result is None


class TestCreateVertexVectorSearch:
    """Test create_vertex_vector_search function."""

    @patch('vectordatabase.vectorsearch.rag')
    def test_creates_vertex_vector_search(self, mock_rag):
        from vectordatabase.vectorsearch import create_vertex_vector_search

        mock_vvs = MagicMock()
        mock_rag.VertexVectorSearch.return_value = mock_vvs

        result = create_vertex_vector_search('index_name', 'endpoint_name')

        assert result == mock_vvs
        mock_rag.VertexVectorSearch.assert_called_once_with(
            index='index_name',
            index_endpoint='endpoint_name',
        )
