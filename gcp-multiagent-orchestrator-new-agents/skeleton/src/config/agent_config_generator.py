"""
Agent Configuration Generator
-------------------------------
Reads a single unified agents-config.json and generates:

  config/
    agent-config.yaml       ← merged single YAML (for deployment via agent_engine_deploy.py)
                               stashed before GitHub push, restored to src/config/ for deploy
    root-agent.yaml         ← ADK format root agent (pushed to GitHub)
    sub_agents/
      <agent_name>.yaml     ← one per agent, ALL nesting levels flat (pushed to GitHub)

Standard field names (new — no legacy aliases):
  JSON field                  → YAML field
  ──────────────────────────────────────────
  agent_type                  → agent_class
  model                       → model
  generate_content_config     → generate_content_config
  name (spaces allowed)       → sanitised to snake_case in filenames

custom_agents[] is merged with agents[] — treated identically.

CLI usage (called by local_deploy.py):
  uv run agent_config_generator.py --json-path <path> --output-dir <dir>
"""

import argparse
import json
import logging
import os
from typing import Any, Dict, List, Optional

import yaml

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(asctime)s - %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Field name mapping: JSON standard → ADK YAML ─────────────────────────────
# agent_type  → agent_class  (ADK uses agent_class)
# model       → model        (same)
# generate_content_config → generate_content_config (same)
_AGENT_CLASS_MAP = {
    "LLMAgent":        "LlmAgent",
    "LlmAgent":        "LlmAgent",
    "llmagent":        "LlmAgent",
    "LoopAgent":       "LoopAgent",
    "loopagent":       "LoopAgent",
    "ParallelAgent":   "ParallelAgent",
    "parallelagent":   "ParallelAgent",
    "SequentialAgent": "SequentialAgent",
    "sequentialagent": "SequentialAgent",
}


def _resolve_agent_class(agent_type: str) -> str:
    resolved = _AGENT_CLASS_MAP.get(agent_type) or _AGENT_CLASS_MAP.get(
        agent_type.lower(), agent_type
    )
    return resolved


def _sanitise_name(name: str) -> str:
    """Convert agent name to safe snake_case for use as a filename."""
    return name.strip().lower().replace(" ", "_").replace("-", "_")


# ── YAML custom dumper ────────────────────────────────────────────────────────

class _Dumper(yaml.SafeDumper):
    """Preserves insertion order, no anchors, block scalar for multiline strings."""

    def ignore_aliases(self, data):
        return True

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)

    def represent_str(self, data):
        if "\n" in data:
            return self.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return self.represent_scalar("tag:yaml.org,2002:str", data)


_Dumper.add_representer(
    dict,
    lambda d, data: d.represent_mapping("tag:yaml.org,2002:map", data.items()),
)
_Dumper.add_representer(str, _Dumper.represent_str)


def _write_yaml(data: Dict[str, Any], path: str) -> None:
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(
            data, f,
            Dumper=_Dumper,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            indent=2,
            width=float("inf"),
        )
    logger.info(f"  ✅ Written: {path}")


# ── RAG + MCP transform (preserved from original) ────────────────────────────

def _transform_rag(tools: Dict[str, Any]) -> List[Dict[str, Any]]:
    if "rag" not in tools:
        return []
    rag_config = tools.get("rag", [])
    if not isinstance(rag_config, list):
        rag_config = [rag_config]
    transformed = []
    for item in rag_config:
        entry: Dict[str, Any] = {}
        rag_details = item.get("rag_details", {})
        value_obj = rag_details.get("value", {}) if isinstance(rag_details, dict) else {}
        name        = value_obj.get("datasetname", item.get("name", ""))
        corpus_id   = value_obj.get("vectorizeddatasetbaseid", item.get("resource_id", ""))
        description = value_obj.get("description", "")
        entry["name"] = name
        if description:
            entry["description"] = description
        entry["config"] = {}
        if corpus_id:
            entry["config"]["rag_resources"] = [{"rag_resource": corpus_id}]
        else:
            entry["config"]["rag_resources"] = []
        for opt in ("vector_distance_threshold", "similarity_top_k"):
            if opt in item:
                entry["config"][opt] = item[opt]
        transformed.append(entry)
    return transformed


