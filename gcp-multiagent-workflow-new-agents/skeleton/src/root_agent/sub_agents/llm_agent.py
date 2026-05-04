"""LLM Agent builder for creating LlmAgent instances from YAML configuration."""

from typing import Any, Callable, Dict, List, Optional

from google.adk.agents import Agent, LlmAgent
from google.genai.types import GenerateContentConfig

from utils.log_helper import setup_logging
from root_agent.tools.tools_builder import create_tools_from_yaml_config
from root_agent.content_filter.safety_settings import safety_settings_model_callback


LOG = setup_logging()


class LlmAgentBuilder:
    """Builder for creating LlmAgent instances from YAML configuration."""

    def __init__(self):
        self._name: Optional[str] = None
        self._model: Optional[Any] = None
        self._description: Optional[str] = None
        self._instruction: Optional[str] = None
        self._disallow_transfer_to_parent: bool = True
        self._disallow_transfer_to_peers: bool = True
        self._sub_agents: List[Agent] = []
        self._tools: List[Any] = []
        self._output_key = None
        self._generate_content_config: Optional[GenerateContentConfig] = (
            GenerateContentConfig(temperature=0.1, top_p=0.5)
        )
        self._before_agent_callback: Optional[Callable] = None
        self._after_agent_callback: Optional[Callable] = None
        self._before_model_callback: Optional[Callable] = None
        self._after_model_callback: Optional[Callable] = None
        self._global_config: Optional[Dict[str, Any]] = (
            None  # Store global config for tools
        )

    def set_name(self, name: str) -> "LlmAgentBuilder":
        self._name = name
        return self

    def set_model(self, model: Any) -> "LlmAgentBuilder":
        self._model = model
        return self

    def set_description(self, description: str) -> "LlmAgentBuilder":
        self._description = description
        return self

    def set_instruction(self, instruction: str) -> "LlmAgentBuilder":
        self._instruction = instruction
        return self

    def set_disallow_transfer_to_parent(self, disallow: bool) -> "LlmAgentBuilder":
        self._disallow_transfer_to_parent = disallow
        return self

    def set_disallow_transfer_to_peers(self, disallow: bool) -> "LlmAgentBuilder":
        self._disallow_transfer_to_peers = disallow
        return self

    def add_sub_agent(self, agent: Agent) -> "LlmAgentBuilder":
        self._sub_agents.append(agent)
        return self

    def add_sub_agents(self, agents: List[Agent]) -> "LlmAgentBuilder":
        self._sub_agents.extend(agents)
        return self

    def set_sub_agents(self, agents: List[Agent]) -> "LlmAgentBuilder":
        self._sub_agents = agents.copy()
        return self

    def add_tool(self, tool: Any) -> "LlmAgentBuilder":
        self._tools.append(tool)
        return self

    def add_tools(self, tools: List[Any]) -> "LlmAgentBuilder":
        self._tools.extend(tools)
        return self

    def set_tools(self, tools: List[Any]) -> "LlmAgentBuilder":
        self._tools = tools.copy()
        return self

    def set_generate_content_config(
        self, config: GenerateContentConfig
    ) -> "LlmAgentBuilder":
        self._generate_content_config = config
        return self

    def set_temperature(self, temperature: float) -> "LlmAgentBuilder":
        if self._generate_content_config is None:
            self._generate_content_config = GenerateContentConfig()
        self._generate_content_config.temperature = temperature
        return self

    def set_top_p(self, top_p: float) -> "LlmAgentBuilder":
        if self._generate_content_config is None:
            self._generate_content_config = GenerateContentConfig()
        self._generate_content_config.top_p = top_p
        return self

    def set_output_key(self, output_key: str) -> "LlmAgentBuilder":
        self._output_key = output_key
        return self

    def set_before_agent_callback(self, callback: Callable) -> "LlmAgentBuilder":
        self._before_agent_callback = callback
        return self

    def set_after_agent_callback(self, callback: Callable) -> "LlmAgentBuilder":
        self._after_agent_callback = callback
        return self

    def set_before_model_callback(self, callback: Callable) -> "LlmAgentBuilder":
        self._before_model_callback = callback
        return self

    def set_after_model_callback(self, callback: Callable) -> "LlmAgentBuilder":
        self._after_model_callback = callback
        return self

    def apply_callbacks(self) -> "LlmAgentBuilder":
        """Apply default callbacks to the agent configuration."""
        # Apply safety settings callback as default before_model_callback
        if not self._before_model_callback:
            self._before_model_callback = safety_settings_model_callback
            LOG.info(
                f"🔒 Applied safety_settings_model_callback to agent '{self._name}'"
            )

        # Add other default callbacks here if needed
        # if not self._before_agent_callback:
        #     self._before_agent_callback = some_other_callback

        return self

    def set_global_config(self, global_config: Dict[str, Any]) -> "LlmAgentBuilder":
        self._global_config = global_config
        return self

    def clear_sub_agents(self) -> "LlmAgentBuilder":
        self._sub_agents.clear()
        return self

    def clear_tools(self) -> "LlmAgentBuilder":
        self._tools.clear()
        return self

    def from_yaml_config(
        self,
        agent_config: Dict[str, Any],
        global_config: Optional[Dict[str, Any]] = None,
    ) -> "LlmAgentBuilder":
        """Configure the builder from YAML agent configuration."""
        name = agent_config.get("name", "unnamed_agent")
        description = agent_config.get("description", "")
        model_id = agent_config.get("model_id", "gemini-2.0-flash-001")
        instruction = agent_config.get("instruction", "")
        output_key = agent_config.get("output_key", None)
        llm_config = agent_config.get("llm_config", {})
        tools_config = agent_config.get("tools", {})

        # Store global config for tool creation
        if global_config:
            self.set_global_config(global_config)

        # Convert instruction to string if it's a list
        if isinstance(instruction, list):
            instruction_text = "\n".join(f"- {instr}" for instr in instruction)
        else:
            instruction_text = str(instruction) if instruction else ""

        # Add output_key instruction if provided
        if output_key:
            if instruction_text:
                instruction_text += f"\n\nOutput Key: {output_key}\n- Ensure your response includes the key '{output_key}' for proper output handling."
            else:
                instruction_text = f"Output Key: {output_key}\n- Ensure your response includes the key '{output_key}' for proper output handling."

        # Set basic properties
        self.set_name(name)
        self.set_model(model_id)
        self.set_description(description)
        self.set_instruction(instruction_text)

        # Set output_key if provided
        if output_key:
            self.set_output_key(output_key)

        # Set transfer policies
        self.set_disallow_transfer_to_parent(True)
        self.set_disallow_transfer_to_peers(True)

        # Configure LLM settings if provided
        if llm_config:
            if "temperature" in llm_config:
                self.set_temperature(llm_config["temperature"])
            if "top_p" in llm_config:
                self.set_top_p(llm_config["top_p"])
            # Create full config if other parameters are needed
            if any(
                key in llm_config
                for key in ["top_k", "candidate_count", "max_output_tokens"]
            ):
                generate_config = GenerateContentConfig(
                    temperature=llm_config.get("temperature", 0.1),
                    top_p=llm_config.get("top_p", 0.5),
                    top_k=llm_config.get("top_k", None),
                    candidate_count=llm_config.get("candidate_count", None),
                    max_output_tokens=llm_config.get("max_output_tokens", None),
                )
                self.set_generate_content_config(generate_config)

        if tools_config:
            try:
                tools = create_tools_from_yaml_config(
                    tools_config, self._global_config, name
                )
                if tools:
                    self.set_tools(tools)
            except Exception as e:
                LOG.warning(f"⚠️ Failed to create tools for agent '{name}': {e}")
                         
        return self

    def build(self) -> LlmAgent:
        """Build and return the LlmAgent instance."""
        if not self._name:
            raise ValueError("❌ Agent name is required")
        if not self._model:
            raise ValueError("❌ Model is required")
        if not self._description:
            raise ValueError("❌ Agent description is required")

        return LlmAgent(
            name=self._name,
            model=self._model,
            description=self._description,
            instruction=self._instruction,
            disallow_transfer_to_parent=self._disallow_transfer_to_parent,
            disallow_transfer_to_peers=self._disallow_transfer_to_peers,
            sub_agents=self._sub_agents,
            tools=self._tools,
            output_key=self._output_key,
            generate_content_config=self._generate_content_config,
            before_agent_callback=self._before_agent_callback,
            after_agent_callback=self._after_agent_callback,
            before_model_callback=self._before_model_callback,
            after_model_callback=self._after_model_callback,
        )

    def reset(self) -> "LlmAgentBuilder":
        self._name = None
        self._model = None
        self._description = None
        self._instruction = None
        self._disallow_transfer_to_parent = True
        self._disallow_transfer_to_peers = True
        self._sub_agents = []
        self._tools = []
        self._output_key = None
        self._generate_content_config = GenerateContentConfig(
            temperature=0.1, top_p=0.5
        )
        self._before_agent_callback = None
        self._after_agent_callback = None
        self._global_config = None
        return self

