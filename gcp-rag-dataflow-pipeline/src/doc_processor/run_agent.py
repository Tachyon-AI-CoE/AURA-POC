
# ETLpipeline (extract config from pub sub, transform--> core logic what should we done(whole code create corpus),loading --> create archive file for us)
#dataflow--> we sync the data pipeline whenever there is msg 


#method process summary to call agent --> create summary--> return the agent output


#creating the bucket , logging back of the summary agent logic should be impl here

import os
import json
import asyncio
from dotenv import load_dotenv
from doc_processor.summary_document_processor import create_and_initialize_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import logging
import warnings

# Set up logging
load_dotenv()

log_level_str = os.getenv("LOG_LEVEL", "DEBUG").upper()
log_level = getattr(logging, log_level_str, logging.DEBUG)

logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

warnings.filterwarnings("ignore", message='Field name "config_type" in "SequentialAgent" shadows an attribute in parent "BaseAgent"')

async def run_agent(config: dict):
    # Use the refactored function to create the agent
    root_agent, filename_container = create_and_initialize_agent(config)
    
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="summariser_agent",
        user_id="user_123"
    )
    
    # CHANGE: No need to iterate - just run the single agent
    runner = Runner(
        app_name="summariser_agent",
        agent=root_agent,
        session_service=session_service
    )
    
    content = types.Content(
        role="user",
        parts=[types.Part(text="Summarise the documents")]
    )
    
    responses = []
    async for event in runner.run_async(
        user_id="user_123",
        session_id=session.id,
        new_message=content
    ):
        text = event.content.parts[0].text if event.content and event.content.parts else "[No content]"
        logger.info(f"Agent response: {text}")
        responses.append(text)
    
    # CHANGE: Get the filename(s) from the container after execution
    filenames = filename_container.get("filenames", [])
    return responses, filenames

async def trigger_agent(config: dict):
    return await run_agent(config)

if __name__ == "__main__":
    # Example configuration dictionary
    config = {
        "STORAGE": {
            "RAG_BUCKETS": {
                "SOURCE": "process-bucket"
            }
        },
        "AGENT": {
            "SUMMARY_BUCKET": "summarised-bucket",
            "custom_summerization_prompt_instructions": "give the answer only in bulletin points"
        }
    }

    # Call the trigger_agent function using asyncio.run
    responses, filename = asyncio.run(trigger_agent(config))
    print("Responses:", responses)
    print("Summary filename:", filename)

