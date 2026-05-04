# Client to invoke vertexai agent

A standalone Python utility to create a client app for invoking vertexai Agents.

The project uses [uv](https://docs.astral.sh/uv/) for packaging and execution. If not already installed install using
``pip install uv``

## Create Virtual Environment and activate it
``uv venv``
``source .venv/bin/activate``

## Usage

1. Set up your configuration variables (see `/config/configuration.json`).
2. Run:

```bash
uv run src/sample_client_app.py
```

## Project Structure
- `src/agent_client.py`: Main script for agent creation.
- `src/sample_client_app.py`: client application
- `pyproject.toml`: Project metadata and dependencies.
- `README.md`: This file.
- `src/`: Source code directory.

## Requirements
- Python 3.8+
- GCP Vertexai credentials
