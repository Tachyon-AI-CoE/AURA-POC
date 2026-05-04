# ${{ values.name }}

## Overview

This is a GCP Agent project created from the NeuroAI GCP Agent template. This Agent helps protect your AI applications by implementing safety measures and content filtering.

## Description

# ${{ values.description }}

## Configuration

### Agent Details
- **Name**: ${{ values.name }}
- **Description**: ${{ values.description }}
- **Region**: ${{ values.region }}
- **Owner**: ${{ values.owner }}
- **Lifecycle**: ${{ values.lifecycle }}


## Files Structure

```
.
├── python/
│   └── src/
│       ├── data_create.py      # Creates Agent records in database
│       ├── data_update.py      # Updates Agent status
│       ├── load_config.py      # Configuration loader utility
│       └── __init__.py         # Python package initialization
├── docs/
│   └── index.md               # This documentation
├── cloudbuild.yaml            # GCP Cloud Build configuration
├── mkdocs.yaml                 # Documentation configuration
├── requirements.txt           # Python dependencies
├── catalog-info.yaml          # Backstage entity configuration
└── README.md                  # Project readme
```

## Usage

### Creating a Agent

The Agent is automatically created when the Cloud Build pipeline runs:

```bash
python src/data_create.py create_Agent 1 --sensitive_information 1
```

### Updating Agent Status

Update the Agent status after deployment:

```bash
python src/data_update.py update_Agent <base_id> <arn> <url> <version> <status>
```

## API Integration

This Agent integrates with the NeuroAI API Gateway:
- **Create Endpoint**: `/Agent/`
- **Update Endpoint**: `/updateAgent/`


## Deployment

This Agent is deployed using GCP Cloud Build. The deployment process:

1. Installs Python dependencies
2. Creates a database record for the Agent
3. Deploys the Agent infrastructure
4. Updates the database with completion status

## Monitoring

Monitor your Agent through:
- GCP Cloud Console
- NeuroAI Dashboard
- API response logs

## Support

For support and questions:
- Check the NeuroAI documentation
- Contact the platform team
- Review the API logs for troubleshooting
