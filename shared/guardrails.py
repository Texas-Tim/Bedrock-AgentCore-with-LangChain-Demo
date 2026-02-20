"""
GuardRails configuration and error handling.

This module provides utilities for configuring AWS Bedrock GuardRails
and handling GuardRails intervention errors.
"""

import logging
from typing import Optional

from shared.config import GuardRailsConfig

logger = logging.getLogger(__name__)

# Keywords that indicate a GuardRails intervention
GUARDRAILS_ERROR_KEYWORDS = frozenset([
    "guardrail",
    "intervention",
    "blocked",
    "content policy",
    "content filter",
])

# User-friendly message for GuardRails interventions
GUARDRAILS_INTERVENTION_MESSAGE = (
    "I apologize, but I cannot provide that response as it violates "
    "content safety policies. Please rephrase your request or ask "
    "something different."
)


def build_guardrails_config(config: GuardRailsConfig) -> Optional[dict]:
    """
    Build GuardRails configuration for ChatBedrock.
    
    GuardRails are configured at the LLM level and automatically filter
    both user inputs and model outputs.
    
    Args:
        config: GuardRails configuration
        
    Returns:
        GuardRails configuration dict for ChatBedrock, or None if disabled
    """
    if not config.enabled:
        logger.info("GuardRails config: Not configured (feature disabled)")
        return None
    
    logger.info(
        f"GuardRails config: Built "
        f"(ID: {config.guardrail_id}, Version: {config.guardrail_version})"
    )
    
    return {
        "guardrailIdentifier": config.guardrail_id,
        "guardrailVersion": config.guardrail_version,
        "trace": "enabled",
    }


def is_guardrails_error(error: Exception) -> bool:
    """
    Check if an exception is a GuardRails intervention.
    
    Args:
        error: The exception to check
        
    Returns:
        True if this is a GuardRails intervention
    """
    error_msg = str(error).lower()
    return any(keyword in error_msg for keyword in GUARDRAILS_ERROR_KEYWORDS)


def handle_guardrails_error(
    error: Exception,
    guardrail_id: Optional[str] = None,
    prompt_preview: Optional[str] = None,
) -> str:
    """
    Handle a GuardRails intervention error.
    
    Logs the intervention and returns a user-friendly message.
    
    Args:
        error: The GuardRails exception
        guardrail_id: Optional GuardRail ID for logging
        prompt_preview: Optional preview of the prompt for logging
        
    Returns:
        User-friendly error message
    """
    log_parts = ["GuardRails intervention occurred."]
    
    if guardrail_id:
        log_parts.append(f"GuardRail ID: {guardrail_id}")
    
    if prompt_preview:
        log_parts.append(f"Prompt preview: {prompt_preview[:100]}...")
    
    logger.warning(" ".join(log_parts))
    
    return GUARDRAILS_INTERVENTION_MESSAGE


def get_guardrails_intervention_message() -> str:
    """
    Get the standard GuardRails intervention message.
    
    Returns:
        User-friendly intervention message
    """
    return GUARDRAILS_INTERVENTION_MESSAGE
