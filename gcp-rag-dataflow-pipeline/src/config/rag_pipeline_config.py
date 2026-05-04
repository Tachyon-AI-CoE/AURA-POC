#  flattens it into a single-level dictionary with simple key-value pairs.(Easier to access , Simpler to pass around,Easier validation)
def get_flattened_rag_pipeline_config(rag_pipeline_config: dict) -> dict:
        rag_corpus = rag_pipeline_config.get("rag_corpus", {})
        
        # Note: project_id and region are BOTH added by ConfigurationResolverDoFn from pipeline options
        # They come from --project and --region command-line arguments ONLY
        
        # Dynamic request-specific values only
        CORPUS_NAME = rag_corpus.get("corpus_name", "")
        corpus_name = CORPUS_NAME  # lowercase alias
        corpus_description = rag_corpus.get("description", "")
        description = corpus_description  # Alias
        sync_through_rag_pipeline = rag_corpus.get("sync_through_rag_pipeline", False)

        # Data source configuration
        data_source_config = rag_corpus.get("data_source", {})
        data_source_type = data_source_config.get("type")
        data_staging_bucket = data_source_config.get("staging_bucket", "")
        
        # JIRA Configuration
        jira_config = data_source_config.get("jira_data_source_config", {})
        jira_projects = jira_config.get("jira_projects", [])
        jira_custom_query = jira_config.get("custom_query", [])
        jira_email = jira_config.get("email", "")
        jira_server_uri = jira_config.get("server_uri", "")
        jira_api_secret_key = jira_config.get("api_secret_key", "")
        jira_sync_through_rag_pipeline = jira_config.get("sync_through_rag_pipeline", False)
        
        # SharePoint Configuration
        sharepoint_config = data_source_config.get("sharepoint_data_source_config", {})
        sharepoint_client_id = sharepoint_config.get("client_id", "")
        sharepoint_tenant_id = sharepoint_config.get("tenant_id", "")
        sharepoint_site_name = sharepoint_config.get("site_name", "")
        sharepoint_folder_path = sharepoint_config.get("folder_path", "")
        sharepoint_drive_name = sharepoint_config.get("drive_name", "")
        sharepoint_api_secret_key = sharepoint_config.get("api_secret_key", "")
        sharepoint_sync_through_rag_pipeline = sharepoint_config.get("sync_through_rag_pipeline", False)
        
        # Embedding Configuration
        embedding_config = rag_corpus.get("embedding_config", {})
        embedding_model = embedding_config.get("embedding_model", "")
        chunk_size = embedding_config.get("chunk_size", 1000)
        chunk_overlap = embedding_config.get("chunk_overlap", 200)
        max_embedding_requests_per_min = embedding_config.get("max_embedding_requests_per_min", 1000)
        parser_type = embedding_config.get("parser_type", "")
        
        # LLM Parser
        llm_parser = embedding_config.get("llm_parser", {})
        llm_parser_model = llm_parser.get("model", "")
        llm_custom_prompt = llm_parser.get("custom_prompt", "")
        
        # Vector Database Configuration
        vector_db_config = rag_corpus.get("vector_db", {})
        vector_db_type = vector_db_config.get("type", "")
        
        vector_search_config = vector_db_config.get("vector_search_config", {})
        vector_db_dimensions = vector_search_config.get("dimensions", 768)
        approximate_neighbours_count = vector_search_config.get("approximate_neighbours_count", 10)
        distance_measure_type = vector_search_config.get("distance_measure_type", "COSINE_DISTANCE")
        
        rag_managed_db_config = vector_db_config.get("rag_managed_db_config", {})
        retrieval_strategy = rag_managed_db_config.get("retrieval_strategy", "")
        
        # Summarization Configuration
        summarization_config = rag_corpus.get("summarization", {})
        pre_corpus_summarization = summarization_config.get("corpus_summarization", False)
        custom_summarization_prompt_instructions = summarization_config.get("summarization_instructions", "")
        
        # Metadata Configuration
        metadata_config = rag_corpus.get("metadata", {})
        metadata_extractor = metadata_config.get("metadata_extractor", "")
        metadata_fields = metadata_config.get("metadata_fields", [])

        config_dict = {
        # Request-specific config only
        # Note: project_id and region are added by ConfigurationResolverDoFn from --project and --region
        'corpus_name': corpus_name,
        'corpus_description': corpus_description,
        'description': description,
        'sync_through_rag_pipeline': sync_through_rag_pipeline,
        'data_staging_bucket': data_staging_bucket,
        'jira_projects': jira_projects,
        'jira_custom_query': jira_custom_query,
        'jira_email': jira_email,
        'jira_server_uri': jira_server_uri,
        'jira_api_secret_key': jira_api_secret_key,
        'jira_sync_through_rag_pipeline': jira_sync_through_rag_pipeline,
        'sharepoint_client_id': sharepoint_client_id,
        'sharepoint_tenant_id': sharepoint_tenant_id,
        'sharepoint_site_name': sharepoint_site_name,
        'sharepoint_folder_path': sharepoint_folder_path,
        'sharepoint_drive_name': sharepoint_drive_name,
        'sharepoint_api_secret_key': sharepoint_api_secret_key,
        'sharepoint_sync_through_rag_pipeline': sharepoint_sync_through_rag_pipeline,
        'embedding_model': embedding_model,
        'chunk_size': chunk_size,
        'chunk_overlap': chunk_overlap,
        'max_embedding_requests_per_min': max_embedding_requests_per_min,
        'parser_type': parser_type,
        'llm_parser_model': llm_parser_model,
        'llm_custom_prompt': llm_custom_prompt,
        'vector_db_type': vector_db_type,
        'vector_db_dimensions': vector_db_dimensions,
        'approximate_neighbours_count': approximate_neighbours_count,
        'distance_measure_type': distance_measure_type,
        'retrieval_strategy': retrieval_strategy,
        'pre_corpus_summarization': pre_corpus_summarization,
        'custom_summarization_prompt_instructions': custom_summarization_prompt_instructions,
        'metadata_extractor': metadata_extractor,
        'metadata_fields': metadata_fields,
        'data_source_type': data_source_type,
    }
        
        return config_dict