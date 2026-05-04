from google.cloud import aiplatform
from vertexai import rag
from typing import Dict, Any
import logging
import pprint
import time


# Configure logging level from config
from config import config  # This will trigger central logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_or_create_index(index_display_name: str, rag_pipeline_config: Dict[str, Any]) -> aiplatform.MatchingEngineIndex:
    """
    Get existing index or create a new one using the provided rag_pipeline_config.
    
    Args:
        index_display_name: Display name for the index
        rag_pipeline_config: RAG pipeline configuration containing dimensions, neighbors count, etc.
                         This parameter is required and must contain the necessary configuration values.
        
    Returns:
        MatchingEngineIndex: The existing or newly created index
    """
    # Extract project_id and region from config (passed from Dataflow pipeline options)
    project_id = rag_pipeline_config.get("project_id")
    region = rag_pipeline_config.get("region")
    
    if not project_id:
        raise ValueError("project_id is required in config. Pass --project argument to Dataflow job")
    if not region:
        raise ValueError("region is required in config. Add it to config file or pass --region argument")
    
    logger.info(f"📍 Using project_id={project_id}, region={region} for Vector Search")
    
    # Check if index already exists
    logger.info(f"Checking for existing index with display name: {index_display_name}")
    indexes = aiplatform.MatchingEngineIndex.list(
        filter=f'display_name="{index_display_name}"'
    )
    
    if indexes:
        index = indexes[0]
        logger.info(f"✅ Using existing index: {index.resource_name}")
        logger.info(f"   Index ID: {index.name}")
        return index

    # Extract configuration from rag_pipeline_config (required parameter)
    dimensions = rag_pipeline_config.get("vector_db_dimensions", 768)
    approximate_neighbors_count = rag_pipeline_config.get("approximate_neighbours_count", 100)
    distance_measure_type = rag_pipeline_config.get("distance_measure_type", "DOT_PRODUCT_DISTANCE")
    description = rag_pipeline_config.get("corpus_description")

    logger.info(f"Using rag_pipeline_config: dimensions={dimensions}, neighbors={approximate_neighbors_count}, distance={distance_measure_type}")

    logger.info(f"🔨 Creating new index: {index_display_name}")
    index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
        project=project_id,
        location=region,
        display_name=index_display_name,
        description=description,
        dimensions=dimensions,
        approximate_neighbors_count=approximate_neighbors_count,
        leaf_node_embedding_count=config.LEAF_NODE_EMBEDDING_COUNT,
        leaf_nodes_to_search_percent=config.LEAF_NODES_TO_SEARCH_PERCENT,
        distance_measure_type=distance_measure_type,
        feature_norm_type=config.FEATURE_NORM_TYPE,
        index_update_method=config.INDEX_UPDATE_METHOD
    )
    logger.info(f"✅ Created new index: {index.resource_name}")
    return index

def get_or_create_endpoint(endpoint_display_name: str, rag_pipeline_config: Dict[str, Any]) -> aiplatform.MatchingEngineIndexEndpoint:
    """
    Get existing endpoint or create a new one.
    
    Args:
        endpoint_display_name: Display name for the endpoint
        rag_pipeline_config: RAG pipeline configuration containing project_id and region
        
    Returns:
        MatchingEngineIndexEndpoint: The existing or newly created endpoint
    """
    # Extract project_id and region from config (passed from Dataflow pipeline options)
    project_id = rag_pipeline_config.get("project_id")
    region = rag_pipeline_config.get("region")
    
    if not project_id:
        raise ValueError("project_id is required in config. Pass --project argument to Dataflow job")
    if not region:
        raise ValueError("region is required in config. Add it to config file or pass --region argument")
    
    logger.info(f"📍 Using project_id={project_id}, region={region} for Vector Search Endpoint")
    
    # Check if endpoint already exists
    logger.info(f"Checking for existing endpoint with display name: {endpoint_display_name}")
    endpoints = aiplatform.MatchingEngineIndexEndpoint.list(
        filter=f'display_name="{endpoint_display_name}"'
    )
    
    if endpoints:
        endpoint = endpoints[0]
        logger.info(f"✅ Using existing endpoint: {endpoint.resource_name}")
        logger.info(f"   Endpoint ID: {endpoint.name}")
        return endpoint
    
    logger.info(f"🔨 Creating new endpoint: {endpoint_display_name}")
    endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
        project=project_id,
        location=region,
        display_name=endpoint_display_name, 
        public_endpoint_enabled=True,
        create_request_timeout=300
    )
    logger.info(f"✅ Created new endpoint: {endpoint.resource_name}")
    return endpoint

def deploy_index_if_needed(endpoint, index, deployed_index_id: str): #async
    """
    Deploy index to endpoint if not already deployed.
    
    Args:
        endpoint: The MatchingEngineIndexEndpoint
        index: The MatchingEngineIndex to deploy
        deployed_index_id: ID for the deployed index
        
    Returns:
        str: deployed_index_id if deployment successful or already deployed, None if failed
    """
    try:
        deployed_indices = [d.id for d in endpoint.deployed_indexes]
        logger.info(f"Current deployed indices: {deployed_indices}")
        
        if deployed_index_id not in deployed_indices:
            logger.info(f"🚀 Deploying index {deployed_index_id} to endpoint {endpoint.display_name}")
            operation = endpoint.deploy_index(index=index, deployed_index_id=deployed_index_id, sync=False)
            
            logger.info(f"Deployment of index has started : {operation}")
            pprint.pprint(vars(operation))

            while True:
                current_deployed_indices = [d.id for d in endpoint.deployed_indexes]

                if deployed_index_id in current_deployed_indices:
                    logger.info(f"✅ Successfully deployed index: {deployed_index_id}")
                    return deployed_index_id

                else:
                    logger.info("Deployment in-progress...")
                    time.sleep(120) ## reduce the time to 2 mins
                
        else:
            logger.info(f"✅ Index already deployed: {deployed_index_id}")
            return deployed_index_id
            
    except Exception as e:
        logger.error(f"❌ Failed to deploy index {deployed_index_id}: {e}")
        logger.exception("Full traceback:")
        return None

def create_vertex_vector_search(index_resource_name: str, endpoint_resource_name: str):
    """
    Create a VertexVectorSearch instance.
    
    Args:
        index_resource_name: Resource name of the index
        endpoint_resource_name: Resource name of the endpoint
        
    Returns:
        VertexVectorSearch: The configured vector search instance
    """
    logger.info(f"Creating VertexVectorSearch with index: {index_resource_name}")
    logger.info(f"  and endpoint: {endpoint_resource_name}")
    
    return rag.VertexVectorSearch(
        index=index_resource_name,
        index_endpoint=endpoint_resource_name
    )