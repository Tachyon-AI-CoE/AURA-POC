"""
Convert agents-config.json (== agent_input.json written by the orchestrator) into:

  1. agent-config.yaml          — simple format consumed by config.py / agent.py
  2. root-agent.yaml            — ADK multi-YAML root agent
  3. sub_agents/<name>.yaml     — one file per sub-agent (all nesting levels, flat)

Run location: Cloud Build step 2, dir = <agent_folder>/src/config/
Input file  : agents-config.json  (copied here from config/ in step 1)
"""

import json
import os
from typing import Any, Dict, List, Optional

import yaml

from utils.log_helper import setup_logging

logger = setup_logging()

# ── agent_type (JSON) → agent_class (ADK YAML) ───────────────────────────────
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
    resolved = _AGENT_CLASS_MAP.get(agent_type) or _AGENT_CLASS_MAP.get(agent_type.lower())
    if not resolved:
        raise ValueError(
            f"Unknown agent_type '{agent_type}'. Supported: {list(_AGENT_CLASS_MAP)}"
        )
    return resolved


# ── Custom YAML dumper ────────────────────────────────────────────────────────

class _ADKDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)

    def represent_str(self, data):
        if "\n" in data:
            return self.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return self.represent_scalar("tag:yaml.org,2002:str", data)


_ADKDumper.add_representer(
    dict,
    lambda dumper, data: dumper.represent_mapping("tag:yaml.org,2002:map", data.items()),
)
_ADKDumper.add_representer(str, _ADKDumper.represent_str)


def _write_yaml(data: Dict[str, Any], path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(
            data, f,
            Dumper=_ADKDumper,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            indent=2,
            width=float("inf"),
        )
    logger.info(f"  ✅ Written: {path}")


# ── ADK YAML builder ──────────────────────────────────────────────────────────

def _build_adk_yaml(agent: Dict[str, Any]) -> Dict[str, Any]:
    """Build the ADK YAML dict for one agent node."""
    agent_class = _resolve_agent_class(agent.get("agent_type", "LLMAgent"))
    out: Dict[str, Any] = {"agent_class": agent_class}

    if agent_class == "LlmAgent" and agent.get("model"):
        out["model"] = agent["model"]

    out["name"] = agent.get("name", "")

    if agent.get("description"):
        out["description"] = agent["description"]

    if agent_class == "LlmAgent" and agent.get("instruction"):
        out["instruction"] = agent["instruction"]

    if agent_class == "LlmAgent":
        gcc = agent.get("generate_content_config") or {}
        out["generate_content_config"] = {
            "temperature":       gcc.get("temperature", 0.2),
            "max_output_tokens": gcc.get("max_output_tokens", 2000),
        }

    if agent_class == "LoopAgent" and agent.get("max_iterations"):
        out["max_iterations"] = agent["max_iterations"]

    out["input_schema"]  = agent.get("input_schema", None)
    out["output_schema"] = agent.get("output_schema", None)
    out["output_key"]    = agent.get("output_key", None)

    if agent_class == "LlmAgent":
        out["include_contents"] = agent.get("include_contents", None)
        out["planner"]          = agent.get("planner", None)

    out["tools"] = {"rag": None, "mcp": None, "openapi_spec": None, "agent_tool": None}
    out["agent_skills"] = None

    sub_agents = agent.get("sub_agents") or []
    if sub_agents:
        out["sub_agents"] = [
            {"config_path": f"sub_agents/{sa['name']}.yaml"} for sa in sub_agents
        ]

    return out


def _collect_all_agents(
    agents: List[Dict[str, Any]],
    collected: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Flatten the agent tree into a single list (all nesting levels)."""
    if collected is None:
        collected = []
    for agent in agents:
        collected.append(agent)
        _collect_all_agents(agent.get("sub_agents") or [], collected)
    return collected


# ── Format 1: simple agent-config.yaml (consumed by config.py / agent.py) ────

def _generate_simple_yaml(root_agent: Dict[str, Any], output_path: str) -> None:
    """Produce the single-file agent-config.yaml that config.py reads."""
    config = {
        "root_agent": {
            "name":        root_agent.get("name", ""),
            "model":       root_agent.get("model", ""),
            "description": root_agent.get("description", ""),
            "instruction": root_agent.get("instruction", ""),
        }
    }
    gcc = root_agent.get("generate_content_config")
    if gcc:
        config["root_agent"]["generate_content_config"] = {
            "temperature":       gcc.get("temperature", 0.28),
            "max_output_tokens": gcc.get("max_output_tokens", 1000),
            "top_p":             gcc.get("top_p", 0.95),
        }
    _write_yaml(config, output_path)


# ── Format 2: ADK multi-YAML (root-agent.yaml + sub_agents/*.yaml) ───────────

def _generate_adk_yaml(
    root_agent: Dict[str, Any],
    top_level_agents: List[Dict[str, Any]],
    config_dir: str,
) -> None:
    """Produce root-agent.yaml and sub_agents/<name>.yaml in ADK format."""
    # Root agent — its sub_agents list points to the top-level agents
    root_with_subs = dict(root_agent)
    root_with_subs["sub_agents"] = top_level_agents
    _write_yaml(_build_adk_yaml(root_with_subs), os.path.join(config_dir, "root-agent.yaml"))

    # All agents at every level, flattened
    all_sub = _collect_all_agents(top_level_agents)
    sub_dir = os.path.join(config_dir, "sub_agents")
    os.makedirs(sub_dir, exist_ok=True)
    for agent in all_sub:
        _write_yaml(
            _build_adk_yaml(agent),
            os.path.join(sub_dir, f"{agent['name']}.yaml"),
        )
    logger.info(
        f"✅ ADK YAML: 1 root-agent.yaml + {len(all_sub)} file(s) in sub_agents/"
    )


# ── Public entry point ────────────────────────────────────────────────────────

def generate_agent_config(
    json_path: str = "agents-config.json",
    output_dir: str = ".",
) -> None:
    """
    Read agents-config.json and write:
      • agent-config.yaml   (simple format — agent.py / config.py)
      • root-agent.yaml     (ADK multi-YAML root)
      • sub_agents/*.yaml   (ADK multi-YAML sub-agents)
    """
    logger.info(f"🚀 Generating config files from: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    root_agent = data.get("root_agent")
    if not root_agent:
        raise ValueError("'root_agent' key missing from agents-config.json")

    top_level_agents = data.get("agents") or []

    # Format 1 — simple YAML (keeps agent.py working as-is)
    _generate_simple_yaml(root_agent, os.path.join(output_dir, "agent-config.yaml"))

    # Format 2 — ADK multi-YAML
    _generate_adk_yaml(root_agent, top_level_agents, output_dir)

    logger.info("✅ Agent configuration generation completed successfully!")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json-path",
        default=None,
        help="Path to agents-config.json (default: agents-config.json in this script's dir)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to write generated YAML files (default: same dir as this script)",
    )
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path  = os.path.abspath(args.json_path)  if args.json_path  else os.path.join(script_dir, "agents-config.json")
    output_dir = os.path.abspath(args.output_dir) if args.output_dir else script_dir

    generate_agent_config(json_path=json_path, output_dir=output_dir)
