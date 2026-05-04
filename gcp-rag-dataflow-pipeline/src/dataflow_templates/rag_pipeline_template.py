#!/usr/bin/env python3
"""
RAG Pipeline - Unified Flex Template

This template works with both DirectRunner and DataflowRunner using ValueProvider parameters.
It automatically handles parameter resolution for both execution modes.

Usage:
  # DirectRunner (development/testing)
  python rag_pipeline_template.py --runner=DirectRunner --config_source=gcs --config_bucket=my-bucket --config_file_pattern=config.json
  
  # DataflowRunner (production)
  gcloud dataflow flex-template run JOB_NAME --template-file-gcs-location=gs://bucket/template.json --parameters=config_source=gcs,config_bucket=my-bucket,...

Author: RAG Pipeline Team
Version: 3.0 (Unified Flex Template)
"""

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
import json
import logging
import sys
import os
from datetime import datetime
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# PIPELINE OPTIONS
# ============================================================================

class RAGPipelineOptions(PipelineOptions):
    """Custom pipeline options for RAG corpus creation."""
    
    @classmethod
    def _add_argparse_args(cls, parser):
        """Add custom arguments for RAG pipeline."""
        parser.add_argument(
            '--config_bucket',
            dest='config_bucket',
            help='GCS bucket containing configuration file'
        )
        parser.add_argument(
            '--config_file_pattern',
            dest='config_file_pattern',
            help='Configuration file name or pattern in GCS bucket'
        )
        parser.add_argument(
            '--result_bucket',
            dest='result_bucket',
            help='GCS bucket for storing pipeline results'
        )
        parser.add_argument(
            '--audit_bucket',
            dest='audit_bucket',
            help='GCS bucket for storing audit logs'
        )
        parser.add_argument(
            '--cloud_run_service',
            dest='cloud_run_service',
            help='Cloud Run service name for Eventarc trigger destination'
        )
        parser.add_argument(
            '--event_arc_service_account',
            dest='event_arc_service_account',
            help='Service account email used by Eventarc triggers'
        )
        parser.add_argument(
            '--corpus_mapping_bucket',
            dest='corpus_mapping_bucket',
            help='GCS bucket for storing corpus-to-staging-bucket mapping files'
        )
        parser.add_argument(
            '--status_webhook_url',
            dest='status_webhook_url',
            help='Webhook URL for sending RAG corpus status updates'
        )
        parser.add_argument(
            '--cloudrun_service_url',
            dest='cloudrun_service_url',
            help='Cloud Run service URL for getting the ID token audience'
        )


# ============================================================================
# PIPELINE TRANSFORMS (DoFns) - In execution order
# ============================================================================

