"""
JIRA data source implementation for RAG pipeline.
"""

from typing import Any
import logging
from vertexai import rag

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_jira_rag_source(rag_pipeline_config) -> Any:
    """
    Import data from JIRA to RAG corpus.
    
    Args:
        rag_corpus: The RAG corpus object
        source_identifier: JIRA source identifier (not a file path)
        result_gcs_path: GCS path for storing import results
        
    Returns:
        Import response (placeholder for now)
    """

    logger.info("Creating the JIRA source for import")

    is_valid = validate_config(rag_pipeline_config)
    if not is_valid:
        raise ValueError("Invalid JIRA configuration")
    

    jira_query = rag.JiraQuery(
    email=rag_pipeline_config.get('jira_email', ''),
    jira_projects=rag_pipeline_config.get('jira_projects', []),
    custom_queries=rag_pipeline_config.get('jira_custom_query', []),
    api_key=rag_pipeline_config.get('jira_api_secret_key', ''),
    server_uri=rag_pipeline_config.get('jira_server_uri', '')
)
    
    
    
    jira_source = rag.JiraSource(
    queries=[jira_query],
)

    return jira_source



    

def validate_config(rag_pipeline_config) -> bool:
    """
    Validate JIRA configuration.
    
    Returns:
        bool: True if configuration is valid
    """
    missing_fields = []

    if not rag_pipeline_config.get('jira_server_uri'):
        missing_fields.append('server_uri')
    if not rag_pipeline_config.get('jira_email'):
        missing_fields.append('email')
    if not rag_pipeline_config.get('jira_api_secret_key'):
        missing_fields.append('api_secret_key')
    if not rag_pipeline_config.get('jira_projects') and not rag_pipeline_config.get('jira_custom_query'):
        missing_fields.append('jira_projects or custom_query')
        
    if missing_fields:
        logger.error(f"JIRA data source missing one or more required fields")
        return False
        
    return True
