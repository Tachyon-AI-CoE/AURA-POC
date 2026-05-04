# Pure agent logic - no file I/O operations

from google.adk.agents import LlmAgent
from instuctions import get_batch_summary_instructions
import os
from dotenv import load_dotenv
import logging

# Set up logging
load_dotenv()

log_level_str = os.getenv("LOG_LEVEL", "DEBUG").upper()
log_level = getattr(logging, log_level_str, logging.DEBUG)

# Explicitly set the logging level to DEBUG
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Ensure all debug logs are captured in the deployed environment
logger.debug("Debug logging enabled for agent logic.")

def create_summarizer_agent(files_content_map, custom_prompt="", callback_func=None):
    """
    Create a summarizer agent with the provided content and callback
    Pure agent logic - no file I/O operations
    
    Args:
        files_content_map: Dict mapping filename to content
        custom_prompt: Custom summarization instructions
        callback_func: Optional callback function for handling responses
    
    Returns:
        LlmAgent: Configured summarizer agent
    """
    if not files_content_map:
        raise ValueError("files_content_map cannot be empty")
    
    # Generate batch instructions for all files
    combined_instructions = get_batch_summary_instructions(files_content_map, custom_prompt)
    logger.debug(f"Generated batch instructions for {len(files_content_map)} files")

    agent = LlmAgent(
        model='gemini-2.0-flash',
        name='summariser_agent',
        description='Summariser agent that generates summaries based on provided documents or uploaded files.',
        global_instruction=combined_instructions,
        after_model_callback=callback_func
    )

    return agent

