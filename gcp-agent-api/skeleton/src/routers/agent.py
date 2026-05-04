from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from dotenv import load_dotenv
import json
import vertexai
import os
from utils.log_helper import setup_logging

# Arize imports
from google.cloud import secretmanager
from arize.otel import register
from opentelemetry import trace
from openinference.instrumentation.vertexai import VertexAIInstrumentor

logger = setup_logging()

def get_env_variable(var_name, default=None):
    """Retrieve the environment variable or return an exception."""
    value = os.getenv(var_name, default)
    if value is None:
        raise EnvironmentError(f"Set the {var_name} environment variable.")
    if not value:
        raise ValueError(f"Environment variable {var_name} is empty")
    return value

def validate_env_variable(var_value, var_name):
    """Validate the environment variable to ensure it's not empty."""
    if not var_value:
        raise ValueError(f"Value for {var_name} cannot be empty")
    return var_value

project_id = validate_env_variable(get_env_variable("PROJECT_ID"), "PROJECT_ID")
location = validate_env_variable(get_env_variable("LOCATION"), "LOCATION")  
  
# ========================== Arize Integration Setup ==========================

# Get tracer at module level for use with decorators
tracer = trace.get_tracer(__name__)

def initialize_arize_secrets():
    """
    Initialize GCP Secret Manager client and retrieve Arize secrets.
    This function retrieves ARIZE_API_KEY and ARIZE_SPACE_ID from Secret Manager.
    """
    try:
        gcp_secret_manager_project = os.getenv("PROJECT_NUMBER")
        api_key_secret_name = os.getenv("ARIZE_API_KEY")
        space_id_secret_name = os.getenv("ARIZE_SPACE_ID")
        
        # Create a SecretManager client
        client = secretmanager.SecretManagerServiceClient()
        
        # Retrieve ARIZE_API_KEY
        if not os.getenv("ARIZE_API_KEY_VALUE"):
            try:
                api_key_path = f"projects/{gcp_secret_manager_project}/secrets/{api_key_secret_name}/versions/latest"
                response = client.access_secret_version(request={"name": api_key_path})
                arize_api_key = response.payload.data.decode("UTF-8")
                os.environ["ARIZE_API_KEY_VALUE"] = arize_api_key
                logger.info(f"✅ ARIZE_API_KEY retrieved from Secret Manager")
            except Exception as e:
                logger.warning(f"⚠️  Failed to retrieve ARIZE_API_KEY from Secret Manager: {e}")
        else:
            logger.info(f"ℹ️  ARIZE_API_KEY already set in environment")
        
        # Retrieve ARIZE_SPACE_ID
        if not os.getenv("ARIZE_SPACE_ID_VALUE"):
            try:
                space_id_path = f"projects/{gcp_secret_manager_project}/secrets/{space_id_secret_name}/versions/latest"
                response = client.access_secret_version(request={"name": space_id_path})
                arize_space_id = response.payload.data.decode("UTF-8")
                os.environ["ARIZE_SPACE_ID_VALUE"] = arize_space_id
                logger.info(f"✅ ARIZE_SPACE_ID retrieved from Secret Manager")
            except Exception as e:
                logger.warning(f"⚠️  Failed to retrieve ARIZE_SPACE_ID from Secret Manager: {e}")
        else:
            logger.info(f"ℹ️  ARIZE_SPACE_ID already set in environment")
    except Exception as e:
        logger.warning(f"⚠️  Arize secret initialization failed (tracing may be disabled): {e}")


def initialize_arize_tracing(project_name: Optional[str] = None):
    """
    Initialize Arize tracing with Vertex AI instrumentation.
    This enables automatic trace collection and sending to Arize Phoenix.
    """
    try:
        # Read from the _VALUE variables that were set by initialize_arize_secrets()
        arize_api_key = os.getenv("ARIZE_API_KEY_VALUE")
        arize_space_id = os.getenv("ARIZE_SPACE_ID_VALUE")
        
        if not arize_api_key or not arize_space_id:
            logger.warning("⚠️  ARIZE_API_KEY_VALUE or ARIZE_SPACE_ID_VALUE not set. Tracing disabled.")
            return None
        
        # Default project name based on agent ID or generic name
        if not project_name:
            project_name = os.getenv("ARIZE_PROJECT_NAME")
        
        logger.info(f"Initializing Arize tracing for project: {project_name}")
        
        # Enable GCP tracing environment variables
        os.environ["GCP_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED"] = "true"
        os.environ["GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY"] = "true"
        os.environ["GCP_TRACING_GEN_AI_CAPTURE_MESSAGE_CONTENT"] = "true"
        os.environ["GCP_TRACING_GEN_AI_INCLUDE_BINARY_DATA"] = "true"
        
        # Register with Arize
        tracer_provider = register(
            space_id=arize_space_id,
            api_key=arize_api_key,
            project_name=project_name,
            set_global_tracer_provider=True,
        )
        
        # Instrument Vertex AI before creating clients
        VertexAIInstrumentor().instrument(tracer_provider=tracer_provider)
        
        logger.info("✅ Arize tracing initialized successfully")
        return tracer_provider
    except Exception as e:
        logger.warning(f"⚠️  Failed to initialize Arize tracing: {e}")
        return None


