"""
AMPS — Agent Memory Portability Standard v1.0
MIT Licensed. Reference implementation by Inflectiv.
"""
from amps.adapters.agent_zero import AgentZeroAdapter
from amps.adapters.autogpt    import AutoGPTAdapter
from amps.adapters.crewai     import CrewAIAdapter
from amps.adapters.langgraph  import LangGraphAdapter
from amps.adapters.llamaindex import LlamaIndexAdapter

__version__ = "1.0.0"
__all__ = [
    "AgentZeroAdapter",
    "AutoGPTAdapter",
    "CrewAIAdapter",
    "LangGraphAdapter",
    "LlamaIndexAdapter",
]