class RAGCorpusConfigurationResolver(beam.DoFn):
    """DoFn that reads and flattens RAG corpus configuration from GCS for Dataflow pipeline."""
    
    def __init__(self, options: RAGPipelineOptions):
        self.options = options

    def get_option_value(self, option_attr):
        """Helper to get value from either static or ValueProvider."""
        if hasattr(self.options, option_attr):
            option_value = getattr(self.options, option_attr)
            if hasattr(option_value, 'get'):
                return option_value.get()
            return option_value
        return None

    def process(self, element):
        """Read and flatten configuration from GCS."""
        try:
            # Read configuration from GCS using Beam's FileSystems
            config_bucket = self.get_option_value('config_bucket')
            config_file_pattern = self.get_option_value('config_file_pattern')
            
            if not config_bucket or not config_file_pattern:
                raise ValueError(
                    "config_bucket and config_file_pattern are required. "
                    "Pass via --parameters: config_bucket=BUCKET,config_file_pattern=FILE"
                )
            
            gcs_path = f"gs://{config_bucket}/{config_file_pattern}"
            logging.info(f"[RAG] Reading config: {gcs_path}")
            
            from apache_beam.io.filesystems import FileSystems
            
            # Match and read config file
            match_results = FileSystems.match([gcs_path])
            if not match_results or not match_results[0].metadata_list:
                raise FileNotFoundError(f"No config files found: {gcs_path}")
            
            file_path = match_results[0].metadata_list[0].path
            with FileSystems.open(file_path) as f:
                config_content = f.read().decode('utf-8')
            
            config_data = json.loads(config_content)
            logging.info(f"[RAG] Config loaded: {file_path}")
            
            # Validate config file pattern and corpus name match
            try:
                from validators.config_validation import validate_gcs_eventfile_pattern
                validate_gcs_eventfile_pattern(config_file_pattern, config_data)
            except (ValueError, ImportError) as e:
                logging.warning(f"[RAG] Pattern validation: {e}")
            
            # Flatten configuration
            try:
                current_dir = os.path.dirname(__file__)
                parent_dir = os.path.join(current_dir, '..')
                if parent_dir not in sys.path:
                    sys.path.append(parent_dir)
                
                from config.rag_pipeline_config import get_flattened_rag_pipeline_config
                flattened_config = get_flattened_rag_pipeline_config(config_data)
            except ImportError:
                flattened_config = config_data
            
            # Validate flattened configuration
            try:
                from validators.config_validation import validate_config
                if not validate_config(flattened_config):
                    raise ValueError("Configuration validation failed")
            except ImportError:
                pass
            
            # Add runtime metadata
            flattened_config.update({
                '_config_source': 'gcs',
                '_resolved_at': datetime.now().isoformat(),
                '_config_file': file_path
            })
            
            # Merge pipeline options
            all_options = self.options.get_all_options()
            if all_options.get('project'):
                flattened_config['project_id'] = all_options['project']
            if all_options.get('region'):
                flattened_config['region'] = all_options['region']
            
            # Validate and add required buckets
            result_bucket = self.get_option_value('result_bucket')
            audit_bucket = self.get_option_value('audit_bucket')
            
            if not result_bucket:
                raise ValueError("result_bucket is REQUIRED in --parameters")
            if not audit_bucket:
                raise ValueError("audit_bucket is REQUIRED in --parameters")
            
            flattened_config['result_bucket'] = result_bucket
            flattened_config['audit_bucket'] = audit_bucket
            
            # Extract optional parameters
            optional_params = {
                'cloud_run_service': self.get_option_value('cloud_run_service'),
                'event_arc_service_account': self.get_option_value('event_arc_service_account'),
                'corpus_mapping_bucket': self.get_option_value('corpus_mapping_bucket'),
                'status_webhook_url': self.get_option_value('status_webhook_url'),
                'cloudrun_service_url': self.get_option_value('cloudrun_service_url'),
            }
            
            for key, value in optional_params.items():
                if value:
                    flattened_config[key] = value
            
            logging.info(f"[RAG] Config ready - Corpus: {flattened_config.get('corpus_name')}, "
                        f"DB: {flattened_config.get('vector_db_type')}")
            
            yield flattened_config
            
        except Exception as e:
            logging.error(f"[RAG] Configuration failed: {e}")
            logging.error(f"[RAG] Traceback: {traceback.format_exc()}")
            
            # Build failure config for audit/webhook
            failure_config = {
                'corpus_name': flattened_config.get('corpus_name'),
                'config_source': 'configuration_resolver'
            }
            
            try:
                audit_bucket = self.get_option_value('audit_bucket')
                if audit_bucket:
                    failure_config['audit_bucket'] = audit_bucket
                
                status_webhook_url = self.get_option_value('status_webhook_url')
                logging.info(f"[RAG] Extracted status_webhook_url: {status_webhook_url is not None}")
                if status_webhook_url:
                    failure_config['status_webhook_url'] = status_webhook_url
                    logging.info(f"[RAG] Webhook URL added to failure_config")
                
                # Add project and region if available from pipeline options
                all_options = self.options.get_all_options()
                if all_options.get('project'):
                    failure_config['project_id'] = all_options['project']
                if all_options.get('region'):
                    failure_config['region'] = all_options['region']
                
                from event_processor.gcs_event_processor import write_failure_audit
                write_failure_audit(failure_config, 'configuration_resolution_failed', e)
            except Exception as audit_ex:
                logging.error(f"[RAG] Failed to write audit/webhook: {audit_ex}")
            
            raise

