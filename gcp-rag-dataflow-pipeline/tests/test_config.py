"""Unit tests for config/config.py — static constants."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import config


class TestConfigConstants:
    """Test that static configuration constants are defined correctly."""

    def test_feature_norm_type(self):
        assert config.FEATURE_NORM_TYPE == "UNIT_L2_NORM"

    def test_index_update_method(self):
        assert config.INDEX_UPDATE_METHOD == "STREAM_UPDATE"

    def test_leaf_node_embedding_count(self):
        assert config.LEAF_NODE_EMBEDDING_COUNT == 500

    def test_leaf_nodes_to_search_percent(self):
        assert config.LEAF_NODES_TO_SEARCH_PERCENT == 7

    def test_tree_depth(self):
        assert config.TREE_DEPTH == 10

    def test_leaf_count(self):
        assert config.LEAF_COUNT == 500

    def test_all_constants_are_integers_or_strings(self):
        assert isinstance(config.FEATURE_NORM_TYPE, str)
        assert isinstance(config.INDEX_UPDATE_METHOD, str)
        assert isinstance(config.LEAF_NODE_EMBEDDING_COUNT, int)
        assert isinstance(config.LEAF_NODES_TO_SEARCH_PERCENT, int)
        assert isinstance(config.TREE_DEPTH, int)
        assert isinstance(config.LEAF_COUNT, int)
