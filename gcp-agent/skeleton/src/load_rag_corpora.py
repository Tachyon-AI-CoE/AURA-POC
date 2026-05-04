import os
import json
from utils.log_helper import setup_logging
logger = setup_logging()
from google.adk.tools.retrieval import vertex_ai_rag_retrieval
from vertexai import rag

# Function to create retrieval tools
def get_corpus_as_tools(filepath):
    rag_tools = []
    if os.path.exists(filepath):
        # Read the JSON file
        with open(filepath, 'r') as file:
            config = json.load(file)

        # Loop through each agent in the data array
        for rag_item in config:
            if "rag_details" not in rag_item or "value" not in rag_item["rag_details"] or "vectorizeddatasetbaseid" not in rag_item["rag_details"]["value"]:
                logger.error("RAG details or vectorizeddatasetbaseid missing in configuration.")
                continue
            corpus_id = rag_item["rag_details"]["value"]["vectorizeddatasetbaseid"]
            logger.info(f"Creating RAG tool for corpus ID: {corpus_id}")

            try:
                # Create retrieval configuration
                # retrieval_config = types.RetrievalConfig(
                #    top_k=3,
                #    filter=types.Filter(vector_distance_threshold=0.5)
                # )
                
                # Create corpus retrieval tool for ADK
                rag_retrieval_tool = vertex_ai_rag_retrieval.VertexAiRagRetrieval(
                    name="claims",
                    description="get claims for a user ",
                    rag_corpora = [corpus_id])
                rag_tools.append(rag_retrieval_tool)
                logger.info("Successfully created RAG tool for ADK")
                
            except Exception as e:
                logger.error(f"Error creating RAG tool for ADK: {str(e)}")
                raise
            
    return rag_tools