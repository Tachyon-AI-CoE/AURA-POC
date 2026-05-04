"""
RAG Pipeline Dataflow Templates

This package contains Google Cloud Dataflow templates for the RAG (Retrieval-Augmented Generation) pipeline.
Templates provide reusable, parameterized pipeline deployments that can be executed multiple times
with different runtime configurations.

Modules:
- rag_pipeline_template: Main Dataflow template implementation
- deploy_template: Deployment and execution utilities

Usage:
    # Create template
    python templates/deploy_template.py --action create --template_location gs://bucket/template

    # Run template  
    python templates/deploy_template.py --action run --template_location gs://bucket/template --corpus_name my-corpus
"""

__version__ = "1.0.0"
__author__ = "RAG Pipeline Team"

# Template metadata
TEMPLATE_INFO = {
    "name": "rag-pipeline-dataflow-template",
    "version": __version__,
    "description": "Google Cloud Dataflow template for RAG corpus creation and document import",
    "supported_data_sources": ["gcs", "jira", "sharepoint"],
    "required_apis": [
        "dataflow.googleapis.com",
        "aiplatform.googleapis.com", 
        "storage.googleapis.com"
    ],
    "min_python_version": "3.11"
}
