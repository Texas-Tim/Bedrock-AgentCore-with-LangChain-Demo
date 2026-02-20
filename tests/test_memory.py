"""
Tests for Memory initialization.
"""

import pytest
from unittest.mock import MagicMock, patch

from shared.config import MemoryConfig
from shared.memory import get_memory_config


class TestInitializeMemory:
    """Tests for initialize_memory function."""
    
    def test_returns_none_when_disabled(self):
        """Should return (None, False) when Memory is disabled."""
        from shared.memory import initialize_memory
        config = MemoryConfig()
        checkpointer, success = initialize_memory(config, "us-east-1")
        
        assert checkpointer is None
        assert success is False
    
    def test_returns_checkpointer_when_enabled(self, mock_memory_saver):
        """Should return checkpointer when Memory is enabled."""
        from shared.memory import initialize_memory
        mock_saver = MagicMock()
        mock_memory_saver.return_value = mock_saver
        
        config = MemoryConfig(memory_id="MEM-test123456")
        checkpointer, success = initialize_memory(config, "us-east-1")
        
        assert checkpointer is mock_saver
        assert success is True
        mock_memory_saver.assert_called_once_with(
            "MEM-test123456",
            region_name="us-east-1",
        )
    
    @patch("langgraph_checkpoint_aws.AgentCoreMemorySaver")
    def test_handles_initialization_error(self, mock_saver_class):
        """Should handle initialization errors gracefully."""
        from shared.memory import initialize_memory
        mock_saver_class.side_effect = Exception("Connection failed")
        
        config = MemoryConfig(memory_id="MEM-test123456")
        checkpointer, success = initialize_memory(config, "us-east-1")
        
        assert checkpointer is None
        assert success is False


class TestGetMemoryConfig:
    """Tests for get_memory_config function."""
    
    def test_default_values(self):
        """Should use default values when not specified."""
        config = get_memory_config()
        
        assert config["configurable"]["actor_id"] == "default-user"
        assert config["configurable"]["thread_id"] == "default-session"
    
    def test_custom_actor_id(self):
        """Should use custom actor_id when specified."""
        config = get_memory_config(actor_id="user-123")
        
        assert config["configurable"]["actor_id"] == "user-123"
    
    def test_custom_thread_id(self):
        """Should use custom thread_id when specified."""
        config = get_memory_config(thread_id="session-456")
        
        assert config["configurable"]["thread_id"] == "session-456"
    
    def test_both_custom_values(self):
        """Should use both custom values when specified."""
        config = get_memory_config(
            actor_id="user-123",
            thread_id="session-456",
        )
        
        assert config["configurable"]["actor_id"] == "user-123"
        assert config["configurable"]["thread_id"] == "session-456"
    
    def test_returns_correct_structure(self):
        """Should return correct nested structure."""
        config = get_memory_config()
        
        assert "configurable" in config
        assert "actor_id" in config["configurable"]
        assert "thread_id" in config["configurable"]