class RAGVectorDatabaseInitializer(beam.DoFn):
    """Initialize RAG vector database for corpus creation in Dataflow pipeline."""
    
    def process(self, config):
        try:
            from vectordatabase.vector_db import initialize_vector_db
            
            vector_db = initialize_vector_db(config)
            config['vector_db_instance'] = vector_db
            
            logging.info(f"[RAG] Vector DB initialized: {type(vector_db).__name__}")
            yield config
        except Exception as e:
            logging.error(f"[RAG] Vector DB initialization failed: {e}")
            from event_processor.gcs_event_processor import write_failure_audit
            write_failure_audit(config, 'vector_db_initialization_failed', e)
            raise


class CreateOrGetRAGCorpus(beam.DoFn):
    """Create or retrieve RAG corpus for document ingestion in Dataflow pipeline."""
    
    def process(self, config):
        try:
            from rag.rag_engine import get_or_create_corpus
            
            vector_db = config.get('vector_db_instance')
            corpus_name = config.get('corpus_name') or config.get('display_name')
            project_id = config.get('project_id')
            region = config.get('region')
            embedding_model = config.get('embedding_model', 'publishers/google/models/text-multilingual-embedding-002')
            if not corpus_name:
                raise ValueError("corpus_name is required")
            if not project_id:
                raise ValueError("project_id is required. Pass --project to Dataflow")
            if not region:
                raise ValueError("region is required")
            
            logging.info(f"[RAG] Creating/getting corpus: {corpus_name}")
            
            corpus = get_or_create_corpus(vector_db, corpus_name, project_id, region, embedding_model)
            
            config['rag_corpus_instance'] = corpus
            config['corpus_name'] = corpus_name
            
            logging.info(f"[RAG] Corpus ready: {corpus.name if hasattr(corpus, 'name') else corpus_name}")
            yield config
        except Exception as e:
            logging.error(f"[RAG] Corpus management failed: {e}")
            from event_processor.gcs_event_processor import write_failure_audit
            write_failure_audit(config, 'corpus_creation_failed', e)
            raise


class RAGDataSourcePathResolver(beam.DoFn):
    """Resolve GCS source path for RAG document ingestion in Dataflow pipeline."""
    
    def process(self, config):
        try:
            from data_sources.gcs_data_source import get_source_path
            
            staging_bucket = config.get('staging_bucket') or config.get('data_staging_bucket')
            
            if not staging_bucket:
                raise ValueError("staging_bucket is required")
            
            source_path = get_source_path(staging_bucket)
            config['source_path'] = source_path
            
            logging.info(f"[RAG] Source path: {source_path}")
            yield config
        except Exception as e:
            logging.error(f"[RAG] Source path resolution failed: {e}")
            from event_processor.gcs_event_processor import write_failure_audit
            write_failure_audit(config, 'source_path_resolution_failed', e)
            raise


