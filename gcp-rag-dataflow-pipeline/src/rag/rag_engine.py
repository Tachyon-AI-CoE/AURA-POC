from urllib import response

from vertexai import rag
import vertexai
import logging
from datetime import datetime
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_or_create_corpus(vector_db, display_name, project_id, region, embedding_model):
        """
        Get or create a RAG corpus.
        
        Args:
            vector_db: Vector database instance
            display_name: Corpus display name
            project_id: GCP project ID (required)
            region: GCP region (required)
        """
        if not project_id or not region:
            raise ValueError(f"project_id and region are required. Got project_id={project_id}, region={region}")
        
        # Initialize vertexai with the correct region
        vertexai.init(project=project_id, location=region)
        # logger.info(f"✅ Initialized Vertex AI for corpus: project={project_id}, region={region}")
        
        if display_name is None:
            logger.info("No corpus_name provided in config, skipping corpus creation.")

        logger.info(f"Checking for vector db {vector_db}")
        
        logger.info(f"Checking for existing corpus with display_name: {display_name}")
        corpora = rag.list_corpora()
        existing = next((c for c in corpora if c.display_name == display_name), None)
        
        if existing:
            rag_corpus = existing
            logger.info(f"✅ Using existing corpus: {rag_corpus.name} (display_name: {display_name})")
        else:
            logger.info(f"🔨 Creating new corpus with display_name: {display_name}")
            try:
                rag_corpus = rag.create_corpus(
                    display_name=display_name,
                    backend_config=rag.RagVectorDbConfig(
                        vector_db=vector_db,
                        rag_embedding_model_config=rag.RagEmbeddingModelConfig(
                            vertex_prediction_endpoint=rag.VertexPredictionEndpoint(
                                publisher_model=embedding_model
                            )
                        )
                    )
                )
                logger.info(f"✅ Created new corpus: {rag_corpus.name} (display_name: {display_name})")
            except Exception as e:
                # Handle race condition: if corpus was created by another instance
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    logger.warning(f"Corpus '{display_name}' was created by another process, fetching it...")
                    # Re-fetch the list to get the newly created corpus
                    corpora = rag.list_corpora()
                    existing = next((c for c in corpora if c.display_name == display_name), None)
                    if existing:
                        rag_corpus = existing
                        logger.info(f"✅ Using corpus created by another process: {rag_corpus.name}")
                    else:
                        logger.error(f"Failed to find corpus '{display_name}' after creation conflict")
                        raise
                else:
                    logger.error(f"Failed to create corpus '{display_name}': {e}")
                    raise
        logger.info(f"Corpus details: Name={rag_corpus.name}, Display Name={rag_corpus.display_name}")
        return rag_corpus
#raise 

def get_result_path(rag_pipeline_config: dict) -> str:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        result_filename = f"rag_results-{ts}.ndjson"
        
        corpus_name = rag_pipeline_config.get("corpus_name")
        # Include corpus_name in the path for organized storage
        if corpus_name:
            result_path = f"{corpus_name}/{result_filename}"
        else:
            result_path = result_filename

        # Get result bucket from config (REQUIRED - no fallback)
        result_bucket = rag_pipeline_config.get("result_bucket")
        
        if not result_bucket:
            raise ValueError("result_bucket is required. Pass --result_bucket argument to Dataflow job")
        
        logging.info(f"[RAG] Using result bucket: {result_bucket}")
        result_gcs_path = f"gs://{result_bucket}/{result_path}"
        
        return result_gcs_path


def _build_transformation_config(rag_pipeline_config: dict) -> object:
    chunking_config = rag.ChunkingConfig(
        chunk_size=rag_pipeline_config.get('chunk_size', 512),
        chunk_overlap=rag_pipeline_config.get('chunk_overlap', 100),
    )

    parser_type = rag_pipeline_config.get('parser_type', '').upper()
    llm_parser_model = rag_pipeline_config.get('llm_parser_model', '')
    llm_custom_prompt = rag_pipeline_config.get('llm_custom_prompt', '')

    parsing_config = None
    if parser_type == 'LLM_PARSER' and llm_parser_model:
        parsing_config = rag.RagFileParsingConfig(
            llm_parser=rag.LlmParserConfig(
                model_name=llm_parser_model,
                custom_parsing_prompt=llm_custom_prompt or None,
            )
        )
        logger.info(f"Using LLM parser: model={llm_parser_model}")
    elif parser_type == 'ADVANCED_PDF':
        parsing_config = rag.RagFileParsingConfig(use_advanced_pdf_parsing=True)
        logger.info("Using advanced PDF parser")

    kwargs = {"chunking_config": chunking_config}
    if parsing_config:
        kwargs["rag_file_parsing_config"] = parsing_config

    return rag.TransformationConfig(**kwargs)


