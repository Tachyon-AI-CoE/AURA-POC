"""
Shared pytest fixtures and module-level mocks for unit tests.

This conftest.py is loaded before any test file. It pre-populates sys.modules
with stubs for heavy third-party packages (openinference, arize) that are not
installed in the test environment, and prevents root_agent/agent.py (which has
complex module-level initialization) from being imported during tests.
"""

import sys
import types

# ---------------------------------------------------------------------------
# Mock openinference (not installed in test environment)
# ---------------------------------------------------------------------------
_openinference = types.ModuleType("openinference")
_openinference_instr = types.ModuleType("openinference.instrumentation")
_openinference_adk = types.ModuleType("openinference.instrumentation.google_adk")


class _MockGoogleADKInstrumentor:
    def instrument(self, **kwargs):
        pass


_openinference_adk.GoogleADKInstrumentor = _MockGoogleADKInstrumentor
_openinference.instrumentation = _openinference_instr
_openinference_instr.google_adk = _openinference_adk

sys.modules.setdefault("openinference", _openinference)
sys.modules.setdefault("openinference.instrumentation", _openinference_instr)
sys.modules.setdefault("openinference.instrumentation.google_adk", _openinference_adk)

# ---------------------------------------------------------------------------
# Mock arize.otel (may not be installed in test environment)
# ---------------------------------------------------------------------------
_arize = types.ModuleType("arize")
_arize_otel = types.ModuleType("arize.otel")
_arize_otel.register = lambda *a, **kw: None
_arize.otel = _arize_otel

sys.modules.setdefault("arize", _arize)
sys.modules.setdefault("arize.otel", _arize_otel)

# ---------------------------------------------------------------------------
# Mock vertexai.rag (RagResource used by rag_tool.py)
# ---------------------------------------------------------------------------


class _DummyRagResource:
    def __init__(self, *args, **kwargs):
        self.rag_corpus = kwargs.get("rag_corpus", "dummy_corpus")


sys.modules.setdefault(
    "vertexai.rag", types.SimpleNamespace(RagResource=_DummyRagResource)
)

# ---------------------------------------------------------------------------
# Prevent root_agent/agent.py from being imported during unit tests.
#
# root_agent/__init__.py does `from . import agent`, which triggers agent.py.
# agent.py has module-level code that:
#   - Calls fetch_arize_secrets() (needs GCP Secret Manager)
#   - Instantiates MultiAgentBuilder and loads agent-config.yaml from disk
#   - Calls build_root_agent() which builds the full agent graph
#
# By pre-populating sys.modules["root_agent.agent"] with a lightweight stub,
# the __init__.py import succeeds without running any of that code.
# ---------------------------------------------------------------------------
_dummy_agent_mod = types.ModuleType("root_agent.agent")
_dummy_agent_mod.root_agent = None
_dummy_agent_mod.build_root_agent = lambda: None
_dummy_agent_mod.fetch_arize_secrets = lambda: (None, None)

sys.modules.setdefault("root_agent.agent", _dummy_agent_mod)

# ---------------------------------------------------------------------------
# mcp_client.py uses `MCPToolset` (uppercase) in return type annotations but
# only imports `McpToolset` (camelCase). Inject MCPToolset into builtins so
# the annotation evaluates without NameError when the module is loaded.
# ---------------------------------------------------------------------------
import builtins as _builtins


class _StubMcpToolset:
    def __init__(self, connection_params=None):
        self._connection_params = connection_params

    def __deepcopy__(self, memo):
        return _StubMcpToolset(self._connection_params)


if not hasattr(_builtins, "MCPToolset"):
    _builtins.MCPToolset = _StubMcpToolset
