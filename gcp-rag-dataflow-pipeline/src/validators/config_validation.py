from config import config
import logging
import json
import re
from datetime import datetime
from google.cloud import storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_config(rag_pipeline_config: dict) -> bool:
    """
    Validate GCS configuration. Expects a FLATTENED config.
    
    Returns:
        bool: True if valid, False otherwise
    """
    errors = []
    
    # Required fields
    required_fields = {
        'data_source_type': 'Data source type',
        'corpus_name': 'Corpus name',
        'vector_db_type': 'Vector DB type',
        'chunk_size': 'Chunk size',
        'chunk_overlap': 'Chunk overlap',
        'embedding_model': 'Embedding model'
    }
    
    for field, description in required_fields.items():
        if not rag_pipeline_config.get(field):
            errors.append(f"Missing required field: '{field}' ({description})")
    
    # Report results
    if errors:
        logger.error("❌ Configuration Validation FAILED:")
        for idx, error in enumerate(errors, 1):
            logger.error(f"  {idx}. {error}")
        return False
    
    logger.info("✅ Configuration Validation PASSED")
    return True



def validate_gcs_eventfile_pattern(config_file_pattern: str, config_data: dict) -> bool:
    """
    Validate that the config file pattern follows the format: rag_{CORPUS_NAME}_config.(json|txt|yaml|yml)
    and that the corpus name in the pattern matches the corpus_name in the config file.
    
    Args:
        config_file_pattern: The config file name (e.g., "rag_mykorpus_config.json")
        config_data: The loaded configuration dictionary
    
    Returns:
        bool: True if valid, False otherwise
    
    Raises:
        ValueError: If validation fails with detailed error message
    """
    # Regex pattern: rag_{CORPUS_NAME}_config.(json|txt|yaml|yml)
    pattern = r'^rag_([a-zA-Z0-9_-]+)_config\.(json|txt|yaml|yml)$'
    
    match = re.match(pattern, config_file_pattern)
    
    if not match:
        raise ValueError(
            f"Invalid config file pattern: '{config_file_pattern}'. "
            f"Expected format: 'rag_{{CORPUS_NAME}}_config.(json|txt|yaml|yml)'"
        )
    
    # Extract corpus name from filename and normalize underscores to hyphens
    corpus_name_from_file = match.group(1).replace('_', '-')
    # corpus_name_from_file = match.group(1)
    logger.info(f"[VALIDATION] Corpus name from file pattern (normalized): '{corpus_name_from_file}'")
    
    # Extract corpus name from config
    # Handle nested structure: config_data['rag_corpus']['corpus_name']
    config_corpus_name = None
    if 'rag_corpus' in config_data and isinstance(config_data['rag_corpus'], dict):
        config_corpus_name = config_data['rag_corpus'].get('corpus_name')
    else:
        # Fallback: check top-level
        config_corpus_name = config_data.get('corpus_name')
    
    if not config_corpus_name:
        raise ValueError(
            "Corpus name not found in configuration file. "
            "Expected field: 'rag_corpus.corpus_name' or 'corpus_name'"
        )
    
    logger.info(f"[VALIDATION] Corpus name from config: '{config_corpus_name}'")
    
    # Compare corpus names (case-sensitive)
    if corpus_name_from_file != config_corpus_name:
        raise ValueError(
            f"Corpus name mismatch! "
            f"File pattern has '{corpus_name_from_file}' but config contains '{config_corpus_name}'. "
            f"They must match exactly."
        )
    
    logger.info(f"✅ [VALIDATION] Config file pattern validated: corpus name '{corpus_name_from_file}' matches")
    return True
