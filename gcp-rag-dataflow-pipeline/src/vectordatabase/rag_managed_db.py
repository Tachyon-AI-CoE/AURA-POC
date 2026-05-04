from vertexai import rag
import vertexai
from google.cloud import aiplatform
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DO NOT initialize vertexai at module level - it will be initialized per function
# with the correct region from the pipeline config


def create_knn_db(project_id, location):
    """
    Initializes and returns a RagManagedDB instance with KNN retrieval strategy.
    
    Args:
        project_id: GCP project ID (required)
        location: GCP region (required)
    """
    if not project_id or not location:
        raise ValueError(f"project_id and location are required. Got project_id={project_id}, location={location}")
    
    # Initialize vertexai
    vertexai.init(project=project_id, location=location)
    # logger.info(f"✅ Initialized Vertex AI: project={project_id}, location={location}")
    
    vector_db = rag.RagManagedDb(retrieval_strategy=rag.KNN())
    logger.info("✅ Initialized KNN-based RagManagedDb")
    return vector_db

def create_ann_db(tree_depth, leaf_count, project_id, location):
    """
    Initializes and returns a RagManagedDb instance with ANN retrieval strategy.
    
    Args:
        tree_depth: Tree depth for ANN
        leaf_count: Leaf count for ANN
        project_id: GCP project ID (required)
        location: GCP region (required)
    """
    if not project_id or not location:
        raise ValueError(f"project_id and location are required. Got project_id={project_id}, location={location}")
    
    # Initialize vertexai
    vertexai.init(project=project_id, location=location)
    # logger.info(f"✅ Initialized Vertex AI: project={project_id}, location={location}")
    
    ann_config = rag.ANN(tree_depth=tree_depth, leaf_count=leaf_count)
    vector_db = rag.RagManagedDb(retrieval_strategy=ann_config)
    logger.info(f"✅ Initialized ANN-based RagManagedDb with tree_depth={tree_depth}, leaf_count={leaf_count}")
    return vector_db

def create_rag_managed_db(project_id, location):
    """
    Initializes and returns a RagManagedDb instance with default settings.
    
    Args:
        project_id: GCP project ID (required)
        location: GCP region (required)
    """
    if not project_id or not location:
        raise ValueError(f"project_id and location are required. Got project_id={project_id}, location={location}")
    
    # Initialize vertexai
    vertexai.init(project=project_id, location=location)
    # logger.info(f"✅ Initialized Vertex AI: project={project_id}, location={location}")
    
    vector_db = rag.RagManagedDb()
    logger.info("✅ Initialized RagManagedDb with default settings")
    return
