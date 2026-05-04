# GCP Multi-Agent Workflow with New Agents

## Overview

This template provides a comprehensive framework for deploying multi-agent workflows on Google Cloud Platform (GCP). It enables the creation of sophisticated AI agent orchestrations where multiple specialized agents collaborate to solve complex tasks and workflows.

## 🚀 Features

- **Multi-Agent Orchestration**: Deploy and manage multiple AI agents working together
- **Root Agent Management**: Central coordinator agent that manages workflow execution
- **GCP Integration**: Native integration with Google Cloud Platform services
- **Configurable Agents**: Dynamic agent configuration with customizable parameters
- **Guardrails Support**: Built-in safety and compliance mechanisms
- **Temperature Control**: Fine-tune agent creativity and determinism
- **Lifecycle Management**: Support for development, staging, and production environments

## 🏗️ Architecture

### Root Agent
- **Display Name**: `${{ values.root_agent_display_name }}`
- **Description**: ${{ values.root_agent_description }}
- **Model**: `${{ values.root_agent_model_id.label }}`
- **Class**: `${{ values.root_agent_class }}`

### Configuration Parameters
- **Temperature**: `${{ values.temperature }}` - Controls randomness (0.0 = deterministic, 2.0 = creative)
- **Top P**: `${{ values.top_p }}` - Controls output diversity
- **Top K**: `${{ values.top_k }}` - Limits token selection
- **Guardrails**: {% if values.enable_guardrail %}`Enabled - ${{ values.guardrail_name.label }}`{% else %}`Disabled`{% endif %}

## 📋 Instructions

### Global Instruction
```
${{ values.root_agent_instruction }}
```

### Detailed Implementation
```
${{ values.second_instruction }}
```

## 🤖 Agent Configuration

{% if values.enable_agents %}
This workflow includes the following specialized agents:

{% for agent in values.agents | dump %}
### {{ agent.agent_display_name }}
- **Description**: {{ agent.agent_description }}
- **Model**: {{ agent.agent_model_id.label }}
- **Class**: {{ agent.agent_class }}
- **Temperature**: {{ agent.agent_temperature }}
- **Top P**: {{ agent.agent_top_p }}
- **Top K**: {{ agent.agent_top_k }}

**Instruction**: 
```
{{ agent.agent_instruction }}
```

**Detailed Implementation**:
```
{{ agent.agent_second_instruction }}
```

---
{% endfor %}
{% else %}
No additional agents configured. This workflow uses only the root agent.
{% endif %}

## 🛠️ Setup Instructions

### Prerequisites
- GCP Account with appropriate permissions
- Staging bucket configured: `${{ values.staging_bucket }}`
- Region: `${{ values.region.label }}`

### Deployment Steps

1. **Clone this repository**
   ```bash
   git clone <repository-url>
   cd ${{ values.root_agent_display_name | lower | replace(" ", "-") }}
   ```

2. **Configure Environment**
   ```bash
   # Set up GCP credentials
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Deploy the Workflow**
   ```bash
   # Use Cloud Build for deployment
   gcloud builds submit --config=cloudbuild.yaml
   ```

## 📁 Project Structure

```
.
├── catalog-info.yaml           # Backstage catalog configuration
├── cloudbuild.yaml            # Cloud Build configuration
├── docs/                      # Documentation
│   └── index.md              # This file
└── python/                   # Python implementation
    ├── config/               # Configuration files
    │   ├── agents.json       # Agent definitions
    │   └── root-agent-config.yaml  # Root agent configuration
    └── src/                  # Source code
```

## 🔧 Configuration Files

### Root Agent Configuration (`config/root-agent-config.yaml`)
Contains the main configuration for the root agent including:
- Agent parameters
- Model settings
- Instruction sets
- Guardrail configurations

### Agents Configuration (`config/agents.json`)
Defines all additional agents in the workflow:
- Agent specifications
- Individual parameters
- Specialized instructions

## 🚦 Lifecycle Management

**Current Lifecycle**: `${{ values.lifecycle }}`

- **Development**: For testing and experimentation
- **Staging**: For integration testing and validation
- **Production**: For live deployment and operations

## 📊 Monitoring and Observability

The workflow includes built-in monitoring capabilities:
- Agent performance metrics
- Workflow execution tracking
- Error handling and logging
- Resource utilization monitoring

## 🛡️ Security and Compliance

{% if values.enable_guardrail %}
### Guardrails
This workflow uses the **${{ values.guardrail_name.label }}** guardrail to ensure:
- Content safety and compliance
- Output validation
- Behavioral constraints
- Risk mitigation
{% else %}
### Security Notice
⚠️ **Guardrails are disabled** for this workflow. Consider enabling guardrails for production deployments to ensure content safety and compliance.
{% endif %}

## 🔗 API Integration

This component provides APIs for:
- Agent interaction
- Workflow orchestration
- Status monitoring
- Configuration management

**API Reference**: See the OpenAPI definition in the catalog.

## 📞 Support and Maintenance

- **Owner**: ${{ values.owner }}
- **Lifecycle**: ${{ values.lifecycle }}
- **Tags**: gcp, multiagent, orchestrator

## 🚀 Getting Started

1. Review the configuration parameters above
2. Ensure your GCP environment meets the prerequisites
3. Follow the deployment steps
4. Monitor the workflow execution through the provided dashboards
5. Iterate and improve based on performance metrics

## 📝 Notes

- This workflow is generated from the GCP Multi-Agent Workflow template
- All agents are configured with optimized parameters for collaborative execution
- The root agent serves as the primary orchestrator for the entire workflow
- Configuration can be modified through the respective YAML and JSON files

---

*Generated with Neuro® AI Engineering Platform - Multi-Agent Workflow Template*