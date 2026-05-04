"""RAG tool configuration and builder for Vertex AI RAG retrieval."""

from typing import Any, Dict, List, Optional, Union

from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval
from vertexai import rag

from utils.log_helper import setup_logging

logger = setup_logging()


def create_rag_resource_from_corpus_id(
    corpus_id: str, project_id: str, location: str
) -> rag.RagResource:
    corpus_path = f"projects/{project_id}/locations/{location}/ragCorpora/{corpus_id}"
    return rag.RagResource(rag_corpus=corpus_path)


def create_rag_resource_from_path(corpus_path: str) -> rag.RagResource:
    return rag.RagResource(rag_corpus=corpus_path)


def build_rag_resources_from_config(
    rag_resources_config: Union[str, List[str]],
    project_id: Optional[str] = None,
    location: Optional[str] = None,
) -> List[rag.RagResource]:
    """Build RAG resources from configuration (corpus IDs or full paths)."""
    if isinstance(rag_resources_config, str):
        rag_resources_config = [rag_resources_config]

    valid_resources = [resource for resource in rag_resources_config if resource]

    if not valid_resources:
        return []

    rag_resources = []

    if all(resource.startswith("projects/") for resource in valid_resources):
        for corpus_path in valid_resources:
            rag_resources.append(create_rag_resource_from_path(corpus_path))
    else:
        if not project_id or not location:
            for resource in valid_resources:
                rag_resources.append(create_rag_resource_from_path(resource))
        else:
            for corpus_id in valid_resources:
                rag_resources.append(
                    create_rag_resource_from_corpus_id(corpus_id, project_id, location)
                )

    return rag_resources


def create_vertex_ai_rag_retrieval(
    name: str,
    description: str,
    rag_resources: List[rag.RagResource],
    similarity_top_k: int = 15,
    vector_distance_threshold: float = 0.75,
) -> VertexAiRagRetrieval:
    if not name:
        raise ValueError("❌ Tool name is required")
    if not description:
        raise ValueError("❌ Tool description is required")
    if not rag_resources:
        raise ValueError("❌ At least one RAG resource is required")

    return VertexAiRagRetrieval(
        name=name,
        description=description,
        rag_resources=rag_resources,
        similarity_top_k=similarity_top_k,
        vector_distance_threshold=vector_distance_threshold,
    )


def create_rag_tool_from_yaml_config(
    rag_tool_config: Dict[str, Any],
    global_config: Optional[Dict[str, Any]] = None,
    agent_name: str = None,
) -> Optional[VertexAiRagRetrieval]:
    """Create a RAG tool from YAML configuration with RAG resources and retrieval parameters."""
    try:
        tool_config = rag_tool_config.get("config", {})

        name = rag_tool_config.get("name", "VertexAI_RAG_Tool")
        description = rag_tool_config.get(
            "description",
            "A tool to retrieve information from a knowledge base using RAG.",
        )
        similarity_top_k = tool_config.get("similarity_top_k", 10)
        vector_distance_threshold = tool_config.get("vector_distance_threshold", 0.8)

        rag_resources_list = []

        if "rag_resources" in tool_config:
            rag_resources_config = tool_config["rag_resources"]
            if isinstance(rag_resources_config, list):
                for resource_obj in rag_resources_config:
                    if (
                        isinstance(resource_obj, dict)
                        and "rag_resource" in resource_obj
                    ):
                        rag_resources_list.append(resource_obj["rag_resource"])
                    elif isinstance(resource_obj, str):
                        rag_resources_list.append(resource_obj)
            elif (
                isinstance(rag_resources_config, dict)
                and "rag_resource" in rag_resources_config
            ):
                rag_resources_list.append(rag_resources_config["rag_resource"])

        if not rag_resources_list:
            logger.warning(
                f"⚠️ No RAG resources configured for tool '{name}' in agent '{agent_name}'. Skipping RAG tool creation."
            )
            return None

        project_id = tool_config.get("project_id")
        location = tool_config.get("location")

        if not project_id and global_config:
            project_id = global_config.get("project_id")
        if not location and global_config:
            location = global_config.get("location", "us-central1")

        rag_resources = build_rag_resources_from_config(
            rag_resources_list, project_id, location
        )

        if not rag_resources:
            logger.warning(
                f"⚠️ No valid RAG resources found for tool '{name}' in agent '{agent_name}'. Skipping RAG tool creation."
            )
            return None

        return create_vertex_ai_rag_retrieval(
            name=name,
            description=description,
            rag_resources=rag_resources,
            similarity_top_k=similarity_top_k,
            vector_distance_threshold=vector_distance_threshold,
        )

    except Exception as e:
        logger.error(
            f"❌ Error creating RAG tool '{rag_tool_config.get('name', 'unnamed')}' for agent '{agent_name}': {e}"
        )
        return None
