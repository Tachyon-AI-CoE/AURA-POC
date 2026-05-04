# Tests for gcp-rag-dataflow-pipeline

## Overview

Unit tests for the RAG (Retrieval Augmented Generation) Dataflow Pipeline modules.

## Structure

```
tests/
├── __init__.py                         # Test package marker
├── conftest.py                         # Shared fixtures and mock module registration
├── requirements-test.txt               # Test-only dependencies
├── README.md                           # This file
├── test_config.py                      # Tests for config/config.py constants
├── test_config_validation.py           # Tests for validators/config_validation.py
├── test_event_arc_trigger.py           # Tests for event_arc/event_arc_trigger.py
├── test_gcs_data_source.py             # Tests for data_sources/gcs_data_source.py
├── test_gcs_event_processor.py         # Tests for event_processor/gcs_event_processor.py
├── test_instructions.py                # Tests for agents/summariser_agent/instuctions.py
├── test_jira_data_source.py            # Tests for data_sources/jira_data_source.py
├── test_main.py                        # Tests for main.py Cloud Function handler
├── test_rag_engine.py                  # Tests for rag/rag_engine.py
├── test_rag_managed_db.py              # Tests for vectordatabase/rag_managed_db.py
├── test_rag_pipeline_config.py         # Tests for config/rag_pipeline_config.py
├── test_rag_pipeline_template.py       # Tests for dataflow_templates/rag_pipeline_template.py
├── test_rag_pipeline_utils.py          # Tests for utils/rag_pipeline_utils.py
├── test_run_agent.py                   # Tests for doc_processor/run_agent.py
├── test_summarizer_agent.py            # Tests for agents/summariser_agent/summarizer_agent.py
├── test_summary_document_processor.py  # Tests for doc_processor/summary_document_processor.py
├── test_vector_db.py                   # Tests for vectordatabase/vector_db.py
├── test_vectorsearch.py               # Tests for vectordatabase/vectorsearch.py
└── test_webhook_notifier.py            # Tests for webhooks/webhook_notifier.py
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run a specific test file
pytest tests/test_rag_engine.py -v
```

## Test Dependencies

Install test dependencies:

```bash
pip install -r tests/requirements-test.txt
```

## Notes

- External dependencies (Apache Beam, Vertex AI RAG, Eventarc, etc.) are mocked in `conftest.py`
- Tests use `unittest.mock` for isolating external service calls
- No changes are made to core source files — tests are self-contained
