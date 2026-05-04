"""Tests for root_agent/sub_agents/sequential_agent.py — SequentialAgentBuilder."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import pytest
from root_agent.sub_agents.sequential_agent import (
    SequentialAgentBuilder,
    create_userstory_agent,
    create_complex_agent,
)


def test_sequential_agent_builder_setters():
    builder = SequentialAgentBuilder()
    builder.set_name("sequential").set_description("desc")
    assert builder._name == "sequential"
    assert builder._description == "desc"

def test_sequential_agent_builder_add_sub_agents():
    builder = SequentialAgentBuilder()
    dummy_agent = object()
    builder.add_sub_agent(dummy_agent)
    assert dummy_agent in builder._sub_agents
    builder.set_sub_agents([dummy_agent])
    assert builder._sub_agents == [dummy_agent]
    builder.add_sub_agents([dummy_agent, dummy_agent])
    assert builder._sub_agents.count(dummy_agent) >= 3


class TestSequentialAgentBuilderFull:
    def test_set_sub_agents_replaces(self):
        b = SequentialAgentBuilder()
        b.add_sub_agent("a1")
        b.set_sub_agents(["a2"])
        assert b._sub_agents == ["a2"]

    def test_set_before_agent_callback(self):
        cb = lambda: None
        b = SequentialAgentBuilder()
        b.set_before_agent_callback(cb)
        assert b._before_agent_callback is cb

    def test_set_after_agent_callback(self):
        cb = lambda: None
        b = SequentialAgentBuilder()
        b.set_after_agent_callback(cb)
        assert b._after_agent_callback is cb

    def test_clear_sub_agents(self):
        b = SequentialAgentBuilder()
        b.add_sub_agent("a")
        b.clear_sub_agents()
        assert b._sub_agents == []

    def test_build_success(self):
        assert SequentialAgentBuilder().set_name("s").set_description("d").build().name == "s"

    def test_build_missing_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            SequentialAgentBuilder().set_description("d").build()

    def test_build_missing_description_raises(self):
        with pytest.raises(ValueError, match="description"):
            SequentialAgentBuilder().set_name("s").build()

    def test_reset(self):
        b = SequentialAgentBuilder()
        b.set_name("s").set_description("d").add_sub_agent("a")
        b.set_before_agent_callback(lambda: None)
        b.set_after_agent_callback(lambda: None)
        b.reset()
        assert b._name is None
        assert b._sub_agents == []
        assert b._before_agent_callback is None


class TestSequentialConvenienceFunctions:
    def test_create_userstory_agent(self):
        assert create_userstory_agent().name == "agent_name"

    def test_create_complex_agent(self):
        assert create_complex_agent("c", "d", []).name == "c"

    def test_create_complex_agent_with_callbacks(self):
        cb = lambda: None
        assert create_complex_agent("c", "d", [], before_callback=cb, after_callback=cb).name == "c"