# Initialize Arize integration at module load time
try:
    initialize_arize_secrets()
    arize_tracer_provider = None
except Exception as e:
    logger.warning(f"⚠️  Arize integration initialization failed: {e}")
    arize_tracer_provider = None

vertexai.init(
    project=project_id,
    location=location
)
from vertexai import agent_engines

# Create FastAPI router
router = APIRouter()

def flush_arize_traces():
    """Flush Arize traces before shutdown (best effort)."""
    if arize_tracer_provider:
        for method_name in ("force_flush", "shutdown", "close"):
            method = getattr(arize_tracer_provider, method_name, None)
            if callable(method):
                try:
                    method()
                    logger.info(f"✅ Arize traces flushed via {method_name}()")
                    break
                except Exception as e:
                    logger.warning(f"⚠️  Failed to flush traces via {method_name}(): {e}")

class StreamQueryRequest(BaseModel):
    user_input: str = Field(alias="userInput")
    agent_id: str = Field(alias="agentId")
    user_id: str = Field(alias="userId")
    agent_display_name: str = Field(alias="agentDisplayName")
    agent_version: str = Field(alias="agentVersion")
    session_id: Optional[str] = Field(None, alias="sessionId")
    model_config = {"populate_by_name": True}
    
class StreamQueryResponse(BaseModel):
    response: str
    status: str


async def invoke_agent(userInput:str, agentId:str, userId: str, sessionId: str) -> str:
    """
    Invoke the multi-agent system with user input and agent ID.
    Wrapped with Arize tracing for observability.
    """
    try:
        # Start a trace span for the agent conversation
        with tracer.start_as_current_span("agent-conversation") as root_span:
            # Set span attributes for better observability
            root_span.set_attribute("input.value", userInput)
            root_span.set_attribute("input.mime_type", "text/plain")
            root_span.set_attribute("agent.id", agentId)
            root_span.set_attribute("user.id", userId)
            if sessionId:
                root_span.set_attribute("session.id", sessionId)
            
            agent_engine = agent_engines.get(agentId)
            
            if isinstance(agent_engine, agent_engines.AsyncQueryable) or isinstance(agent_engine, agent_engines.AsyncStreamQueryable):
                logger.info(f"Using async streaming query for agent {agentId}")
                curr_response = {}
                async for event in agent_engine.async_stream_query(user_id=userId, session_id=sessionId, message=userInput):
                    curr_response = event
                    logger.debug(f"Received a response chunk")
                
                # Set output span attributes
                root_span.set_attribute("output.value", json.dumps(curr_response))
                root_span.set_attribute("output.mime_type", "application/json")
                
                return curr_response  # this will be the last response (required for multi-agent transfer handling)

            elif isinstance(agent_engine, agent_engines.Queryable):
                logger.info(f"Using sync query for agent {agentId}")
                response = agent_engine.query(input=userInput, max_turns=2)
                
                # Set output span attributes
                root_span.set_attribute("output.value", json.dumps(response))
                root_span.set_attribute("output.mime_type", "application/json")
                
                return response
            else:
                error_msg = f"Agent engine type not supported for agent {agentId}"
                logger.error(error_msg)
                return f"Error: {error_msg}"
    except Exception as e:
        logger.error(f"Error during agent invocation: {e}")
        # Set error attributes on span
        if tracer:
            with tracer.start_as_current_span("agent-error") as error_span:
                error_span.set_attribute("error", True)
                error_span.set_attribute("error.message", str(e))
        return f"Error: {str(e)}"

