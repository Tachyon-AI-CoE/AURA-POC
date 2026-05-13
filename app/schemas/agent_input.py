"""
Agent input schema — matches the structure of inputs/*.json.

Top-level AgentInput uses extra="forbid" to reject unknown keys at the API
boundary. Nested agent models use extra="allow" so that agent-specific
extension fields (e.g. workflow, rag_enabled) are preserved and written
through to agents-config.json without modification.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GenerateContentConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    temperature: float = 0.0
    max_output_tokens: int = 2048
    top_p: float | None = None
    top_k: int | None = None


class Tools(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled_tools: list[Any] = Field(default_factory=list)
    rag: list[Any] = Field(default_factory=list)
    mcp: list[Any] = Field(default_factory=list)


class SubAgent(BaseModel):
    """Nested agent (inside a LoopAgent sub_agents list)."""

    model_config = ConfigDict(extra="allow")

    name: str
    agent_type: str
    description: str
    model: str | None = None
    instruction: str | None = None
    generate_content_config: GenerateContentConfig | None = None
    tools: Tools | None = None
    output_key: str | None = None
    input_schema: Any | None = None
    output_schema: Any | None = None
    include_contents: str | None = None
    planner: Any | None = None
    max_iterations: int | None = None


class Agent(BaseModel):
    """Top-level agent entry in the 'agents' array."""

    model_config = ConfigDict(extra="allow")

    name: str
    agent_type: str
    description: str
    model: str | None = None
    instruction: str | None = None
    generate_content_config: GenerateContentConfig | None = None
    tools: Tools | None = None
    output_key: str | None = None
    input_schema: Any | None = None
    output_schema: Any | None = None
    include_contents: str | None = None
    planner: Any | None = None
    max_iterations: int | None = None
    sub_agents: list[SubAgent] = Field(default_factory=list)


class RootAgent(BaseModel):
    """Root/orchestrator agent definition."""

    model_config = ConfigDict(extra="allow")

    name: str
    agent_type: str
    description: str
    multiagent: bool = False
    model: str | None = None
    instruction: str | None = None
    generate_content_config: GenerateContentConfig | None = None
    tools: Tools | None = None
    output_key: str | None = None
    input_schema: Any | None = None
    output_schema: Any | None = None
    include_contents: str | None = None
    planner: Any | None = None


class AgentInput(BaseModel):
    """Top-level request body for POST /scaffold. Strict: no unknown keys allowed."""

    model_config = ConfigDict(extra="forbid")

    scaffold_type: str
    repo_name: str
    description: str = "Component created via AURA platform"
    root_agent: RootAgent
    agents: list[Agent] = Field(default_factory=list)
    custom_agents: list[Any] = Field(default_factory=list)
