from google.adk.agents import Agent
from google.adk.agents import SequentialAgent
from typing import List, Optional, Callable, Any


class SequentialAgentBuilder:
    """Builder class for creating SequentialAgent instances dynamically."""
    
    def __init__(self):
        self._name: Optional[str] = None
        self._description: Optional[str] = None
        self._sub_agents: List[Agent] = []
        self._before_agent_callback: Optional[Callable] = None
        self._after_agent_callback: Optional[Callable] = None
    
    def set_name(self, name: str) -> 'SequentialAgentBuilder':
        """Set the agent name."""
        self._name = name
        return self
    
    def set_description(self, description: str) -> 'SequentialAgentBuilder':
        """Set the agent description."""
        self._description = description
        return self
    
    def add_sub_agent(self, agent: Agent) -> 'SequentialAgentBuilder':
        """Add a single sub-agent to the list."""
        self._sub_agents.append(agent)
        return self
    
    def add_sub_agents(self, agents: List[Agent]) -> 'SequentialAgentBuilder':
        """Add multiple sub-agents to the list."""
        self._sub_agents.extend(agents)
        return self
    
    def set_sub_agents(self, agents: List[Agent]) -> 'SequentialAgentBuilder':
        """Set the complete list of sub-agents (replaces existing)."""
        self._sub_agents = agents.copy()
        return self
    
    def set_before_agent_callback(self, callback: Callable) -> 'SequentialAgentBuilder':
        """Set the before agent callback function."""
        self._before_agent_callback = callback
        return self
    
    def set_after_agent_callback(self, callback: Callable) -> 'SequentialAgentBuilder':
        """Set the after agent callback function."""
        self._after_agent_callback = callback
        return self
    
    def clear_sub_agents(self) -> 'SequentialAgentBuilder':
        """Clear all sub-agents from the list."""
        self._sub_agents.clear()
        return self
    
    def build(self) -> SequentialAgent:
        """Build and return the SequentialAgent instance."""
        if not self._name:
            raise ValueError("Agent name is required")
        if not self._description:
            raise ValueError("Agent description is required")
        
        return SequentialAgent(
            name=self._name,
            description=self._description,
            sub_agents=self._sub_agents,
            before_agent_callback=self._before_agent_callback,
            after_agent_callback=self._after_agent_callback
        )
    
    def reset(self) -> 'SequentialAgentBuilder':
        """Reset the builder to initial state."""
        self._name = None
        self._description = None
        self._sub_agents = []
        self._before_agent_callback = None
        self._after_agent_callback = None
        return self


# Example usage:
def create_userstory_agent() -> SequentialAgent:
    """Example function showing how to use the builder."""
    builder = SequentialAgentBuilder()
    
    return (builder
            .set_name("agent_name")
            .set_description("agent_description")
            .build())


# Alternative usage with all parameters:
def create_complex_agent(name: str, description: str, agents: List[Agent], 
                        before_callback: Optional[Callable] = None,
                        after_callback: Optional[Callable] = None) -> SequentialAgent:
    """Create a SequentialAgent with all parameters."""
    builder = SequentialAgentBuilder()
    
    builder.set_name(name).set_description(description).set_sub_agents(agents)
    
    if before_callback:
        builder.set_before_agent_callback(before_callback)
    
    if after_callback:
        builder.set_after_agent_callback(after_callback)
    
    return builder.build()