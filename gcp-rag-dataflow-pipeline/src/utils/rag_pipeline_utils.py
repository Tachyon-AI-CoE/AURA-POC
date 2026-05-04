import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def convert_blob_to_json(blob):
    """
    Convert a Google Cloud Storage Blob to a JSON object.
    
    Args:
        blob (google.cloud.storage.blob.Blob): The GCS Blob to convert.
        
    Returns:
        dict: The JSON object representation of the blob's content.
    """
    content = blob.download_as_text()
    return json.loads(content)

def convert_string_to_json(json_string):
    """
    Convert a JSON string to a JSON object.
    
    Args:
        json_string (str): The JSON string to convert.
        
    Returns:
        dict: The JSON object representation of the string.
    """
    return json.loads(json_string)