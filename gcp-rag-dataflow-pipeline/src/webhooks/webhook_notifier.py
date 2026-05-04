"""Simple webhook sender for RAG corpus status updates via REST API."""

import requests
import logging
import os
import json
import urllib3

from google.auth.transport.requests import Request
from google.oauth2 import id_token

def _get_id_token(target_audience: str) -> str:
    """Get ID token for authenticating with Cloud Run services."""
    try:
        # Get the default credentials and generate an ID token
        auth_req = Request()
        token = id_token.fetch_id_token(auth_req, target_audience)
        return token
    except Exception as e:
        logger.warning(f"Failed to fetch ID token: {e}. Proceeding without authentication.")
        return None

# Disable SSL warnings when using verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


def send_rag_status(corpus_name, status, error_message=None, webhook_url=None, corpus_resource_name=None, project_id=None, region=None, cloudrun_service_url=None):
    """
    Send RAG corpus status to webhook endpoint via REST API.
    
    Args:
        corpus_name: Name of the corpus (used as dataset_name in request body)
        status: 'Ready' (success) or 'Failed' (failure)
        error_message: Error details if status is 'Failed'
        webhook_url: Optional webhook URL (can also be set via DATA_APP_API_URL env var)
        corpus_resource_name: RAG corpus resource name (e.g., projects/<PROJECT_ID>/locations/us-east4/ragCorpora/123...)
        project_id: GCP project ID (optional, used for constructing console URL)
        region: GCP region (optional, used for constructing console URL)
    
    Returns:
        dict: Response from the webhook endpoint or None if webhook URL not provided
    """
    
    # Skip webhook call if no URL provided
    if not webhook_url:
        logger.info(f"[WEBHOOK] Skipping webhook notification - no webhook URL provided")
        return None
    
    # Construct full URL with the update endpoint path
    full_url = f"{webhook_url}"
    
    # Construct query parameters (dataset_name must be in URL query string)
    query_params = {
        "dataset_name": corpus_name
    }
    
    # Construct request body (status and vectorizedDatasetBasedId only)
    payload = {
        "status": status
    }
    
    # Add corpus resource name if available (will be None for early failures before corpus creation)
    if corpus_resource_name:
        payload["vectorizedDatasetBaseId"] = corpus_resource_name
        
        # Construct Vertex AI console URL for the corpus
        # corpus_resource_name format: projects/{PROJECT}/locations/{REGION}/ragCorpora/{CORPUS_ID}
        # Extract corpus ID from resource name
        try:
            corpus_id = corpus_resource_name.split('/')[-1]  # Get last part (corpus ID)
            
            # Extract project and region from resource name if not provided
            if not project_id or not region:
                parts = corpus_resource_name.split('/')
                extracted_project = parts[1] if len(parts) > 1 else None
                extracted_region = parts[3] if len(parts) > 3 else None
                project_id = project_id or extracted_project
                region = region or extracted_region
            
            # Construct console URL
            if project_id and region and corpus_id:
                console_url = (
                    f"https://console.cloud.google.com/vertex-ai/rag/locations/{region}/"
                    f"corpus/{corpus_id}/data?authuser=1&hl=en&project={project_id}"
                )
                payload["vectorizedDatasetUrl"] = console_url
                logger.info(f"[WEBHOOK] Constructed corpus URL: {console_url}")
            else:
                logger.warning(f"[WEBHOOK] Could not construct corpus URL - missing project_id or region")
        except Exception as e:
            logger.warning(f"[WEBHOOK] Failed to construct corpus URL: {e}")
    
    # Optionally add error message to payload if provided (for failure cases)
    if error_message:
        payload["error_message"] = error_message
    
    try:
        logger.info(f"[WEBHOOK] Making PUT request to: {full_url}")
        logger.info(f"[WEBHOOK] Query parameters: {query_params}")
        logger.info(f"[WEBHOOK] Request data: {payload}")
        
        # Send PUT request (matching reference implementation)

        headers = {"Content-Type": "application/json"}
        # Add authentication token for Cloud Run services
        # Use the actual Cloud Run service URL for token audience (required for authentication)
        # even when making requests through internal load balancer
        token = _get_id_token(cloudrun_service_url)
        if token:
            headers["Authorization"] = f"Bearer {token}"
            logger.info("Added ID token for Cloud Run authentication")

        response = requests.put(
            full_url,
            params=query_params,
            json=payload,
            headers=headers,
            timeout=30,
        )
        
        logger.info(f"[WEBHOOK] Response status code: {response.status_code}")
        logger.info(f"[WEBHOOK] Response headers: {dict(response.headers)}")
        
        # Log response content for debugging
        try:
            response_content = response.json()
            logger.info(f"[WEBHOOK] Response content: {json.dumps(response_content, indent=2)}")
        except Exception:
            logger.info(f"[WEBHOOK] Response text: {response.text}")
        
        # Raise exception if request failed (4xx or 5xx status codes)
        response.raise_for_status()
        
        return {"status": "success", "response": response.json()}
        
    except requests.exceptions.HTTPError as e:
        # HTTP error (4xx, 5xx) - log response details
        logger.error(f"[WEBHOOK] HTTP error {response.status_code}: {e}")
        logger.error(f"[WEBHOOK] Response body: {response.text}")
        return {"status": "error", "error": f"HTTP {response.status_code}: {response.text}"}
        
    except requests.exceptions.RequestException as e:
        logger.error(f"[WEBHOOK] Request failed: {e}")
        return {"status": "error", "error": str(e)}
    except Exception as e:
        logger.error(f"[WEBHOOK] Unexpected error: {e}")
        return {"status": "error", "error": str(e)}
