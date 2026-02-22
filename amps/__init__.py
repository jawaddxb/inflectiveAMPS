"""
AMPS — Agent Memory Portability Standard v1.0
MIT Licensed. Reference implementation: OpenClaw / Inflectiv Vault.
"""
from amps.adapters.base       import AMPSAdapter, empty_amps
from amps.adapters.agent_zero import AgentZeroAdapter
from amps.adapters.autogpt    import AutoGPTAdapter
from amps.adapters.crewai     import CrewAIAdapter
from amps.adapters.langgraph  import LangGraphAdapter
from amps.adapters.llamaindex import LlamaIndexAdapter
from amps.adapters.openclaw   import OpenClawAdapter

__version__ = "1.0.0"
__all__ = [
    "AMPSAdapter",
    "empty_amps",
    "AgentZeroAdapter",
    "AutoGPTAdapter",
    "CrewAIAdapter",
    "LangGraphAdapter",
    "LlamaIndexAdapter",
    "OpenClawAdapter",
]