@router.post("/invoke-agent", response_model=StreamQueryResponse)
async def invoke_agent_endpoint(request: StreamQueryRequest):
    """
    Invoke the multi-agent system with user input
    """
    global arize_tracer_provider
    try:
        if not request.user_input.strip():
            raise HTTPException(status_code=400, detail="User input cannot be empty")
        os.environ["ARIZE_PROJECT_NAME"] = f"{request.agent_display_name}_{request.agent_version}_TracingProject"
        # Initialize tracing and update the global tracer provider
        arize_tracer_provider = initialize_arize_tracing()
        # Call the invoke_agent function with the user input from request
        response = await invoke_agent(request.user_input, request.agent_id, request.user_id, request.session_id)

        return StreamQueryResponse(
            response=json.dumps(response),
            status="success"
        )
    except HTTPException:
        # Re-raise HTTP exceptions as they are
        raise
    except Exception as e:
        logger.error(f"Error in invoke_agent_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
@router.post("/stream-query", response_model=StreamQueryResponse)
async def stream_query_endpoint(request: StreamQueryRequest):
    """
    Invoke the multi-agent system with user input
    """
    try:
        if not request.user_input.strip():
            raise HTTPException(status_code=400, detail="User input cannot be empty")
        
        # Call the invoke_agent function with the user input from request
        response = await invoke_agent(request.user_input, request.agent_id, request.user_id, request.session_id)

        return StreamQueryResponse(
            response=json.dumps(response),
            status="success"
        )
    except HTTPException:
        # Re-raise HTTP exceptions as they are
        raise
    except Exception as e:
        logger.error(f"Error in stream_query_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


class CreateSessionRequest(BaseModel):
    user_id: str = Field(alias="userId")
    agent_id: str = Field(alias="agentId")
    model_config = {"populate_by_name": True}
    
class CreateSessionResponse(BaseModel):
    response: str
    status: str


async def create_session(userInput:str, agentId:str) -> str:
    """
    Invoke the multi-agent system with user input and agent ID
    """
    try:
        
        agent_engine=agent_engines.get(agentId)
        async for event in agent_engine.async_create_session(
            user_id="u_123",
        ):
            return event
    except Exception as e:
        logger.error(f"Error during create_session invocation: {e}")
        return f"Error: {str(e)}"

@router.post("/create-session", response_model=CreateSessionResponse)
async def create_session_endpoint(request: CreateSessionRequest):
    """
    Invoke the create-session with user id
    """
    try:
        if not request.user_id.strip():
            raise HTTPException(status_code=400, detail="User id cannot be empty")
        
        # Call the invoke_agent function with the user input from request
        response = await create_session(request.user_id, request.agent_id)

        return CreateSessionResponse(
            response=json.dumps(response),
            status="success"
        )
    except HTTPException:
        # Re-raise HTTP exceptions as they are
        raise
    except Exception as e:
        logger.error(f"Error in create_session_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


class ListSessionsRequest(BaseModel):
    user_id: str = Field(alias="userId")
    agent_id: str = Field(alias="agentId")
    model_config = {"populate_by_name": True}
    
class ListSessionsResponse(BaseModel):
    response: str
    status: str


async def list_sessions(userId:str, agentId:str) -> str:
    """
    List Sessions
    """
    try:
        
        agent_engine=agent_engines.get(agentId)
        async for event in agent_engine.async_list_sessions(
            user_id=userId,
        ):
            return event
    except Exception as e:
        logger.error(f"Error during list_sessions invocation: {e}")
        return f"Error: {str(e)}"

@router.get("/list-sessions", response_model=ListSessionsResponse)
async def list_sessions_endpoint(request: ListSessionsRequest):
    """
    Invoke the list_sessions with user id
    """
    try:
        if not request.user_id.strip():
            raise HTTPException(status_code=400, detail="User id cannot be empty")
        
        # Call the invoke_agent function with the user input from request
        response = await list_sessions(request.user_id, request.agent_id)

        return ListSessionsResponse(
            response=json.dumps(response),
            status="success"
        )
    except HTTPException:
        # Re-raise HTTP exceptions as they are
        raise
    except Exception as e:
        logger.error(f"Error in list_sessions_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


class GetSessionRequest(BaseModel):
    user_id: str = Field(alias="userId")
    session_id: str = Field(alias="sessionId")
    agent_id: str = Field(alias="agentId")
    model_config = {"populate_by_name": True}
    
class GetSessionResponse(BaseModel):
    response: str
    status: str


async def get_session(userId:str, sessionId:str, agentId:str) -> str:
    """
    Get Session
    """
    try:
        
        agent_engine=agent_engines.get(agentId)
        async for event in agent_engine.async_get_session(
            user_id=userId,
            session_id=sessionId,
        ):
            return event
    except Exception as e:
        logger.error(f"Error during get_session invocation: {e}")
        return f"Error: {str(e)}"

@router.get("/get-session", response_model=GetSessionResponse)
async def get_session_endpoint(request: GetSessionRequest):
    """
    Invoke the get_session with user id
    """
    try:
        if not request.user_id.strip():
            raise HTTPException(status_code=400, detail="User id cannot be empty")
        if not request.session_id.strip():
            raise HTTPException(status_code=400, detail="Session id cannot be empty")
        # Call the invoke_agent function with the user input from request
        response = await get_session(request.user_id, request.session_id, request.agent_id)

        return GetSessionResponse(
            response=json.dumps(response),
            status="success"
        )
    except HTTPException:
        # Re-raise HTTP exceptions as they are
        raise
    except Exception as e:
        logger.error(f"Error in get_session_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


class DeleteSessionRequest(BaseModel):
    user_id: str = Field(alias="userId")
    session_id: str = Field(alias="sessionId")
    agent_id: str = Field(alias="agentId")
    model_config = {"populate_by_name": True}
    
class DeleteSessionResponse(BaseModel):
    response: str
    status: str


async def delete_session(userId:str, sessionId:str, agentId:str) -> str:
    """
    Delete Session
    """
    try:
        
        agent_engine=agent_engines.get(agentId)
        async for event in agent_engine.async_delete_session(
            user_id=userId,
            session_id=sessionId,
        ):
            return event
    except Exception as e:
        logger.error(f"Error during delete_session invocation: {e}")
        return f"Error: {str(e)}"

@router.post("/delete-session", response_model=DeleteSessionResponse)
async def delete_session_endpoint(request: DeleteSessionRequest):
    """
    Invoke the delete_session with user id
    """
    try:
        if not request.user_id.strip():
            raise HTTPException(status_code=400, detail="User id cannot be empty")
        if not request.session_id.strip():
            raise HTTPException(status_code=400, detail="Session id cannot be empty")
        # Call the invoke_agent function with the user input from request
        response = await delete_session(request.user_id, request.session_id, request.agent_id)

        return DeleteSessionResponse(
            response=json.dumps(response),
            status="success"
        )
    except HTTPException:
        # Re-raise HTTP exceptions as they are
        raise
    except Exception as e:
        logger.error(f"Error in delete_session_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


class AddSessionToMemoryRequest(BaseModel):
    session: dict = Field(alias="session")
    agent_id: str = Field(alias="agentId")
    model_config = {"populate_by_name": True}
    
class AddSessionToMemoryResponse(BaseModel):
    response: str
    status: str


async def add_session_to_memory(session:dict, agentId:str) -> str:
    """
    Delete Session
    """
    try:
        
        agent_engine=agent_engines.get(agentId)
        async for event in agent_engine.async_add_session_to_memory(
            session=session,
        ):
            return event
    except Exception as e:
        logger.error(f"Error during add_session_to_memory invocation: {e}")
        return f"Error: {str(e)}"

@router.post("/add-session-to-memory", response_model=AddSessionToMemoryResponse)
async def add_session_to_memory_endpoint(request: AddSessionToMemoryRequest):
    """
    Invoke the add-session-to-memory with session
    """
    try:
        if not request.session:
            raise HTTPException(status_code=400, detail="Session dict cannot be empty")
        # Call the add_session_to_memory function with the user input from request
        response = await add_session_to_memory(request.session, request.agent_id)

        return AddSessionToMemoryResponse(
            response=json.dumps(response),
            status="success"
        )
    except HTTPException:
        # Re-raise HTTP exceptions as they are
        raise
    except Exception as e:
        logger.error(f"Error in add_session_to_memory_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    

class SearchMemoryRequest(BaseModel):
    user_id: str = Field(alias="userId")
    query: str = Field(alias="query")
    agent_id: str = Field(alias="agentId")
    model_config = {"populate_by_name": True}
    
class SearchMemoryResponse(BaseModel):
    response: str
    status: str


async def search_memory(user_id:str, query:str, agentId:str) -> str:
    """
    Search Memory
    """
    try:
        
        agent_engine=agent_engines.get(agentId)
        async for event in agent_engine.async_search_memory(
            user_id=user_id,
            query=query,
        ):
            return event
    except Exception as e:
        logger.error(f"Error during add_session_to_memory invocation: {e}")
        return f"Error: {str(e)}"

@router.post("/search-memory", response_model=SearchMemoryResponse)
async def search_memory_endpoint(request: SearchMemoryRequest):
    """
    Invoke the search_memory with user id and query
    """
    try:
        if not request.user_id.strip():
            raise HTTPException(status_code=400, detail="User Id cannot be empty")
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        # Call the add_session_to_memory function with the user input from request
        response = await search_memory(request.user_id, request.query, request.agent_id)

        return SearchMemoryResponse(
            response=json.dumps(response),
            status="success"
        )
    except HTTPException:
        # Re-raise HTTP exceptions as they are
        raise
    except Exception as e:
        logger.error(f"Error in search_memory_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")