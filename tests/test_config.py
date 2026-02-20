"""
Tests for configuration management.
"""

import os
import pytest
from unittest.mock import patch

from shared.config import (
    AgentConfig,
    GuardRailsConfig,
    KnowledgeBaseConfig,
    MemoryConfig,
    load_config,
)


class TestGuardRailsConfig:
    """Tests for GuardRailsConfig."""
    
    def test_disabled_when_no_id(self):
        """GuardRails should be disabled when no ID is provided."""
        config = GuardRailsConfig()
        assert not config.enabled
        assert config.guardrail_id is None
    
    def test_disabled_when_empty_string(self):
        """GuardRails should be disabled when ID is empty string."""
        config = GuardRailsConfig(guardrail_id="")
        assert not config.enabled
        assert config.guardrail_id is None
    
    def test_disabled_when_whitespace_only(self):
        """GuardRails should be disabled when ID is whitespace only."""
        config = GuardRailsConfig(guardrail_id="   ")
        assert not config.enabled
        assert config.guardrail_id is None
    
    def test_enabled_when_valid_id(self):
        """GuardRails should be enabled when valid ID is provided."""
        config = GuardRailsConfig(
            guardrail_id="gr-test123456",
            guardrail_version="1",
        )
        assert config.enabled
        assert config.guardrail_id == "gr-test123456"
    
    def test_default_version_is_draft(self):
        """Default version should be DRAFT."""
        config = GuardRailsConfig(guardrail_id="gr-test123456")
        assert config.guardrail_version == "DRAFT"
    
    def test_invalid_id_format_raises_error(self):
        """Short ID should raise validation error."""
        with pytest.raises(ValueError, match="Invalid GuardRail ID format"):
            GuardRailsConfig(guardrail_id="gr", guardrail_version="1")
    
    def test_missing_version_raises_error(self):
        """Missing version when ID is set should raise error."""
        with pytest.raises(ValueError, match="version is required"):
            GuardRailsConfig(guardrail_id="gr-test123456", guardrail_version="")


class TestKnowledgeBaseConfig:
    """Tests for KnowledgeBaseConfig."""
    
    def test_disabled_when_no_id(self):
        """Knowledge Base should be disabled when no ID is provided."""
        config = KnowledgeBaseConfig()
        assert not config.enabled
    
    def test_enabled_when_valid_id(self):
        """Knowledge Base should be enabled when valid ID is provided."""
        config = KnowledgeBaseConfig(knowledge_base_id="KB-test123456")
        assert config.enabled
    
    def test_default_num_results(self):
        """Default number of results should be 5."""
        config = KnowledgeBaseConfig(knowledge_base_id="KB-test123456")
        assert config.num_results == 5
    
    def test_custom_num_results(self):
        """Custom number of results should be accepted."""
        config = KnowledgeBaseConfig(
            knowledge_base_id="KB-test123456",
            num_results=10,
        )
        assert config.num_results == 10
    
    def test_invalid_id_format_raises_error(self):
        """Short ID should raise validation error."""
        with pytest.raises(ValueError, match="Invalid Knowledge Base ID format"):
            KnowledgeBaseConfig(knowledge_base_id="KB")


class TestMemoryConfig:
    """Tests for MemoryConfig."""
    
    def test_disabled_when_no_id(self):
        """Memory should be disabled when no ID is provided."""
        config = MemoryConfig()
        assert not config.enabled
    
    def test_enabled_when_valid_id(self):
        """Memory should be enabled when valid ID is provided."""
        config = MemoryConfig(memory_id="MEM-test123456")
        assert config.enabled
    
    def test_invalid_id_format_raises_error(self):
        """Short ID should raise validation error."""
        with pytest.raises(ValueError, match="Invalid Memory ID format"):
            MemoryConfig(memory_id="MEM")


class TestAgentConfig:
    """Tests for AgentConfig."""
    
    def test_default_values(self):
        """Default configuration should have sensible defaults."""
        config = AgentConfig()
        assert config.region == "us-east-1"
        assert "claude" in config.model_id.lower()
        assert not config.guardrails.enabled
        assert not config.knowledge_base.enabled
        assert not config.memory.enabled
    
    def test_all_features_enabled(self):
        """All features should be configurable."""
        config = AgentConfig(
            region="us-west-2",
            guardrails=GuardRailsConfig(
                guardrail_id="gr-test123456",
                guardrail_version="1",
            ),
            knowledge_base=KnowledgeBaseConfig(
                knowledge_base_id="KB-test123456",
            ),
            memory=MemoryConfig(
                memory_id="MEM-test123456",
            ),
        )
        assert config.region == "us-west-2"
        assert config.guardrails.enabled
        assert config.knowledge_base.enabled
        assert config.memory.enabled


class TestLoadConfig:
    """Tests for load_config function."""
    
    def test_load_from_env_vars(self, mock_env_vars):
        """Configuration should load from environment variables."""
        config = load_config()
        assert config.region == "us-east-1"
        assert config.guardrails.enabled
        assert config.guardrails.guardrail_id == "gr-test123456"
        assert config.knowledge_base.enabled
        assert config.memory.enabled
    
    def test_load_minimal_config(self, mock_env_vars_minimal):
        """Configuration should work with minimal env vars."""
        config = load_config()
        assert config.region == "us-east-1"
        assert not config.guardrails.enabled
        assert not config.knowledge_base.enabled
        assert not config.memory.enabled
    
    def test_override_values(self, mock_env_vars):
        """Override values should take precedence."""
        config = load_config(
            region="eu-west-1",
            system_prompt="Custom prompt",
        )
        assert config.region == "eu-west-1"
        assert config.system_prompt == "Custom prompt"
