"""Tests for root_agent/sub_agents/loop_agent.py — LoopAgentBuilder."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import pytest
from root_agent.sub_agents.loop_agent import (
    LoopAgentBuilder,
    create_refinement_loop,
    create_loop_agent_from_config,
    create_complex_loop_agent,
)


def test_loop_agent_builder_setters():
    builder = LoopAgentBuilder()
    builder.set_name("loop").set_description("desc")
    assert builder._name == "loop"
    assert builder._description == "desc"

def test_loop_agent_builder_add_sub_agents():
    builder = LoopAgentBuilder()
    dummy_agent = object()
    builder.add_sub_agent(dummy_agent)
    assert dummy_agent in builder._sub_agents
    builder.set_sub_agents([dummy_agent])
    assert builder._sub_agents == [dummy_agent]
    builder.add_sub_agents([dummy_agent, dummy_agent])
    assert builder._sub_agents.count(dummy_agent) >= 3

def test_loop_agent_builder_max_iterations():
    builder = LoopAgentBuilder()
    assert builder._max_iterations == 5


class TestLoopAgentBuilderFull:
    def test_set_sub_agents_replaces(self):
        b = LoopAgentBuilder()
        b.add_sub_agent("a1")
        b.set_sub_agents(["a2", "a3"])
        assert b._sub_agents == ["a2", "a3"]

    def test_set_max_iterations(self):
        b = LoopAgentBuilder()
        b.set_max_iterations(10)
        assert b._max_iterations == 10

    def test_set_before_agent_callback(self):
        cb = lambda: None
        b = LoopAgentBuilder()
        b.set_before_agent_callback(cb)
        assert b._before_agent_callback is cb

    def test_set_after_agent_callback(self):
        cb = lambda: None
        b = LoopAgentBuilder()
        b.set_after_agent_callback(cb)
        assert b._after_agent_callback is cb

    def test_clear_sub_agents(self):
        b = LoopAgentBuilder()
        b.add_sub_agent("a")
        b.clear_sub_agents()
        assert b._sub_agents == []

    def test_from_dict_all_fields(self):
        cb = lambda: None
        config = {"name": "loop1", "description": "d", "sub_agents": ["a1"],
                  "max_iterations": 3, "before_agent_callback": cb, "after_agent_callback": cb}
        b = LoopAgentBuilder().from_dict(config)
        assert b._name == "loop1"
        assert b._max_iterations == 3

    def test_from_dict_partial(self):
        b = LoopAgentBuilder().from_dict({"name": "x"})
        assert b._name == "x"
        assert b._description is None

    def test_build_success(self):
        assert LoopAgentBuilder().set_name("l").set_description("d").build().name == "l"

    def test_build_missing_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            LoopAgentBuilder().set_description("d").build()

    def test_build_missing_description_raises(self):
        with pytest.raises(ValueError, match="description"):
            LoopAgentBuilder().set_name("l").build()

    def test_reset(self):
        b = LoopAgentBuilder()
        b.set_name("l").set_description("d").set_max_iterations(10)
        b.add_sub_agent("a")
        b.set_before_agent_callback(lambda: None)
        b.set_after_agent_callback(lambda: None)
        b.reset()
        assert b._name is None
        assert b._sub_agents == []
        assert b._max_iterations == 5


class TestLoopConvenienceFunctions:
    def test_create_refinement_loop(self):
        assert create_refinement_loop().name == "RefinementLoop"

    def test_create_loop_agent_from_config(self):
        assert create_loop_agent_from_config({"name": "t", "description": "d", "max_iterations": 2}).name == "t"

    def test_create_complex_loop_agent(self):
        assert create_complex_loop_agent("c", "d", [], max_iterations=7).name == "c"

    def test_create_complex_loop_agent_with_callbacks(self):
        cb = lambda: None
        assert create_complex_loop_agent("c", "d", [], before_callback=cb, after_callback=cb).name == "c"
