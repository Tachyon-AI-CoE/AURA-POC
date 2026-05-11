"""MultiAgent Builder for constructing multi-agent systems from YAML configuration."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from google.adk.agents import LlmAgent, LoopAgent, ParallelAgent, SequentialAgent

from utils.log_helper import setup_logging
from root_agent.sub_agents.llm_agent import LlmAgentBuilder
from root_agent.sub_agents.loop_agent import LoopAgentBuilder
from root_agent.sub_agents.parallel_agent import ParallelAgentBuilder
from root_agent.sub_agents.sequential_agent import SequentialAgentBuilder


logger = setup_logging()


class MultiAgentBuilder:
    """Builder for constructing multi-agent systems from YAML configuration."""

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "config",
                "agent-config.yaml",
            )

        self.config_path = Path(config_path)
        self.config = self._load_config()

        logger.info(f"✅ Initialized MultiAgentBuilder with config: {self.config_path}")

    def _load_config(self) -> Dict[str, Any]:
        try:
            logger.debug(f"📖 Loading configuration from: {self.config_path}")

            with open(self.config_path, "r", encoding="utf-8") as file:
                config = yaml.safe_load(file)

            if not config:
                raise ValueError("Configuration file is empty or invalid")

            logger.info("✅ Configuration loaded successfully")
            return config

        except FileNotFoundError as e:
            logger.error(f"❌ Configuration file not found: {self.config_path}")
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}"
            ) from e

        except yaml.YAMLError as e:
            logger.error(f"❌ Invalid YAML configuration: {e}")
            raise yaml.YAMLError(f"Invalid YAML configuration: {e}") from e

    def _build_llm_agent(self, agent_config: Dict[str, Any]) -> LlmAgent:
        agent_name = agent_config.get("name", "unnamed_llm_agent")
        logger.debug(f"🔧 Building LLM agent: {agent_name}")

        try:
            builder = LlmAgentBuilder()
            builder.from_yaml_config(agent_config, self.config)

            sub_agents_config = agent_config.get("sub_agents", [])
            if sub_agents_config:
                logger.debug(
                    f"Building {len(sub_agents_config)} sub-agents for {agent_name}"
                )
                sub_agents = self._build_sub_agents(sub_agents_config)
                builder.set_sub_agents(sub_agents)

            agent = builder.apply_callbacks().build()
            logger.info(f"✅ Successfully built LLM agent: {agent_name}")
            return agent

        except Exception as e:
            logger.error(f"❌ Failed to build LLM agent '{agent_name}': {e}")
            raise

    def _build_sub_agents(
        self, sub_agents_config: List[Dict[str, Any]]
    ) -> List[Union[LlmAgent, LoopAgent, SequentialAgent, ParallelAgent]]:
        if not sub_agents_config:
            logger.debug("No sub-agents to build")
            return []

        logger.info(f"🔧 Building {len(sub_agents_config)} sub-agents")
        sub_agents = []

        for i, sub_agent_config in enumerate(sub_agents_config):
            agent_class = sub_agent_config.get("agent_class", "LLMAgent")
            agent_name = sub_agent_config.get("name", f"unnamed_sub_agent_{i}")

            try:
                logger.debug(
                    f"Building sub-agent {i+1}/{len(sub_agents_config)}: {agent_name} ({agent_class})"
                )

                sub_agent = self.build_agent(sub_agent_config)
                sub_agents.append(sub_agent)

                logger.info(f"✅ Successfully built sub-agent: {agent_name}")

            except Exception as e:
                logger.warning(f"⚠️ Failed to build sub-agent '{agent_name}': {e}")

        logger.info(
            f"✅ Successfully built {len(sub_agents)} out of {len(sub_agents_config)} sub-agents"
        )
        return sub_agents

    def _build_loop_agent(self, agent_config: Dict[str, Any]) -> LoopAgent:
        name = agent_config.get("name", "unnamed_loop_agent")
        description = agent_config.get("description", "")
        max_iterations = agent_config.get("max_iterations", 5)
        sub_agents_config = agent_config.get("sub_agents", [])

        logger.debug(
            f"🔧 Building Loop agent: {name} (max_iterations: {max_iterations})"
        )

        try:
            builder = LoopAgentBuilder()
            builder.set_name(name)
            builder.set_description(description)
            builder.set_max_iterations(max_iterations)

            if sub_agents_config:
                logger.debug(
                    f"Building {len(sub_agents_config)} sub-agents for Loop agent: {name}"
                )
                sub_agents = self._build_sub_agents(sub_agents_config)
                builder.set_sub_agents(sub_agents)

            agent = builder.build()
            logger.info(f"✅ Successfully built Loop agent: {name}")
            return agent

        except Exception as e:
            logger.error(f"❌ Failed to build Loop agent '{name}': {e}")
            raise

    def _build_sequential_agent(self, agent_config: Dict[str, Any]) -> SequentialAgent:
        name = agent_config.get("name", "unnamed_sequential_agent")
        description = agent_config.get("description", "")
        sub_agents_config = agent_config.get("sub_agents", [])

        logger.debug(f"🔧 Building Sequential agent: {name}")

        try:
            builder = SequentialAgentBuilder()
            builder.set_name(name)
            builder.set_description(description)

            if sub_agents_config:
                logger.debug(
                    f"Building {len(sub_agents_config)} sub-agents for Sequential agent: {name}"
                )
                sub_agents = self._build_sub_agents(sub_agents_config)
                builder.set_sub_agents(sub_agents)

            agent = builder.build()
            logger.info(f"✅ Successfully built Sequential agent: {name}")
            return agent

        except Exception as e:
            logger.error(f"❌ Failed to build Sequential agent '{name}': {e}")
            raise

    def _build_parallel_agent(self, agent_config: Dict[str, Any]) -> ParallelAgent:
        name = agent_config.get("name", "unnamed_parallel_agent")
        description = agent_config.get("description", "")
        sub_agents_config = agent_config.get("sub_agents", [])

        logger.debug(f"🔧 Building Parallel agent: {name}")

        try:
            builder = ParallelAgentBuilder()
            builder.set_name(name)
            builder.set_description(description)

            if sub_agents_config:
                logger.debug(
                    f"Building {len(sub_agents_config)} sub-agents for Parallel agent: {name}"
                )
                sub_agents = self._build_sub_agents(sub_agents_config)
                builder.set_sub_agents(sub_agents)

            agent = builder.build()
            logger.info(f"✅ Successfully built Parallel agent: {name}")
            return agent

        except Exception as e:
            logger.error(f"❌ Failed to build Parallel agent '{name}': {e}")
            raise

    def build_agent(
        self, agent_config: Dict[str, Any]
    ) -> Union[LlmAgent, LoopAgent, SequentialAgent, ParallelAgent]:
        """Build an agent from configuration based on agent_class."""
        if not agent_config:
            raise ValueError("Agent configuration cannot be empty")

        agent_class = agent_config.get("agent_class", "LLMAgent")
        agent_name = agent_config.get("name", "unnamed_agent")

        logger.debug(f"🔧 Building agent '{agent_name}' of type '{agent_class}'")

        agent_builders = {
            "LLMAgent":        self._build_llm_agent,
            "LlmAgent":        self._build_llm_agent,
            "LoopAgent":       self._build_loop_agent,
            "SequentialAgent": self._build_sequential_agent,
            "ParallelAgent":   self._build_parallel_agent,
        }

        builder_method = agent_builders.get(agent_class)
        if not builder_method:
            supported_classes = list(agent_builders.keys())
            error_msg = f"Unsupported agent class: '{agent_class}'. Supported classes: {supported_classes}"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)

        try:
            return builder_method(agent_config)
        except Exception as e:
            logger.error(
                f"❌ Failed to build agent '{agent_name}' of type '{agent_class}': {e}"
            )
            raise

    def build_agents_from_config(
        self,
    ) -> List[Union[LlmAgent, LoopAgent, SequentialAgent, ParallelAgent]]:
        agents_config = self.config.get("agents", [])

        if not agents_config:
            logger.info("ℹ️ No agents found in configuration")
            return []

        logger.info(f"🔧 Building {len(agents_config)} agents from configuration")
        agents = []

        for i, agent_config in enumerate(agents_config):
            agent_name = agent_config.get("name", f"unnamed_agent_{i}")
            agent_class = agent_config.get("agent_class", "LLMAgent")

            try:
                logger.debug(f"Building agent {i+1}/{len(agents_config)}: {agent_name}")

                agent = self.build_agent(agent_config)
                agents.append(agent)

                logger.info(
                    f"✅ Successfully built agent: {agent.name} ({agent_class})"
                )

            except Exception as e:
                logger.warning(f"⚠️ Failed to build agent '{agent_name}': {e}")

        logger.info(
            f"✅ Successfully built {len(agents)} out of {len(agents_config)} agents"
        )
        return agents

    def build_root_agent(self, include_sub_agents: bool = True) -> LlmAgent:
        """Build the root agent from configuration."""
        logger.info("🔧 Building root agent from configuration")

        root_config = self.config.get("root_agent", {})
        if not root_config:
            error_msg = "No root_agent configuration found"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)

        agent_class = root_config.get("agent_class", "LLMAgent")
        agent_name = (
            root_config.get("agent_display_name")
            or root_config.get("name", "root_agent")
        )
        model_id = root_config.get("model", root_config.get("model_id", "gemini-2.0-flash-001"))
        description = root_config.get("description", "")
        instruction = root_config.get("instruction", "")
        global_instruction = root_config.get("global_instruction", "")
        llm_config = root_config.get("llm_config", {})
        multiagent = root_config.get("multiagent", False)
        output_key = root_config.get("output_key", None)

        logger.debug(
            f"Root agent configuration: name='{agent_name}', model='{model_id}', multiagent={multiagent}"
        )

        final_instruction = self._process_instructions(instruction, global_instruction)

        root_agent_config = {
            "name": agent_name,
            "model": model_id,
            "description": description,
            "instruction": final_instruction,
            "output_key": output_key,
            "llm_config": llm_config,
        }

        try:
            builder = LlmAgentBuilder()
            builder.from_yaml_config(root_agent_config, self.config)

            if multiagent and include_sub_agents:
                logger.info("🔧 Building sub-agents for root agent")
                sub_agents = self.build_agents_from_config()
                builder.set_sub_agents(sub_agents)

            if agent_class != "LLMAgent":
                logger.warning(
                    f"Root agent class is '{agent_class}', but only 'LLMAgent' is supported. Using LLMAgent."
                )

            root_agent = builder.build()

            if global_instruction:
                setattr(root_agent, "global_instruction", global_instruction)

            sub_agent_count = (
                len(root_agent.sub_agents)
                if hasattr(root_agent, "sub_agents") and root_agent.sub_agents
                else 0
            )

            logger.info(
                f"✅ Successfully built root agent '{agent_name}' with {sub_agent_count} sub-agents"
            )
            return root_agent

        except Exception as e:
            logger.error(f"❌ Failed to build root agent '{agent_name}': {e}")
            raise

    def _process_instructions(self, instruction: Any, global_instruction: Any) -> str:
        instruction_parts = []

        if global_instruction:
            if isinstance(global_instruction, list):
                global_instruction_text = "\n".join(
                    f"- {instr}" for instr in global_instruction
                )
            else:
                global_instruction_text = str(global_instruction)
            instruction_parts.append(f"GLOBAL INSTRUCTIONS:\n{global_instruction_text}")

        if instruction:
            if isinstance(instruction, list):
                instruction_text = "\n".join(f"- {instr}" for instr in instruction)
            else:
                instruction_text = str(instruction)
            instruction_parts.append(f"SPECIFIC INSTRUCTIONS:\n{instruction_text}")

        return "\n\n".join(instruction_parts) if instruction_parts else ""

    def validate_config(self) -> bool:
        """Validate the configuration structure and required fields."""
        logger.info("🔍 Validating configuration structure")

        if "root_agent" not in self.config:
            error_msg = "Missing 'root_agent' section in configuration"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)

        root_config = self.config["root_agent"]

        supported_classes = [
            "LLMAgent",
            "LlmAgent",
            "LoopAgent",
            "SequentialAgent",
            "ParallelAgent",
        ]

        self._validate_agent_config(
            root_config, "root_agent", supported_classes, is_root=True
        )

        agents_config = self.config.get("agents", [])
        if agents_config:
            logger.debug(f"Validating {len(agents_config)} agent configurations")

            for i, agent_config in enumerate(agents_config):
                agent_name = agent_config.get("name", f"agent_at_index_{i}")
                try:
                    self._validate_agent_config(
                        agent_config, agent_name, supported_classes
                    )
                except ValueError as e:
                    raise ValueError(
                        f"Invalid configuration for agent at index {i}: {e}"
                    )

        logger.info("✅ Configuration validation completed successfully")
        return True

    def _validate_agent_config(
        self,
        agent_config: Dict[str, Any],
        agent_identifier: str,
        supported_classes: List[str],
        is_root: bool = False,
    ) -> None:
        # LLM-only fields (instruction, model_id) not required for
        # LoopAgent, ParallelAgent, SequentialAgent — they have no LLM
        agent_class_val = agent_config.get("agent_class", "LLMAgent")
        is_llm = agent_class_val in {"LLMAgent", "LlmAgent"}

        if is_root:
            required_fields = ["agent_class", "description"]
            if is_llm:
                required_fields += ["model", "instruction"]
        else:
            required_fields = ["name", "agent_class", "description"]
            if is_llm:
                required_fields += ["model", "instruction"]

        for field in required_fields:
            if field not in agent_config:
                raise ValueError(
                    f"Missing required field '{field}' in {agent_identifier} configuration"
                )

        agent_class = agent_config.get("agent_class")
        if agent_class not in supported_classes:
            if is_root and agent_class != "LLMAgent":
                logger.warning(
                    f"Root agent class is '{agent_class}', but only 'LLMAgent' is fully supported. "
                    f"Supported classes: {supported_classes}"
                )
            else:
                logger.warning(
                    f"Agent '{agent_identifier}' has class '{agent_class}'. "
                    f"Supported classes: {supported_classes}"
                )

    def print_agent_hierarchy(self, agent=None, indent: int = 0) -> None:
        if agent is None:
            logger.info("🔧 Building root agent to display hierarchy...")
            try:
                agent = self.build_root_agent(include_sub_agents=True)
            except Exception as e:
                logger.error(
                    f"❌ Failed to build root agent for hierarchy display: {e}"
                )
                return

        if agent is None:
            logger.error("❌ No root agent found or agent is None")
            return

        prefix = "  " * indent
        agent_type = type(agent).__name__
        agent_name = getattr(agent, "name", "unnamed")

        logger.info(f"{prefix}├─ {agent_name} ({agent_type})")

        if hasattr(agent, "sub_agents") and agent.sub_agents:
            logger.debug(f"{prefix}│  └─ {len(agent.sub_agents)} sub-agents:")

            for i, sub_agent in enumerate(agent.sub_agents):
                is_last = i == len(agent.sub_agents) - 1
                self.print_agent_hierarchy(sub_agent, indent + 1)
        else:
            logger.debug(f"{prefix}│  └─ No sub-agents")

    def get_agent_count(self, agent=None) -> Dict[str, int]:
        if agent is None:
            agent = self.build_root_agent(include_sub_agents=True)

        counts = {}

        def _count_recursive(current_agent):
            agent_type = type(current_agent).__name__
            counts[agent_type] = counts.get(agent_type, 0) + 1

            if hasattr(current_agent, "sub_agents") and current_agent.sub_agents:
                for sub_agent in current_agent.sub_agents:
                    _count_recursive(sub_agent)

        _count_recursive(agent)
        return counts


def build_multi_agent_system(config_path: str = None) -> LlmAgent:
    logger.info(
        f"🔧 Building multi-agent system from config: {config_path or 'default'}"
    )

    try:
        builder = MultiAgentBuilder(config_path)
        builder.validate_config()

        root_agent = builder.build_root_agent(include_sub_agents=True)

        agent_counts = builder.get_agent_count(root_agent)
        total_agents = sum(agent_counts.values())
        logger.info(
            f"✅ Multi-agent system built successfully with {total_agents} total agents: {agent_counts}"
        )

        return root_agent

    except Exception as e:
        logger.error(f"❌ Failed to build multi-agent system: {e}")
        raise


def validate_config_file(config_path: str = None) -> bool:
    logger.info(f"🔍 Validating configuration file: {config_path or 'default'}")

    builder = MultiAgentBuilder(config_path)
    is_valid = builder.validate_config()

    logger.info("✅ Configuration file validation completed successfully")
    return is_valid

