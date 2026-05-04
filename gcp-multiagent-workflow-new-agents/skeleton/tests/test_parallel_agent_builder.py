"""Tests for root_agent/sub_agents/parallel_agent.py — ParallelAgentBuilder."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import pytest
from root_agent.sub_agents.parallel_agent import (
    ParallelAgentBuilder,
    create_parallel_processing_agent,
    create_parallel_agent_from_config,
    create_complex_parallel_agent,
    create_original_parallel_agent,
)


def test_parallel_agent_builder_setters():
    builder = ParallelAgentBuilder()
    builder.set_name("parallel").set_description("desc")
    assert builder._name == "parallel"
    assert builder._description == "desc"

def test_parallel_agent_builder_add_sub_agents():
    builder = ParallelAgentBuilder()
    dummy_agent = object()
    builder.add_sub_agent(dummy_agent)
    assert dummy_agent in builder._sub_agents
    builder.set_sub_agents([dummy_agent])
    assert builder._sub_agents == [dummy_agent]
    builder.add_sub_agents([dummy_agent, dummy_agent])
    assert builder._sub_agents.count(dummy_agent) >= 3


class TestParallelAgentBuilderFull:
    def test_set_sub_agents_replaces(self):
        b = ParallelAgentBuilder()
        b.add_sub_agent("a1")
        b.set_sub_agents(["a2"])
        assert b._sub_agents == ["a2"]

    def test_set_before_agent_callback(self):
        cb = lambda: None
        b = ParallelAgentBuilder()
        b.set_before_agent_callback(cb)
        assert b._before_agent_callback is cb

    def test_set_after_agent_callback(self):
        cb = lambda: None
        b = ParallelAgentBuilder()
        b.set_after_agent_callback(cb)
        assert b._after_agent_callback is cb

    def test_clear_sub_agents(self):
        b = ParallelAgentBuilder()
        b.add_sub_agent("a")
        b.clear_sub_agents()
        assert b._sub_agents == []

    def test_from_dict_all_fields(self):
        cb = lambda: None
        b = ParallelAgentBuilder().from_dict({"name": "p1", "description": "d", "sub_agents": ["a1"],
                                               "before_agent_callback": cb, "after_agent_callback": cb})
        assert b._name == "p1"

    def test_from_dict_partial(self):
        assert ParallelAgentBuilder().from_dict({"name": "x"})._name == "x"

    def test_build_success(self):
        assert ParallelAgentBuilder().set_name("p").set_description("d").build().name == "p"

    def test_build_missing_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            ParallelAgentBuilder().set_description("d").build()

    def test_build_missing_description_raises(self):
        with pytest.raises(ValueError, match="description"):
            ParallelAgentBuilder().set_name("p").build()

    def test_reset(self):
        b = ParallelAgentBuilder()
        b.set_name("p").set_description("d").add_sub_agent("a")
        b.set_before_agent_callback(lambda: None)
        b.reset()
        assert b._name is None
        assert b._sub_agents == []
        assert b._before_agent_callback is None


class TestParallelConvenienceFunctions:
    def test_create_parallel_processing_agent(self):
        assert create_parallel_processing_agent("n", "d").name == "n"

    def test_create_parallel_agent_from_config(self):
        assert create_parallel_agent_from_config({"name": "p", "description": "d"}).name == "p"

    def test_create_complex_parallel_agent(self):
        assert create_complex_parallel_agent("c", "d", []).name == "c"

    def test_create_complex_parallel_agent_with_callbacks(self):
        cb = lambda: None
        assert create_complex_parallel_agent("c", "d", [], before_callback=cb, after_callback=cb).name == "c"

    def test_create_original_parallel_agent(self):
        assert create_original_parallel_agent().name == "name_parallel_agent"
