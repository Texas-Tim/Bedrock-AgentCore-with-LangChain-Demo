"""
Shared utilities for LangGraph + Bedrock AgentCore agents.

This module provides reusable components for:
- Configuration management with validation
- Knowledge Base tool creation
- GuardRails configuration
- Memory initialization
- Retry logic for AWS operations
"""

from shared.config import AgentConfig, load_config
from shared.guardrails import build_guardrails_config, handle_guardrails_error
from shared.retry import with_retry, RetryConfig

# Lazy imports for modules that require optional dependencies
def create_knowledge_base_tool(*args, **kwargs):
    """Create a Knowledge Base query tool. Lazy import wrapper."""
    from shared.knowledge_base import create_knowledge_base_tool as _create_kb_tool
    return _create_kb_tool(*args, **kwargs)

def initialize_memory(*args, **kwargs):
    """Initialize AgentCore Memory. Lazy import wrapper."""
    from shared.memory import initialize_memory as _init_memory
    return _init_memory(*args, **kwargs)

__all__ = [
    "AgentConfig",
    "load_config",
    "create_knowledge_base_tool",
    "build_guardrails_config",
    "handle_guardrails_error",
    "initialize_memory",
    "with_retry",
    "RetryConfig",
]
