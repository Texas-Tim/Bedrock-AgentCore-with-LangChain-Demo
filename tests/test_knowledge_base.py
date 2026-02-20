"""
Tests for Knowledge Base tool creation.
"""

import pytest
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

from shared.config import KnowledgeBaseConfig


# Import format_kb_error directly since it doesn't require langchain_aws
def get_format_kb_error():
    """Lazy import of format_kb_error."""
    from shared.knowledge_base import format_kb_error
    return format_kb_error


class TestFormatKbError:
    """Tests for format_kb_error function."""
    
    def test_resource_not_found_error(self):
        """ResourceNotFoundException should return helpful message."""
        format_kb_error = get_format_kb_error()
        error = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Not found"}},
            "Retrieve",
        )
        result = format_kb_error(error, "KB-123", "us-east-1", "test query")
        
        assert "Knowledge Base not found" in result
        assert "KB-123" in result
        assert "us-east-1" in result
    
    def test_validation_exception(self):
        """ValidationException should return helpful message."""
        format_kb_error = get_format_kb_error()
        error = ClientError(
            {"Error": {"Code": "ValidationException", "Message": "Invalid query"}},
            "Retrieve",
        )
        result = format_kb_error(error, "KB-123", "us-east-1", "test query")
        
        assert "Invalid query format" in result
    
    def test_access_denied_exception(self):
        """AccessDeniedException should return helpful message."""
        format_kb_error = get_format_kb_error()
        error = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "Access denied"}},
            "Retrieve",
        )
        result = format_kb_error(error, "KB-123", "us-east-1", "test query")
        
        assert "Access denied" in result
        assert "IAM permissions" in result
    
    def test_throttling_exception(self):
        """ThrottlingException should return helpful message."""
        format_kb_error = get_format_kb_error()
        error = ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
            "Retrieve",
        )
        result = format_kb_error(error, "KB-123", "us-east-1", "test query")
        
        assert "throttled" in result
        assert "rate limits" in result
    
    def test_generic_exception(self):
        """Generic exceptions should return error message."""
        format_kb_error = get_format_kb_error()
        error = ValueError("Something went wrong")
        result = format_kb_error(error, "KB-123", "us-east-1", "test query")
        
        assert "unexpected error" in result.lower()
        assert "Something went wrong" in result


class TestCreateKnowledgeBaseTool:
    """Tests for create_knowledge_base_tool function."""
    
    def test_returns_none_when_disabled(self):
        """Should return None when Knowledge Base is disabled."""
        from shared.knowledge_base import create_knowledge_base_tool
        config = KnowledgeBaseConfig()
        tool = create_knowledge_base_tool(config, "us-east-1")
        assert tool is None
    
    @patch("shared.knowledge_base.AmazonKnowledgeBasesRetriever", create=True)
    def test_returns_tool_when_enabled(self, mock_retriever_class):
        """Should return tool function when Knowledge Base is enabled."""
        from shared.knowledge_base import create_knowledge_base_tool
        config = KnowledgeBaseConfig(knowledge_base_id="KB-test123456")
        tool = create_knowledge_base_tool(config, "us-east-1")
        assert tool is not None
        # LangChain tools are StructuredTool objects with an invoke method
        assert hasattr(tool, 'invoke') or callable(tool)
    
    @patch("shared.knowledge_base.AmazonKnowledgeBasesRetriever", create=True)
    def test_tool_has_correct_name(self, mock_retriever_class):
        """Tool should have correct name."""
        from shared.knowledge_base import create_knowledge_base_tool
        config = KnowledgeBaseConfig(knowledge_base_id="KB-test123456")
        tool = create_knowledge_base_tool(config, "us-east-1")
        assert tool.name == "query_knowledge_base"
    
    @patch("shared.knowledge_base.AmazonKnowledgeBasesRetriever", create=True)
    def test_tool_has_description(self, mock_retriever_class):
        """Tool should have a description."""
        from shared.knowledge_base import create_knowledge_base_tool
        config = KnowledgeBaseConfig(knowledge_base_id="KB-test123456")
        tool = create_knowledge_base_tool(config, "us-east-1")
        assert tool.description is not None
        assert len(tool.description) > 0
