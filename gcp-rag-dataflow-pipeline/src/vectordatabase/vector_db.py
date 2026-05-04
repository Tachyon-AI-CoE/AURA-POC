import logging
import os
from typing import Dict, Optional, Any
from config import config # This will trigger central logging configuration
from vectordatabase.vectorsearch import deploy_index_if_needed, get_or_create_endpoint, get_or_create_index, create_vertex_vector_search
from vectordatabase.rag_managed_db import create_ann_db,create_knn_db,create_rag_managed_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Here we are initializing the vectordb, it looks at the config which vector db we want create a connection with it and returns an API to use it

def initialize_vector_db(
   rag_pipeline_config: dict
):
    """
    Initializes the vector database by reading db_type and retrieval_strategy
    from VectorDbExtractor. Chooses the correct backend automatically.
    - For vector_search: creates index, endpoint, deploys index, then returns vector search handle
    - For ragmanaged_db: initializes RagManagedDb and creates ANN or KNN db
    
    Args:
        vector_db_config: Vector database configuration dictionary
        index_display_name: Display name for the index
        endpoint_display_name: Display name for the endpoint
        deployed_index_id: ID for the deployed index
        config_instance: Configuration instance (optional)
        
    Returns:
        Initialized vector database object
    """
    try:
        # Use vector_db_config to get the type
        raw_db_type = rag_pipeline_config.get("vector_db_type")
        logger.info(f"🔍 Raw vector_db_type from config: '{raw_db_type}' (type: {type(raw_db_type)})")
        
        if raw_db_type is None or raw_db_type == "":
            raise ValueError(f"Unsupported db_type: '{raw_db_type}' - vector_db_type is missing or empty in config")
        
        db_type = raw_db_type.lower()
        logger.info(f"🚀 Initializing Vector DB with type: {db_type}")

        corpus_name = rag_pipeline_config.get("corpus_name", "default_corpus")
        index_display_name = f"{corpus_name}_index"
        endpoint_display_name = f"{corpus_name}_endpoint"
        deployed_index_id = f"{corpus_name}_deployed_index"
        
        if db_type == "vertexvectorsearch":
            # Get project_id and region from config (added by ConfigurationResolverDoFn from pipeline options)
            project_id = rag_pipeline_config.get("project_id")
            region = rag_pipeline_config.get("region")
            
            logger.info(f"📊 Initializing Vector Search")
            logger.info(f"📍 Using project_id={project_id}, region={region}")
            
            if not project_id:
                raise ValueError("project_id is required in config. Pass --project argument to Dataflow job")
            if not region:
                raise ValueError("region is required in config. Pass --region argument to Dataflow job")
            
            # Create or reuse Index and Endpoint
            logger.info("📊 Creating/getting vector search index...")
            index = get_or_create_index(index_display_name, rag_pipeline_config)

            logger.info("🌐 Creating/getting vector search endpoint...")
            endpoint = get_or_create_endpoint(endpoint_display_name, rag_pipeline_config)
            
            logger.info("🚀 Deploying index to endpoint...")
            deployed_id = deploy_index_if_needed(endpoint, index, deployed_index_id)
            
            if deployed_id:
                # Return a Vertex Vector Search DB only if deployment was successful
                logger.info(f"✅ Vector Search DB initialized successfully with deployed ID: {deployed_id}")
                return create_vertex_vector_search(index.resource_name, endpoint.resource_name)
            else:
                raise Exception(f"Failed to deploy index {deployed_index_id} to endpoint {endpoint_display_name}")

        elif db_type == "ragmanageddb":
            retrieval_strategy = rag_pipeline_config.get("retrieval_strategy")
            # Get project_id and region from config (added by ConfigurationResolverDoFn from pipeline options)
            project_id = rag_pipeline_config.get("project_id")
            region = rag_pipeline_config.get("region")
            
            logger.info(f"📚 Initializing RAG Managed DB with strategy: {retrieval_strategy}")
            logger.info(f"📍 Using project_id={project_id}, region={region}")
            
            if not project_id:
                raise ValueError("project_id is required in config. Pass --project argument to Dataflow job")
            if not region:
                raise ValueError("region is required in config. Pass --region argument to Dataflow job")

            if retrieval_strategy == "ANN":
                # Use config instance if provided, otherwise use defaults
                tree_depth = config.TREE_DEPTH
                leaf_count = config.LEAF_COUNT
                logger.info(f"🌳 Creating ANN DB with tree_depth={tree_depth}, leaf_count={leaf_count}")
                return create_ann_db(tree_depth, leaf_count, project_id, region)

            elif retrieval_strategy == "KNN":
                logger.info("🔍 Creating KNN DB")
                return create_knn_db(project_id, region)
            
            elif retrieval_strategy == "":
                logger.info("🔍 Creating RagManaged DB")
                return create_rag_managed_db(project_id, region)

            else:
                raise ValueError(f"Unsupported retrieval strategy: '{retrieval_strategy}' for rag_managed_db")

        else:
            raise ValueError(f"Unsupported db_type: '{db_type}' - must be 'vector_search' or 'rag_managed_db'")
            
    except Exception as e:
        logger.error(f"❌ Vector DB initialization failed: {e}")
        logger.exception("Full traceback:")
        raise
