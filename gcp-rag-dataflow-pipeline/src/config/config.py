"""
Configuration for RAG Pipeline.
Simple constants with direct config loading.
"""

import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Vector Search Config Values (static defaults)
FEATURE_NORM_TYPE = "UNIT_L2_NORM"
INDEX_UPDATE_METHOD = "STREAM_UPDATE"
LEAF_NODE_EMBEDDING_COUNT = 500
LEAF_NODES_TO_SEARCH_PERCENT = 7
TREE_DEPTH = 10
LEAF_COUNT = 500
