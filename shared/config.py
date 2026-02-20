"""
Configuration management with Pydantic validation.

This module provides type-safe configuration loading and validation
for all Bedrock Agents features (GuardRails, Knowledge Base, Memory).
"""

import os
import logging
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


class GuardRailsConfig(BaseModel):
    """Configuration for AWS Bedrock GuardRails."""
    
    guardrail_id: Optional[str] = Field(
        default=None,
        description="GuardRail resource ID from AWS Console"
    )
    guardrail_version: str = Field(
        default="DRAFT",
        description="Version number (e.g., '1') or 'DRAFT'"
    )
    
    @field_validator("guardrail_id", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: Optional[str]) -> Optional[str]:
        """Convert empty strings to None."""
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return v.strip()
    
    @model_validator(mode="after")
    def validate_version_when_id_present(self) -> "GuardRailsConfig":
        """Ensure version is provided when ID is set."""
        if self.guardrail_id and not self.guardrail_version:
            raise ValueError(
                "GuardRail version is required when GuardRail ID is set. "
                "Set BEDROCK_GUARDRAIL_VERSION to a version number or 'DRAFT'."
            )
        if self.guardrail_id and len(self.guardrail_id) < 5:
            raise ValueError(
                f"Invalid GuardRail ID format: '{self.guardrail_id}'. "
                "GuardRail IDs should be longer than 5 characters."
            )
        return self
    
    @property
    def enabled(self) -> bool:
        """Check if GuardRails is enabled."""
        return self.guardrail_id is not None


class KnowledgeBaseConfig(BaseModel):
    """Configuration for AWS Bedrock Knowledge Base."""
    
    knowledge_base_id: Optional[str] = Field(
        default=None,
        description="Knowledge Base resource ID from AWS Console"
    )
    num_results: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of results to retrieve"
    )
    
    @field_validator("knowledge_base_id", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: Optional[str]) -> Optional[str]:
        """Convert empty strings to None."""
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return v.strip()
    
    @model_validator(mode="after")
    def validate_id_format(self) -> "KnowledgeBaseConfig":
        """Validate Knowledge Base ID format."""
        if self.knowledge_base_id and len(self.knowledge_base_id) < 5:
            raise ValueError(
                f"Invalid Knowledge Base ID format: '{self.knowledge_base_id}'. "
                "Knowledge Base IDs should be longer than 5 characters."
            )
        return self
    
    @property
    def enabled(self) -> bool:
        """Check if Knowledge Base is enabled."""
        return self.knowledge_base_id is not None


class MemoryConfig(BaseModel):
    """Configuration for AWS Bedrock AgentCore Memory."""
    
    memory_id: Optional[str] = Field(
        default=None,
        description="Memory resource ID from AWS Console"
    )
    
    @field_validator("memory_id", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: Optional[str]) -> Optional[str]:
        """Convert empty strings to None."""
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return v.strip()
    
    @model_validator(mode="after")
    def validate_id_format(self) -> "MemoryConfig":
        """Validate Memory ID format."""
        if self.memory_id and len(self.memory_id) < 5:
            raise ValueError(
                f"Invalid Memory ID format: '{self.memory_id}'. "
                "Memory IDs should be longer than 5 characters."
            )
        return self
    
    @property
    def enabled(self) -> bool:
        """Check if Memory is enabled."""
        return self.memory_id is not None


class AgentConfig(BaseModel):
    """Complete agent configuration with all features."""
    
    # AWS Configuration
    region: str = Field(default="us-east-1", description="AWS region")
    model_id: str = Field(
        default="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        description="Bedrock model ID"
    )
    
    # Feature Configurations
    guardrails: GuardRailsConfig = Field(default_factory=GuardRailsConfig)
    knowledge_base: KnowledgeBaseConfig = Field(default_factory=KnowledgeBaseConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    
    # System Prompt
    system_prompt: str = Field(
        default="You are a helpful assistant.",
        description="System prompt for the agent"
    )
    
    def log_status(self) -> None:
        """Log the configuration status for all features."""
        logger.info("=" * 60)
        logger.info("Bedrock Agents Feature Status:")
        logger.info(f"  Region: {self.region}")
        logger.info(f"  Model: {self.model_id}")
        logger.info(f"  GuardRails: {'ENABLED' if self.guardrails.enabled else 'DISABLED'}")
        if self.guardrails.enabled:
            logger.info(f"    - ID: {self.guardrails.guardrail_id}")
            logger.info(f"    - Version: {self.guardrails.guardrail_version}")
        logger.info(f"  Knowledge Base: {'ENABLED' if self.knowledge_base.enabled else 'DISABLED'}")
        if self.knowledge_base.enabled:
            logger.info(f"    - ID: {self.knowledge_base.knowledge_base_id}")
            logger.info(f"    - Results: {self.knowledge_base.num_results}")
        logger.info(f"  Memory: {'ENABLED' if self.memory.enabled else 'DISABLED'}")
        if self.memory.enabled:
            logger.info(f"    - ID: {self.memory.memory_id}")
        logger.info("=" * 60)


def load_config(
    region: Optional[str] = None,
    model_id: Optional[str] = None,
    system_prompt: Optional[str] = None,
) -> AgentConfig:
    """
    Load agent configuration from environment variables.
    
    Args:
        region: Override AWS region (default: from env or us-east-1)
        model_id: Override model ID (default: from env or Claude Sonnet 4.5)
        system_prompt: Override system prompt
        
    Returns:
        AgentConfig: Validated configuration object
        
    Raises:
        ValueError: If configuration is invalid
    """
    return AgentConfig(
        region=region or os.getenv("AWS_REGION", "us-east-1"),
        model_id=model_id or os.getenv(
            "BEDROCK_MODEL_ID",
            "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
        ),
        system_prompt=system_prompt or "You are a helpful assistant.",
        guardrails=GuardRailsConfig(
            guardrail_id=os.getenv("BEDROCK_GUARDRAIL_ID"),
            guardrail_version=os.getenv("BEDROCK_GUARDRAIL_VERSION", "DRAFT"),
        ),
        knowledge_base=KnowledgeBaseConfig(
            knowledge_base_id=os.getenv("BEDROCK_KNOWLEDGE_BASE_ID"),
            num_results=int(os.getenv("BEDROCK_KB_NUM_RESULTS", "5")),
        ),
        memory=MemoryConfig(
            memory_id=os.getenv("BEDROCK_MEMORY_ID"),
        ),
    )