class ImportFilesToRAGCorpus(beam.DoFn):
    """Import documents to RAG corpus in Dataflow pipeline for vector indexing."""
    
    def process(self, config):
        try:
            from rag.rag_engine import import_files_to_corpus
            
            rag_corpus = config.get('rag_corpus_instance')
            rag_source = config.get('source_path')
            
            if not rag_corpus:
                raise ValueError("rag_corpus_instance is required")
            if not rag_source:
                raise ValueError("source_path is required")
            
            logging.info(f"[RAG] Importing from {rag_source}")
            import_response = import_files_to_corpus(config, rag_corpus, rag_source)
            
            # Archive config file
            try:
                from event_processor.gcs_event_processor import archive_config_file
                archive_config_file(config)
            except Exception as e:
                logging.warning(f"[RAG] Config archive failed: {e}")
            
            # Add import stats to config
            if import_response:
                config['message'] = (f"Imported {import_response.imported_rag_files_count} file(s), "
                                   f"Skipped {import_response.skipped_rag_files_count} file(s)")
            
            # Write success audit
            try:
                from event_processor.gcs_event_processor import write_rag_audit
                write_rag_audit(config, 'corpus_creation_completed')
            except Exception as e:
                logging.warning(f"[RAG] Audit write failed: {e}")
            
            # Create Eventarc trigger if sync enabled
            if config.get('sync_through_rag_pipeline', False):
                try:
                    from event_arc.event_arc_trigger import create_eventarc_trigger
                    
                    trigger_name = f"rag-trigger-{config.get('corpus_name')}"
                    bucket_name = config.get('staging_bucket') or config.get('data_staging_bucket')
                    project_id = config.get('project_id')
                    location = config.get('region')
                    
                    if not bucket_name:
                        raise ValueError("staging_bucket required for Eventarc trigger")
                    if not project_id:
                        raise ValueError("project_id required for Eventarc trigger")
                    if not location:
                        raise ValueError("region required for Eventarc trigger")
                    
                    cloud_run_service = config.get('cloud_run_service', 'rag-event-handler')
                    event_arc_service_account = config.get('event_arc_service_account')
                                                
                    trigger_result = create_eventarc_trigger(
                        trigger_name=trigger_name,
                        bucket_name=bucket_name,
                        project_id=project_id,
                        location=location,
                        cloud_run_service=cloud_run_service,
                        event_arc_service_account=event_arc_service_account
                    )
                    
                    status = trigger_result.get('status')
                    if status == 'error':
                        logging.error(f"[RAG] Eventarc trigger failed: {trigger_result.get('error')}")
                    elif status == 'warning':
                        logging.warning(f"[RAG] Eventarc trigger exists: {trigger_result.get('trigger_name')}")
                    else:
                        logging.info(f"[RAG] Eventarc trigger created: {trigger_result.get('trigger_resource_name')}")
                except Exception as e:
                    logging.error(f"[RAG] Eventarc trigger error: {e}")
            
            # Create corpus mapping file
            corpus_mapping_bucket = config.get('corpus_mapping_bucket')
            if corpus_mapping_bucket:
                try:
                    corpus_name = config.get('corpus_name', 'unknown')
                    staging_bucket = config.get('staging_bucket') or config.get('data_staging_bucket')
                    
                    if not staging_bucket:
                        logging.warning("[RAG] staging_bucket not found - skipping corpus mapping")
                    else:
                        # Create JSON content
                        corpus_mapping_data = {
                            'corpus_name': corpus_name,
                            'staging_bucket': staging_bucket,
                            'created_at': datetime.now().isoformat(),
                            'project_id': config.get('project_id', 'unknown'),
                            'region': config.get('region', 'unknown'),
                            'vector_db_type': config.get('vector_db_type', 'unknown')
                        }
                        
                        # Add corpus resource name if available
                        corpus_instance = config.get('rag_corpus_instance')
                        if corpus_instance and hasattr(corpus_instance, 'name'):
                            corpus_mapping_data['corpus_resource_name'] = corpus_instance.name
                        
                        # Write using Beam FileSystems
                        mapping_file_path = f"gs://{corpus_mapping_bucket}/{staging_bucket}.json"
                        
                        from apache_beam.io.filesystems import FileSystems
                        with FileSystems.create(mapping_file_path) as f:
                            f.write(json.dumps(corpus_mapping_data, indent=2).encode('utf-8'))
                        
                        logging.info(f"[RAG] Corpus mapping created: {mapping_file_path}")
                        
                except Exception as e:
                    logging.warning(f"[RAG] Corpus mapping failed: {e}")

            logging.info("[RAG] Files imported successfully")
            yield config
        except Exception as e:
            logging.error(f"[RAG] File import failed: {e}")
            from event_processor.gcs_event_processor import write_failure_audit
            write_failure_audit(config, 'file_import_failed', e)
            raise