def import_files_to_corpus(rag_pipeline_config: dict, rag_corpus, rag_source):
    data_source = rag_pipeline_config.get("data_source_type").lower()
    result_gcs_path = get_result_path(rag_pipeline_config)
    #transformation_config = _build_transformation_config(rag_pipeline_config)

    if data_source == "gcs":
        logger.info("Importing files from GCS to corpus")
        logger.info(f"Using source path: {rag_source}")
        logger.info(f"rag_corpus name: {rag_corpus.name}")
        logger.info(f"Result GCS path: {result_gcs_path}")
        logger.info(f"Import config: chunk_size={rag_pipeline_config.get('chunk_size')}, chunk_overlap={rag_pipeline_config.get('chunk_overlap')}, max_embedding_requests_per_min={rag_pipeline_config.get('max_embedding_requests_per_min')}")

        try:
            response = rag.import_files(
                rag_corpus.name,
                paths=[f"{rag_source}"],
                #transformation_config=transformation_config,
                max_embedding_requests_per_min=rag_pipeline_config.get('max_embedding_requests_per_min', 1000),
                import_result_sink=result_gcs_path,
                timeout=720  # timeout as 720 sec
            )
            logger.info(f"Imported {response.imported_rag_files_count} files from GCS")
            logger.info(f"Skipped {response.skipped_rag_files_count} files from GCS")
        except Exception as e:
            logger.error(f"Failed to import files from GCS: {str(e)}")
            raise e

    else:
        logger.info(f"Importing files from {data_source.upper()} to corpus")
        logger.info(f"Using source: {rag_source}")
        logger.info(f"rag_corpus name: {rag_corpus.name}")

        try:
            response = rag.import_files(
                rag_corpus.name,
                source=rag_source,
                #transformation_config=transformation_config,
                max_embedding_requests_per_min=rag_pipeline_config.get('max_embedding_requests_per_min', 1000),
                import_result_sink=result_gcs_path,
                timeout=720  # timeout as 720 sec
            )
            logger.info(f"Imported {response.imported_rag_files_count} files from GCS")
            logger.info(f"Skipped {response.skipped_rag_files_count} files from GCS")
        except Exception as e:
            logger.error(f"Failed to import files from {data_source.upper()}: {str(e)}")
            raise e
    
    return response

##################################################################################################################



# # Deleting the corpus using the corpus ID
# --------------------------------------------
# from vertexai import rag
# import vertexai

# # Initialize Vertex AI API once per session
# vertexai.init(project=PROJECT_ID, location=REGION)

# rag.delete_corpus(name=corpus_name)
# logger.info(f"✅ Successfully deleted corpus: {corpus_name}")
# print(f"Corpus {corpus_name} deleted.")


# -----------------------------------------------------

# # Deleting the corpus using the display name
# -----------------------------------------------
# from vertexai import rag
# import vertexai

# # Initialize Vertex AI API once per session
# vertexai.init(project=PROJECT_ID, location=REGION)

# # Find corpus by display name
# logger.info(f"Looking for corpus with display_name: {CORPUS_DISPLAY_NAME}")
# corpora = rag.list_corpora()
# existing = next((c for c in corpora if c.display_name == CORPUS_DISPLAY_NAME), None)

# if not existing:
#     logger.error(f"Corpus with display_name '{CORPUS_DISPLAY_NAME}' not found")
#     raise ValueError(f"Corpus '{CORPUS_DISPLAY_NAME}' not found")

# corpus_name = existing.name
# logger.info(f"Found corpus: {corpus_name}")

# # Delete the corpus
# logger.info(f"Deleting corpus: {corpus_name}")
# rag.delete_corpus(name=corpus_name)
# logger.info(f"✅ Successfully deleted corpus: {corpus_name}")
# print(f"Corpus {corpus_name} deleted.")