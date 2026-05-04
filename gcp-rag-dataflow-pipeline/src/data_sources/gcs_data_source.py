"""
Google Cloud Storage data source implementation for RAG pipeline.
"""

from vertexai import rag
from typing import Any, Dict
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# incoming array --> string , iterate the array each index would be a string now (file name)

def get_source_path(source_identifier: str, filename: str = None) -> str:
    """
    Get the GCS source path.
    
    Args:
        source_identifier: GCS bucket name
        filename: File name in the bucket
        
    Returns:
        str: GCS path in format gs://bucket/filename
    """
    if filename:
        return f"gs://{source_identifier}/{filename}" ###here 
    else:
        return f"gs://{source_identifier}"



def validate_config(rag_pipeline_config: dict) -> bool:
    """
    Validate GCS configuration.
    
    Returns:
        bool: True if configuration is valid
    """
    if not rag_pipeline_config.get("staging_bucket"):
        logger.error("GCS data source requires 'staging_bucket' in configuration")
        return False
    logger.info(f"GCS configuration valid. staging_bucket: '{rag_pipeline_config['staging_bucket']}'")
    return True