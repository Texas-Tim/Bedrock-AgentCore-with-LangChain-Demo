"""
Memory initialization with error handling.

This module provides utilities for initializing AWS Bedrock AgentCore
Memory with proper error handling and fallback behavior.
"""

import logging
from typing import Optional, Tuple

from shared.config import MemoryConfig

logger = logging.getLogger(__name__)


def initialize_memory(
    config: MemoryConfig,
    region: str,
) -> Tuple[Optional["AgentCoreMemorySaver"], bool]:
    """
    Initialize AgentCore Memory checkpointer with error handling.
    
    Memory initialization can fail for various reasons:
    - Invalid or missing MEMORY_ID
    - AWS credentials not configured
    - Insufficient IAM permissions
    - Network connectivity issues
    - Memory resource doesn't exist in the specified region
    
    If initialization fails, the agent falls back to stateless mode.
    
    Args:
        config: Memory configuration
        region: AWS region
        
    Returns:
        Tuple of (checkpointer, success):
            - checkpointer: AgentCoreMemorySaver instance or None
            - success: True if initialization succeeded
    """
    if not config.enabled:
        logger.info("Memory: Not initialized (feature disabled)")
        return None, False
    
    try:
        from langgraph_checkpoint_aws import AgentCoreMemorySaver
        
        checkpointer = AgentCoreMemorySaver(
            config.memory_id,
            region_name=region,
        )
        logger.info(f"Memory: Successfully initialized (ID: {config.memory_id})")
        return checkpointer, True
    
    except ImportError as e:
        logger.warning(
            f"Memory initialization failed: langgraph_checkpoint_aws not installed. "
            f"Error: {e}. Agent will run in stateless mode."
        )
        return None, False
    
    except Exception as e:
        logger.warning(
            f"Memory initialization failed: {e}. "
            f"Agent will run in stateless mode (no conversation persistence)."
        )
        return None, False


def get_memory_config(
    actor_id: str = "default-user",
    thread_id: str = "default-session",
) -> dict:
    """
    Build configuration dict for memory-enabled agent calls.
    
    Args:
        actor_id: Unique identifier for the user/actor
        thread_id: Unique identifier for the conversation thread
        
    Returns:
        Configuration dict for agent.astream() or agent.ainvoke()
    """
    return {
        "configurable": {
            "thread_id": thread_id,
            "actor_id": actor_id,
        }
    }