class SendWebhookNotification(beam.DoFn):
    """Standalone worker to send webhook notifications AFTER corpus import completes."""
    
    def process(self, config):
        """
        Send webhook notification after ImportFiles completes.
        Runs as separate worker with all corpus data available (truly standalone).
        Note: Only runs if status_webhook_url is provided (filtered by pipeline).
        """
        try:
            webhook_url = config.get('status_webhook_url')
            
            from webhooks.webhook_notifier import send_rag_status
            
            logging.info(f"[RAG] Standalone webhook worker started (post-processing)")
            
            # Extract corpus resource name (available since this runs AFTER ImportFiles)
            corpus_resource_name = None
            corpus_instance = config.get('rag_corpus_instance')
            if corpus_instance and hasattr(corpus_instance, 'name'):
                corpus_resource_name = corpus_instance.name
                logging.info(f"[RAG] Corpus resource name available: {corpus_resource_name}")
            
            # Send success webhook
            webhook_result = send_rag_status(
                corpus_name=config.get('corpus_name', 'unknown'),
                status='Ready',
                webhook_url=webhook_url,
                corpus_resource_name=corpus_resource_name,
                project_id=config.get('project_id'),
                region=config.get('region'),
                cloudrun_service_url=config.get('cloudrun_service_url')
            )
            
            # Log result
            if webhook_result and webhook_result.get('status') == 'success':
                logging.info(f"[RAG] Webhook sent successfully by standalone worker")
            elif webhook_result:
                logging.warning(f"[RAG] Webhook failed: {webhook_result.get('error', 'Unknown error')}")
            
            yield config
                
        except Exception as e:
            # Don't fail the pipeline if webhook fails
            logging.warning(f"[RAG] Webhook worker error (non-blocking): {e}")
            yield config


# ============================================================================
# MAIN PIPELINE EXECUTION
# ============================================================================

def run_rag_corpus_creation_pipeline():
    """Main Dataflow pipeline for RAG corpus creation - works with both DirectRunner and DataflowRunner."""
    logger.info("[RAG] Pipeline Starting - Version 3.0")
    
    pipeline_options = PipelineOptions()
    rag_options = pipeline_options.view_as(RAGPipelineOptions)
    
    try:
        with beam.Pipeline(options=pipeline_options) as pipeline:
            # Main configuration - shared by all workers
            config_resolved = (
                pipeline 
                | 'Start' >> beam.Create(['start'])
                | 'ResolveConfig' >> beam.ParDo(RAGCorpusConfigurationResolver(rag_options))
            )
            
            # Main RAG corpus processing pipeline
            import_results = (
                config_resolved
                | 'InitVectorDB' >> beam.ParDo(RAGVectorDatabaseInitializer())
                | 'CreateCorpus' >> beam.ParDo(CreateOrGetRAGCorpus())
                | 'ResolveSourcePath' >> beam.ParDo(RAGDataSourcePathResolver())
                | 'ImportFiles' >> beam.ParDo(ImportFilesToRAGCorpus())
            )
            
            # Conditional webhook: Only run if URL is provided
            _ = (
                import_results
                | 'FilterForWebhook' >> beam.Filter(lambda config: config.get('status_webhook_url') is not None)
                | 'SendWebhook' >> beam.ParDo(SendWebhookNotification())  # Only runs if URL exists
            )
        
        logger.info("[RAG] Pipeline completed successfully")
    
    except Exception as e:
        logger.error(f"[RAG] Pipeline failed: {e}")
        logger.error(f"[RAG] Details: {traceback.format_exc()}")
        raise


if __name__ == '__main__': 
    logger.info("[RAG] Unified Flex Template Entry Point")
    
    try:
        run_rag_corpus_creation_pipeline() 
    except KeyboardInterrupt:
        logger.warning("[RAG] Pipeline interrupted")
        sys.exit(1)
    except Exception as e:
        logger.error(f"[RAG] Fatal error: {e}")
        sys.exit(1)
