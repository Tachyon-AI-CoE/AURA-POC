"""Eventarc trigger creation for Cloud Storage events."""

from google.cloud import eventarc_v1
from google.api_core import exceptions
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_eventarc_trigger(
    trigger_name: str,
    bucket_name: str,
    project_id: str,
    location: str,
    cloud_run_service: str,
    event_arc_service_account: str
) -> dict:
    """Create an Eventarc trigger for Cloud Storage finalized events.
    
    Args:
        trigger_name: Name of the Eventarc trigger to create
        bucket_name: GCS bucket to monitor for events
        project_id: GCP project ID (from runtime --project parameter)
        location: GCP region (from runtime --region parameter)
        cloud_run_service: Cloud Run service name for trigger destination (from runtime parameters)
        event_arc_service_account: Service account email for Eventarc trigger (from runtime parameters)
    """
    
    try:
        client = eventarc_v1.EventarcClient()
        parent = f"projects/{project_id}/locations/{location}"
        
        trigger = eventarc_v1.Trigger(
            name=f"{parent}/triggers/{trigger_name}",
            event_filters=[
                eventarc_v1.EventFilter(
                    attribute="type",
                    value="google.cloud.storage.object.v1.finalized"
                ),
                eventarc_v1.EventFilter(
                    attribute="bucket",
                    value=bucket_name
                )
            ],
            destination=eventarc_v1.Destination(
                cloud_run=eventarc_v1.CloudRun(
                    service=cloud_run_service,
                    region=location
                )
            ),
            service_account=event_arc_service_account
        )
        
        logger.info(f"Creating Eventarc trigger: {trigger_name}")
        operation = client.create_trigger(parent=parent, trigger=trigger, trigger_id=trigger_name)
        result = operation.result()
        logger.info(f"Successfully created trigger: {trigger_name}")
        
        return {
            "status": "success",
            "trigger_name": trigger_name,
            "trigger_resource_name": result.name
        }
        
    except exceptions.AlreadyExists:
        logger.warning(f"Trigger {trigger_name} already exists")
        return {"status": "warning", "trigger_name": trigger_name}
        
    except Exception as e:
        logger.error(f"Failed to create trigger {trigger_name}: {e}")
        return {"status": "error", "error": str(e)}

