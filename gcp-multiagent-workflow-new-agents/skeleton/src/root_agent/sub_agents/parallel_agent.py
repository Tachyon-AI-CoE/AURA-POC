from google.adk.agents import Agent
from google.adk.agents import ParallelAgent
from typing import List, Optional, Callable, Any, Dict


class ParallelAgentBuilder:
    """Builder class for creating ParallelAgent instances dynamically."""
    
    def __init__(self):
        self._name: Optional[str] = None
        self._description: Optional[str] = None
        self._sub_agents: List[Agent] = []
        self._before_agent_callback: Optional[Callable] = None
        self._after_agent_callback: Optional[Callable] = None
    
    def set_name(self, name: str) -> 'ParallelAgentBuilder':
        """Set the agent name."""
        self._name = name
        return self
    
    def set_description(self, description: str) -> 'ParallelAgentBuilder':
        """Set the agent description."""
        self._description = description
        return self
    
    def add_sub_agent(self, agent: Agent) -> 'ParallelAgentBuilder':
        """Add a single sub-agent to the list."""
        self._sub_agents.append(agent)
        return self
    
    def add_sub_agents(self, agents: List[Agent]) -> 'ParallelAgentBuilder':
        """Add multiple sub-agents to the list."""
        self._sub_agents.extend(agents)
        return self
    
    def set_sub_agents(self, agents: List[Agent]) -> 'ParallelAgentBuilder':
        """Set the complete list of sub-agents (replaces existing)."""
        self._sub_agents = agents.copy()
        return self
    
    def set_before_agent_callback(self, callback: Callable) -> 'ParallelAgentBuilder':
        """Set the before agent callback function."""
        self._before_agent_callback = callback
        return self
    
    def set_after_agent_callback(self, callback: Callable) -> 'ParallelAgentBuilder':
        """Set the after agent callback function."""
        self._after_agent_callback = callback
        return self
    
    def clear_sub_agents(self) -> 'ParallelAgentBuilder':
        """Clear all sub-agents from the list."""
        self._sub_agents.clear()
        return self
    
    def from_dict(self, config: Dict[str, Any]) -> 'ParallelAgentBuilder':
        """Configure the builder from a dictionary of parameters."""
        if 'name' in config:
            self.set_name(config['name'])
        
        if 'description' in config:
            self.set_description(config['description'])
        
        if 'sub_agents' in config:
            self.set_sub_agents(config['sub_agents'])
        
        if 'before_agent_callback' in config:
            self.set_before_agent_callback(config['before_agent_callback'])
        
        if 'after_agent_callback' in config:
            self.set_after_agent_callback(config['after_agent_callback'])
        
        return self
    
    def build(self) -> ParallelAgent:
        """Build and return the ParallelAgent instance."""
        if not self._name:
            raise ValueError("Agent name is required")
        if not self._description:
            raise ValueError("Agent description is required")
        
        return ParallelAgent(
            name=self._name,
            description=self._description,
            sub_agents=self._sub_agents,
            before_agent_callback=self._before_agent_callback,
            after_agent_callback=self._after_agent_callback
        )
    
    def reset(self) -> 'ParallelAgentBuilder':
        """Reset the builder to initial state."""
        self._name = None
        self._description = None
        self._sub_agents = []
        self._before_agent_callback = None
        self._after_agent_callback = None
        return self


# Example usage with method chaining:
def create_parallel_processing_agent(name: str, description: str) -> ParallelAgent:
    """Create a parallel processing agent with basic configuration."""
    builder = ParallelAgentBuilder()
    
    return (builder
            .set_name(name)
            .set_description(description)
            .build())


# Example usage with dictionary configuration:
def create_parallel_agent_from_config(config: Dict[str, Any]) -> ParallelAgent:
    """Create a ParallelAgent from a configuration dictionary."""
    builder = ParallelAgentBuilder()
    return builder.from_dict(config).build()


# Example usage with all parameters:
def create_complex_parallel_agent(
    name: str,
    description: str,
    agents: List[Agent],
    before_callback: Optional[Callable] = None,
    after_callback: Optional[Callable] = None
) -> ParallelAgent:
    """Create a ParallelAgent with all configurations."""
    builder = ParallelAgentBuilder()
    
    builder.set_name(name).set_description(description).set_sub_agents(agents)
    
    if before_callback:
        builder.set_before_agent_callback(before_callback)
    
    if after_callback:
        builder.set_after_agent_callback(after_callback)
    
    return builder.build()


# Example configuration dictionaries:
basic_parallel_config = {
    "name": "data_processing_parallel_agent",
    "description": "Processes multiple data streams in parallel",
    "sub_agents": []  # Add your sub-agents here
}

advanced_parallel_config = {
    "name": "multi_task_parallel_agent",
    "description": "Handles multiple tasks simultaneously",
    "sub_agents": [],  # Add your sub-agents here
    "before_agent_callback": None,  # Add callback function if needed
    "after_agent_callback": None   # Add callback function if needed
}

# Usage examples:
# agent1 = create_parallel_agent_from_config(basic_parallel_config)
# agent2 = create_parallel_agent_from_config(advanced_parallel_config)

# Original agent converted to use builder:
def create_original_parallel_agent() -> ParallelAgent:
    """Recreate the original parallel agent using the builder."""
    return (ParallelAgentBuilder()
            .set_name("name_parallel_agent")
            .set_description("parallel_agent_description")
            .build())
