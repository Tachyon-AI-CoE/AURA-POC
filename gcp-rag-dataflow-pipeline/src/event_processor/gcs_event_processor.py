from config import config
import logging
import json
import re
from datetime import datetime
import traceback
from apache_beam.io.filesystems import FileSystems

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def write_failure_audit(config, status_name, error):
    """
    Helper function to write audit for failures. Called from all DoFn exception handlers.
    
    Args:
        config: Pipeline configuration dictionary
        status_name: Status name for audit (e.g., 'vector_db_initialization_failed')
        error: The exception object
    """
    try:
        config['error'] = str(error)
        write_rag_audit(config, status_name, str(error))
    except Exception as audit_error:
        logging.warning(f"[RAG] Failed to write audit for {status_name}: {audit_error}")
    
    # Send failure webhook notification (inline)
    try:
        from webhooks.webhook_notifier import send_rag_status
        webhook_url = config.get('status_webhook_url')
        
        logging.info(f"[RAG] Attempting failure webhook notification for {status_name}")
        logging.info(f"[RAG] Webhook URL present: {webhook_url is not None}")
        
        if webhook_url:
            logging.info(f"[RAG] Sending failure webhook to: {webhook_url}")
            
            corpus_resource_name = None
            corpus_instance = config.get('rag_corpus_instance')
            if corpus_instance and hasattr(corpus_instance, 'name'):
                corpus_resource_name = corpus_instance.name
            
            # Log config contents for debugging (excluding non-serializable objects)
            try:
                config_for_logging = {k: v for k, v in config.items() if not k.endswith('_instance')}
                logging.info(f"[RAG] Config contents for webhook: {json.dumps(config_for_logging, default=str)}")
            except Exception as log_ex:
                logging.warning(f"[RAG] Could not serialize config for logging: {log_ex}")
            
            webhook_result = send_rag_status(
                corpus_name=config.get('corpus_name', 'unknown'),
                status='Failed',
                error_message=f"{status_name}: {str(error)}",
                webhook_url=webhook_url,
                corpus_resource_name=corpus_resource_name,
                project_id=config.get('project_id'),
                region=config.get('region')
            )
            
            if webhook_result and webhook_result.get('status') == 'success':
                logging.info(f"[RAG] Failure webhook sent successfully")
            elif webhook_result:
                logging.warning(f"[RAG] Failure webhook failed: {webhook_result.get('error')}")
        else:
            logging.info(f"[RAG] No webhook URL configured - skipping failure notification")
    except Exception as e:
        logging.error(f"[RAG] Failed to send failure webhook: {e}")
        logging.error(f"[RAG] Webhook exception details: {traceback.format_exc()}")


def write_rag_audit(pipeline_config, status, error=None):
    """
    Write RAG pipeline audit record to GCS.
    
    Args:
        pipeline_config: Pipeline configuration dictionary
        status: Status string (e.g., 'completed', 'failed', 'pipeline_execution_completed')
        error: Optional error message
    """
    # Extract message FIRST (before creating serializable_config to avoid duplication)
    corpus_name = pipeline_config.get('corpus_name', 'unknown')
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        
    # Extract only JSON-serializable values from config
    serializable_config = {}
    for key, value in pipeline_config.items():
        # Skip internal objects, non-serializable items, message, and error (to avoid duplication)
        if key.startswith('_') or key.endswith('_instance') or key in ('message', 'error'):
            continue
        # Only include basic types (str, int, float, bool, None, list, dict)
        if isinstance(value, (str, int, float, bool, type(None), list, dict)):
            serializable_config[key] = value
        else:
            # For objects, try to get a string representation
            try:
                serializable_config[key] = str(value.name) if hasattr(value, 'name') else str(type(value).__name__)
            except:
                serializable_config[key] = str(type(value).__name__)
    
    # Create audit record with proper order: corpus_name, status, message, timestamp, pipeline_config
    record = {
        'corpus_name': corpus_name,
        'status': status
    } 
    if error:
        record['error'] = str(error)
    
    # Add optional message field
    if pipeline_config.get('message'):
        record['message'] = pipeline_config['message']
    
    # Add timestamp
    record['timestamp'] = timestamp
    
    # Add pipeline config last
    record['pipeline_config'] = serializable_config
   
    # Always log locally first (guaranteed to work)
    logger.info(f"AUDIT RECORD - Status: {status}, Corpus: {corpus_name}, Time: {timestamp}")
    if error:
        logger.error(f"AUDIT ERROR DETAILS: {error}")
   
    try:
        # Get bucket from pipeline config (REQUIRED - no fallback)
        audit_bucket = pipeline_config.get("audit_bucket")
        
        if not audit_bucket:
            logger.error("audit_bucket not found in config. Pass --audit_bucket argument to Dataflow job")
            return
        
        logger.info(f"Using audit bucket: {audit_bucket}")
       
        # Determine status prefix (success or failure)
        status_prefix = "success" if "completed" in status.lower() else "failure"
        
        # Create file path: corpus_name/success_corpusname.json
        blob_path = f"{corpus_name}/{status_prefix}_{corpus_name}.json"
        audit_path = f"gs://{audit_bucket}/{blob_path}"
 
        logger.info(f"Writing audit to: {audit_path}")
 
        # Write to GCS using FileSystems
        with FileSystems.create(audit_path) as f:
            f.write(json.dumps(record, indent=2).encode('utf-8'))
       
        logger.info(f"Audit saved successfully: {audit_path}")
       
    except Exception as e:
        # If GCS audit fails for any reason, continue with local logging only
        logger.warning(f"GCS audit failed ({type(e).__name__}: {e}), continuing with local audit only")
        # Don't re-raise - pipeline should continue even if audit fails



def archive_config_file(pipeline_config):
    """
    Archive (delete) the config file from source bucket after successful corpus creation.
    Uses Apache Beam's FileSystems for better Dataflow integration and automatic retries.
    
    Args:
        pipeline_config: Pipeline configuration dictionary containing '_config_file' path
        
    Returns:
        dict: Status of the archival operation
    """
    try:
        from apache_beam.io.filesystems import FileSystems
        
        config_file = pipeline_config.get('_config_file')
        
        if not config_file or not config_file.startswith('gs://'):
            logger.warning(f"Invalid or missing config file path: {config_file}. Skipping archival.")
            return {"status": "skipped"}
        
        logger.info(f"Archiving config file: {config_file}")
        
        # Delete the file using Beam's FileSystems for better Dataflow integration
        FileSystems.delete([config_file])
        
        logger.info(f"Successfully archived config file: {config_file}")
        return {"status": "archived", "config_file": config_file}
            
    except Exception as e:
        logger.warning(f"Failed to archive config file: {e}")
        return {"status": "failed", "error": str(e)}
