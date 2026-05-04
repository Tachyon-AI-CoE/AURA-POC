from google.adk.agents import Agent
from google.adk.agents import LoopAgent
from typing import List, Optional, Callable, Any, Dict


class LoopAgentBuilder:
    """Builder class for creating LoopAgent instances dynamically."""
    
    def __init__(self):
        self._name: Optional[str] = None
        self._description: Optional[str] = None
        self._sub_agents: List[Agent] = []
        self._before_agent_callback: Optional[Callable] = None
        self._after_agent_callback: Optional[Callable] = None
        self._max_iterations: int = 5
    
    def set_name(self, name: str) -> 'LoopAgentBuilder':
        """Set the agent name."""
        self._name = name
        return self
    
    def set_description(self, description: str) -> 'LoopAgentBuilder':
        """Set the agent description."""
        self._description = description
        return self
    
    def add_sub_agent(self, agent: Agent) -> 'LoopAgentBuilder':
        """Add a single sub-agent to the list."""
        self._sub_agents.append(agent)
        return self
    
    def add_sub_agents(self, agents: List[Agent]) -> 'LoopAgentBuilder':
        """Add multiple sub-agents to the list."""
        self._sub_agents.extend(agents)
        return self
    
    def set_sub_agents(self, agents: List[Agent]) -> 'LoopAgentBuilder':
        """Set the complete list of sub-agents (replaces existing)."""
        self._sub_agents = agents.copy()
        return self
    
    def set_max_iterations(self, max_iterations: int) -> 'LoopAgentBuilder':
        """Set the maximum number of iterations."""
        self._max_iterations = max_iterations
        return self
    
    def set_before_agent_callback(self, callback: Callable) -> 'LoopAgentBuilder':
        """Set the before agent callback function."""
        self._before_agent_callback = callback
        return self
    
    def set_after_agent_callback(self, callback: Callable) -> 'LoopAgentBuilder':
        """Set the after agent callback function."""
        self._after_agent_callback = callback
        return self
    
    def clear_sub_agents(self) -> 'LoopAgentBuilder':
        """Clear all sub-agents from the list."""
        self._sub_agents.clear()
        return self
    
    def from_dict(self, config: Dict[str, Any]) -> 'LoopAgentBuilder':
        """Configure the builder from a dictionary of parameters."""
        if 'name' in config:
            self.set_name(config['name'])
        
        if 'description' in config:
            self.set_description(config['description'])
        
        if 'sub_agents' in config:
            self.set_sub_agents(config['sub_agents'])
        
        if 'max_iterations' in config:
            self.set_max_iterations(config['max_iterations'])
        
        if 'before_agent_callback' in config:
            self.set_before_agent_callback(config['before_agent_callback'])
        
        if 'after_agent_callback' in config:
            self.set_after_agent_callback(config['after_agent_callback'])
        
        return self
    
    def build(self) -> LoopAgent:
        """Build and return the LoopAgent instance."""
        if not self._name:
            raise ValueError("Agent name is required")
        if not self._description:
            raise ValueError("Agent description is required")
        
        return LoopAgent(
            name=self._name,
            description=self._description,
            sub_agents=self._sub_agents,
            before_agent_callback=self._before_agent_callback,
            after_agent_callback=self._after_agent_callback,
            max_iterations=self._max_iterations
        )
    
    def reset(self) -> 'LoopAgentBuilder':
        """Reset the builder to initial state."""
        self._name = None
        self._description = None
        self._sub_agents = []
        self._before_agent_callback = None
        self._after_agent_callback = None
        self._max_iterations = 5
        return self


# Example usage with method chaining:
def create_refinement_loop() -> LoopAgent:
    """Create the original refinement loop using the builder."""
    builder = LoopAgentBuilder()
    
    return (builder
            .set_name("RefinementLoop")
            .set_description("A loop agent that refines outputs based on critiques.")
            .set_max_iterations(5)
            .build())


# Example usage with dictionary configuration:
def create_loop_agent_from_config(config: Dict[str, Any]) -> LoopAgent:
    """Create a LoopAgent from a configuration dictionary."""
    builder = LoopAgentBuilder()
    return builder.from_dict(config).build()


# Example usage with all parameters:
def create_complex_loop_agent(
    name: str,
    description: str,
    agents: List[Agent],
    max_iterations: int = 5,
    before_callback: Optional[Callable] = None,
    after_callback: Optional[Callable] = None
) -> LoopAgent:
    """Create a LoopAgent with all configurations."""
    builder = LoopAgentBuilder()
    
    builder.set_name(name).set_description(description).set_sub_agents(agents).set_max_iterations(max_iterations)
    
    if before_callback:
        builder.set_before_agent_callback(before_callback)
    
    if after_callback:
        builder.set_after_agent_callback(after_callback)
    
    return builder.build()


# Example configuration dictionaries:
refinement_loop_config = {
    "name": "RefinementLoop",
    "description": "A loop agent that refines outputs based on critiques.",
    "sub_agents": [],  # Add critique and refine agents here
    "max_iterations": 5,
    "before_agent_callback": None,
    "after_agent_callback": None
}

quality_assurance_loop_config = {
    "name": "QualityAssuranceLoop",
    "description": "Continuously improves output quality through iterative feedback",
    "sub_agents": [],  # Add QA agents here
    "max_iterations": 3,
}

iterative_improvement_config = {
    "name": "IterativeImprovementLoop",
    "description": "Iteratively improves solutions until criteria are met",
    "sub_agents": [],  # Add improvement agents here
    "max_iterations": 10,
}

# Usage examples:
# refinement_loop = create_loop_agent_from_config(refinement_loop_config)
# qa_loop = create_loop_agent_from_config(quality_assurance_loop_config)
# improvement_loop = create_loop_agent_from_config(iterative_improvement_config)

# Original agent converted to use builder:
refinement_loop = create_refinement_loop()