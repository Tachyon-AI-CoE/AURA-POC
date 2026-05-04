# Dockerfile for Dataflow Flex Template
# Use the official Apache Beam Python SDK image as base
FROM gcr.io/dataflow-templates-base/python312-template-launcher-base

# Set working directory
WORKDIR /dataflow/template

# Copy setup.py and source code
COPY setup.py /dataflow/template/
COPY src/ /dataflow/template/src/

# Install the package and its dependencies
# This installs all modules into site-packages, making them globally importable
RUN pip install --no-cache-dir -e .

# Verify the package was installed correctly
RUN echo "=== Installed packages ===" && \
    pip list | grep rag-pipeline && \
    echo "=== Testing imports ===" && \
    python3 -c "import vectordatabase; print('vectordatabase imported successfully')" && \
    python3 -c "import config; print('config imported successfully')" && \
    python3 -c "import rag; print('rag imported successfully')" && \
    python3 -c "import data_sources; print('data_sources imported successfully')" && \
    python3 -c "import event_processor; print('event_processor imported successfully')" && \
    python3 -c "import dataflow_templates; print('dataflow_templates imported successfully')" && \
    echo "=== All imports successful ==="

# Set environment variables for Dataflow Flex Template
ENV FLEX_TEMPLATE_PYTHON_PY_FILE="/dataflow/template/src/dataflow_templates/rag_pipeline_template.py"
ENV FLEX_TEMPLATE_PYTHON_SETUP_FILE="/dataflow/template/setup.py"

# Ensure proper permissions
RUN chmod +x /dataflow/template/src/dataflow_templates/rag_pipeline_template.py