def _transform_mcp(tools: Dict[str, Any]) -> List[Dict[str, Any]]:
    if "mcp" not in tools:
        return []
    mcp_config = tools.get("mcp", {})
    if isinstance(mcp_config, dict) and "mcp_servers" in mcp_config:
        result = []
        for srv in mcp_config.get("mcp_servers", []):
            if srv:
                result.append({
                    "name": srv,
                    "description": f"MCP server: {srv}",
                    "tool_filter": [],
                    "config": {"server_url": ""},
                })
        return result
    if isinstance(mcp_config, list):
        return mcp_config
    return []


# ── Agent → legacy YAML dict (for agent-config.yaml) ─────────────────────────

def _transform_agent_legacy(agent: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform one agent for the legacy agent-config.yaml format.
    This is what agent_engine_deploy.py reads to build and deploy the agent.
    """
    out: Dict[str, Any] = {}

    if "name" in agent:
        out["name"] = agent["name"]

    # Fields excluded from direct copy (handled manually below)
    exclude = {
        "model", "tools", "sub_agents", "name",
        "show_advanced_options", "show_sub_agent_advanced",
        "agent_type",
    }

    # Copy all simple fields
    for key, value in agent.items():
        if key not in exclude:
            out[key] = value

    # agent_type → agent_class in output
    if "agent_type" in agent:
        out["agent_class"] = _resolve_agent_class(agent["agent_type"])

    # model → model in output
    model = agent.get("model", "")
    if isinstance(model, dict):
        out["model"] = model.get("value", "gemini-2.0-flash-001")
    else:
        out["model"] = model or "gemini-2.0-flash-001"

    # Tools
    tools = agent.get("tools") or {}
    if tools:
        tools_out: Dict[str, Any] = {}
        if "enabled_tools" in tools:
            tools_out["enabled_tools"] = tools["enabled_tools"]
        rag = _transform_rag(tools)
        if rag:
            tools_out["rag"] = rag
        mcp = _transform_mcp(tools)
        if mcp:
            tools_out["mcp"] = mcp
        if tools_out:
            out["tools"] = tools_out

    # Recurse into sub_agents
    if agent.get("sub_agents"):
        out["sub_agents"] = [
            _transform_agent_legacy(sa) for sa in agent["sub_agents"]
        ]

    return out


# ── Agent → ADK YAML dict (for root-agent.yaml / sub_agents/*.yaml) ──────────

def _build_adk_yaml(agent: Dict[str, Any], sub_agents_list: List[str]) -> Dict[str, Any]:
    """
    Build one agent YAML in ADK format.
    sub_agents_list = list of direct child agent names (not recursive — flat folder).
    """
    out: Dict[str, Any] = {}

    # agent_class (mapped from agent_type)
    out["agent_class"] = _resolve_agent_class(agent.get("agent_type", "LLMAgent"))

    # model — only for LlmAgent
    if out["agent_class"] == "LlmAgent" and agent.get("model"):
        out["model"] = agent["model"]

    # name (sanitised)
    out["name"] = _sanitise_name(agent.get("name", ""))

    # description
    if agent.get("description"):
        out["description"] = agent["description"]

    # instruction — only for LlmAgent
    if out["agent_class"] == "LlmAgent" and agent.get("instruction"):
        out["instruction"] = agent["instruction"]

    # generate_content_config — only for LlmAgent
    if out["agent_class"] == "LlmAgent":
        gcc = agent.get("generate_content_config") or {}
        out["generate_content_config"] = {
            "temperature":       gcc.get("temperature", 0.2),
            "max_output_tokens": gcc.get("max_output_tokens", 2000),
        }

    # max_iterations — only for LoopAgent
    if out["agent_class"] == "LoopAgent" and agent.get("max_iterations"):
        out["max_iterations"] = agent["max_iterations"]

    # Null fields
    out["input_schema"]  = agent.get("input_schema", None)
    out["output_schema"] = agent.get("output_schema", None)
    out["output_key"]    = agent.get("output_key", None)

    if out["agent_class"] == "LlmAgent":
        out["include_contents"] = agent.get("include_contents", None)
        out["planner"]          = agent.get("planner", None)

    # Tools
    out["tools"] = {
        "rag":         None,
        "mcp":         None,
        "openapi_spec": None,
        "agent_tool":  None,
    }

    # Agent skills
    out["agent_skills"] = None

    # sub_agents — config_path references (flat sub_agents/ folder)
    if sub_agents_list:
        out["sub_agents"] = [
            {"config_path": f"sub_agents/{_sanitise_name(n)}.yaml"}
            for n in sub_agents_list
        ]

    return out


# ── Collect all agents flat ───────────────────────────────────────────────────

def _collect_all_agents(
    agents: List[Dict[str, Any]],
    collected: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Walk the full agent tree and return every agent in a flat list."""
    if collected is None:
        collected = []
    for agent in agents:
        collected.append(agent)
        sub = agent.get("sub_agents") or []
        if sub:
            _collect_all_agents(sub, collected)
    return collected


# ── Legacy agent-config.yaml builder ─────────────────────────────────────────

def _build_legacy_config(
    root_agent: Dict[str, Any],
    all_agents: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build the legacy agent-config.yaml structure that agent_engine_deploy.py reads.
    Format matches the original merged YAML the skeleton expected.
    """
    merged: Dict[str, Any] = {}

    # Root agent section
    root_out = _transform_agent_legacy(root_agent)
    root_out["sub_agents"] = [
        _transform_agent_legacy(a) if not a.get("sub_agents")
        else _transform_agent_legacy(a)
        for a in all_agents
    ]
    merged["root_agent"] = root_out
    merged["agents"] = [_transform_agent_legacy(a) for a in all_agents]

    return merged


# ── Main generation logic ─────────────────────────────────────────────────────

def generate(json_path: str, output_dir: str) -> bool:
    """
    Read agents-config.json and write all output files into output_dir.

    Returns True on success.
    """
    logger.info(f"🚀 Generating config files from: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Validate
    if "root_agent" not in data:
        raise ValueError("agents-config.json missing required key: 'root_agent'")

    root_agent   = data["root_agent"]
    agents       = data.get("agents") or []
    custom_agents = data.get("custom_agents") or []
    all_agents   = agents + custom_agents   # custom_agents treated identically

    if custom_agents:
        logger.info(f"  Merging {len(custom_agents)} custom_agents with agents list")

    os.makedirs(output_dir, exist_ok=True)
    sub_agents_dir = os.path.join(output_dir, "sub_agents")
    os.makedirs(sub_agents_dir, exist_ok=True)

    # ── 1. agent-config.yaml (legacy — for deployment) ────────────────────────
    legacy_config = _build_legacy_config(root_agent, all_agents)
    _write_yaml(legacy_config, os.path.join(output_dir, "agent-config.yaml"))

    # ── 2. root-agent.yaml (ADK format — for GitHub) ──────────────────────────
    root_child_names = [a.get("name", "") for a in all_agents]
    root_adk = _build_adk_yaml(root_agent, root_child_names)
    _write_yaml(root_adk, os.path.join(output_dir, "root-agent.yaml"))

    # ── 3. sub_agents/*.yaml (ADK format — for GitHub) ────────────────────────
    all_flat = _collect_all_agents(all_agents)
    for agent in all_flat:
        child_names = [sa.get("name", "") for sa in (agent.get("sub_agents") or [])]
        agent_adk   = _build_adk_yaml(agent, child_names)
        safe_name   = _sanitise_name(agent.get("name", "agent"))
        _write_yaml(agent_adk, os.path.join(sub_agents_dir, f"{safe_name}.yaml"))

    total_sub = len(all_flat)
    logger.info(
        f"✅ ADK YAML: 1 root-agent.yaml + {total_sub} file(s) in sub_agents/"
    )
    logger.info("✅ Agent configuration generation completed successfully!")
    return True


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate agent YAML config files from a unified agents-config.json"
    )
    parser.add_argument(
        "--json-path",
        required=True,
        help="Path to agents-config.json",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where YAML files will be written (config/ folder)",
    )
    args = parser.parse_args()

    generate(
        json_path=os.path.abspath(args.json_path),
        output_dir=os.path.abspath(args.output_dir),
    )