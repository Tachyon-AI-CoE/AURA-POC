"""
Document Processor for Summary Agent
Handles all file I/O operations for the summarization workflow
"""

from google.cloud import storage
import io
from PyPDF2 import PdfReader
import docx
import pandas as pd
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from typing import Optional, Dict
import datetime
import logging
import asyncio

logger = logging.getLogger(__name__)


def extract_text_from_blob(blob):
    """Extract text content from various file types in GCS blob"""
    file_name = blob.name.lower()

    try:
        if file_name.endswith(".pdf"):
            pdf_stream = io.BytesIO(blob.download_as_bytes())
            reader = PdfReader(pdf_stream)
            return "\n".join(page.extract_text() for page in reader.pages if page.extract_text())

        elif file_name.endswith(".docx"):
            doc_stream = io.BytesIO(blob.download_as_bytes())
            document = docx.Document(doc_stream)
            return "\n".join(paragraph.text for paragraph in document.paragraphs)

        elif file_name.endswith(".csv"):
            csv_stream = io.BytesIO(blob.download_as_bytes())
            df = pd.read_csv(csv_stream)
            return df.to_string(index=False)

        else:
            return blob.download_as_text()

    except Exception as e:
        return f"[Error reading {blob.name}: {str(e)}]"


# Removed unnecessary wrapper functions - the original agent did file reading directly


def create_summary_upload_callback(config: dict):
    """Creates a callback function that uploads agent responses to GCS"""
    filename_container = {"filename": None}
    
    def log_response_to_gcs(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[LlmResponse]:
        logger.info(f"[Callback] Invoked for agent: {callback_context.agent_name}")
        logger.debug(f"[Callback] Received LlmResponse: {llm_response}")

        response_text = ""

        if llm_response.content and llm_response.content.parts:
            part = llm_response.content.parts[0]
            if part.text:
                response_text = part.text
            elif part.function_call:
                response_text = f"Function call: {part.function_call.name}"
            else:
                response_text = "Empty response content."
        elif llm_response.error_message:
            response_text = f"Error: {llm_response.error_message}"
        else:
            response_text = "Empty LlmResponse."

        logger.debug(f"[Callback] Response text to upload: {response_text}")

        # --- Upload to GCS ---
        agent_config = config.get("AGENT", {})
        summary_bucket = agent_config.get("SUMMARY_BUCKET")

        if not summary_bucket:
            logger.warning(f"[Callback] No SUMMARY_BUCKET found in config, skipping GCS upload")
            return None

        storage_client = storage.Client()
        bucket = storage_client.bucket(summary_bucket)

        # Try to parse and create separate files for each summary
        if "**SUMMARY FOR" in response_text:
            # Split response into individual file summaries
            sections = response_text.split("**SUMMARY FOR")
            
            for section in sections[1:]:  # Skip the first empty section
                lines = section.strip().split('\n')
                if lines:
                    # Extract filename from the first line
                    filename_line = lines[0].replace(':**', '').replace('[', '').replace(']', '').strip()
                    
                    # Create a clean filename for the summary
                    summary_filename = f"summary_{filename_line}.txt"
                    
                    # Upload this section as a separate file
                    section_content = f"**SUMMARY FOR {section}"
                    blob = bucket.blob(summary_filename)
                    blob.upload_from_string(section_content, content_type="text/plain")
                    
                    filename_container["filename"] = summary_filename  # Store last filename
                    logger.info(f"[Callback] Individual summary saved as {summary_filename}")
        else:
            # Fallback: save as single file if parsing fails
            file_name = f"summary_combined_{datetime.datetime.now().isoformat()}.txt"
            blob = bucket.blob(file_name)
            blob.upload_from_string(response_text, content_type="text/plain")
            filename_container["filename"] = file_name
            logger.info(f"[Callback] Combined summary saved as {file_name}")

        return None

    # Return both the callback function and the filename container
    return log_response_to_gcs, filename_container


# Removed unnecessary wrapper function - original agent handled this directly in create_root_agent()


def create_and_initialize_agent(config=None):
    """Create and initialize the summarizer agent with file processing"""
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'agents', 'summariser_agent'))
    from summarizer_agent import create_summarizer_agent
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Use provided config or default config for deployment
    if config is None:
        config = {
            "STORAGE": {
                "RAG_BUCKETS": {
                    "SOURCE": "source-bucket"
                }
            },
            "AGENT": {
                "SUMMARY_BUCKET": "rag-pipeline-df-audit",
                "custom_summerization_prompt_instructions": "Summarize the content in bullet points."
            }
        }
    
    # Extract source bucket from config
    storage_config = config.get("STORAGE", {})
    buckets = storage_config.get("RAG_BUCKETS", {})
    source_bucket = buckets.get("SOURCE")
    
    if not source_bucket:
        raise ValueError("SOURCE bucket not found in config")
    
    # File processing logic
    client = storage.Client()
    bucket = client.bucket(source_bucket)
    blobs = bucket.list_blobs()
    
    files_content_map = {}
    for blob in blobs:
        content = extract_text_from_blob(blob)
        files_content_map[blob.name] = content
        logger.debug(f"Extracted content from {blob.name}: {len(content)} characters")
    
    logger.debug(f"Total files processed: {len(files_content_map)}")
    
    custom_prompt = config.get("AGENT", {}).get("custom_summerization_prompt_instructions", "")
    
    # Create callback with config
    callback_func, filename_container = create_summary_upload_callback(config)
    
    # Create the agent using pure agent logic
    agent = create_summarizer_agent(files_content_map, custom_prompt, callback_func)
    
    return agent, filename_container


# Execute initialization when module is imported (commented out for direct execution)
# root_agent, filename_container = create_and_initialize_agent()



### to run the agent###############################
async def run_summarizer(config=None):
    """Run the summarizer agent and return responses"""
    # Create agent with provided or default config
    agent, filename_container = create_and_initialize_agent(config)
    
    # Setup session and runner
    user_id = "user_123"
    app_name = "summariser_agent"
    
    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name=app_name, user_id=user_id)
    
    runner = Runner(app_name=app_name, agent=agent, session_service=session_service)
    
    # Run agent with message
    content = types.Content(role="user", parts=[types.Part(text="Summarise the documents")])
    
    responses = []
    async for event in runner.run_async(user_id=user_id, session_id=session.id, new_message=content):
        text = event.content.parts[0].text if event.content and event.content.parts else "[No content]"
        logger.info(f"Agent response: {text}")
        responses.append(text)
    
    return responses, filename_container.get("filename")


# For direct execution
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Run the agent with default config (no need to redefine)
    responses, filename = asyncio.run(run_summarizer())
    print("Responses:", responses)
    print("Summary filename:", filename)
