import functions_framework
from cloudevents.http import CloudEvent
from google.cloud import storage
import json
import logging
from datetime import datetime
import base64
from flask import make_response
from concurrent.futures import ThreadPoolExecutor
from config.config import load_config
from event_processor.gcs_event_processor import validate_gcs_eventfile
from config.rag_pipeline_config import get_flattened_rag_pipeline_config
from utils.rag_pipeline_utils import convert_string_to_json
from rag.rag_pipeline import run_pipeline

# Get log level from config system
from config import config
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a ThreadPoolExecutor for background tasks
executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="rag-pipeline")

load_config()

# Function to handle CloudEvents from Cloud Storage or Pub/Sub Topic
@functions_framework.cloud_event
def rag_pipeline_handler(cloud_event: CloudEvent):
    logger.info("Rag Pipeline triggered")
    try:
        # Decode the raw event data if it's in bytes
        raw_data = cloud_event.data
        logger.info(f"Rag Pipeline triggered at {datetime.now()}")
        if isinstance(raw_data, bytes):
            logger.info(f"raw_data got from pubsub cloud event: {raw_data}")
            raw_data = json.loads(raw_data.decode("utf-8"))
            
        data = raw_data
        event_type = None
        eventfile_name = None
        # Check if it's a Cloud Storage event
        if "bucket" in data and "name" in data:
            logger.info(f"Event data got from cloud storage event at {datetime.now()}: {data}")
            bucket_name = data.get("bucket")
            eventfile_name = data.get("name")
            event_type = "GCS_EVENT"

            if not bucket_name or not eventfile_name:
                logger.error("Missing bucket or eventfile_name in Cloud Storage event")
                return make_response("Missing bucket or eventfile_name", 400)            # Process Cloud Storage event
            storage_client = storage.Client()
            
            rag_pipeline_config = validate_gcs_eventfile(bucket_name, eventfile_name, storage_client)
            rag_pipeline_config["event_type"] = event_type
            rag_pipeline_config["event_file_name"] = eventfile_name
            rag_pipeline_config["event_bucket_name"] = bucket_name

            # Submit to background thread
            future = executor.submit(run_pipeline, rag_pipeline_config, storage_client=storage_client)
            logger.info(f"Task submitted to background thread")
            
            logger.info(f"Cloud Storage event processed at {datetime.now()}")
            
            # Test: Create response object
            response = make_response("Cloud Storage event processed", 200)
            logger.info(f"✅ Response object created: {vars(response)}")
            logger.info(f"🚀 About to return response at {datetime.now()}")
            
            return response

        # Check if it's a Pub/Sub event
        elif "message" in data:
            logger.info(f"Event data got from pubsub cloud event at {datetime.now()}: {data}")
            pubsub_message = data.get("message", {})
            message_data = pubsub_message.get("data")
            event_type = "PUBSUB_EVENT"

            if not message_data:
                logger.error("Missing message data in Pub/Sub event")
                return make_response("Missing message data", 400)

            storage_client = storage.Client()

            # Decode and parse the Pub/Sub message
            decoded_data = base64.b64decode(message_data).decode("utf-8")
            rag_event_config = convert_string_to_json(decoded_data)
            rag_pipeline_config = get_flattened_rag_pipeline_config(rag_event_config, storage_client=storage_client)
            rag_pipeline_config["event_type"] = event_type

            logger.info(f"Received config from Pub/Sub: {rag_event_config}")

            # Submit to background thread
            future = executor.submit(run_pipeline, rag_pipeline_config, storage_client=storage_client)
            logger.info(f"Pub/Sub event processed at {datetime.now()}: Document processing submitted to thread pool")

            return make_response("Pub/Sub event processing started", 200)

        else:
            logger.error("Unknown event type")
            return make_response("Unknown event type", 400)  

    except Exception as e:
        logger.exception("CloudEvent handler failed")
        logger.error(f"Error is {e}")
        return make_response("Internal server error", 500)