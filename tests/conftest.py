"""
Pytest configuration and shared fixtures.
"""

import os
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_env_vars():
    """Fixture to set up mock environment variables."""
    env_vars = {
        "AWS_REGION": "us-east-1",
        "BEDROCK_GUARDRAIL_ID": "gr-test123456",
        "BEDROCK_GUARDRAIL_VERSION": "1",
        "BEDROCK_KNOWLEDGE_BASE_ID": "KB-test123456",
        "BEDROCK_MEMORY_ID": "MEM-test123456",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars


@pytest.fixture
def mock_env_vars_minimal():
    """Fixture with minimal environment variables (no features enabled)."""
    env_vars = {
        "AWS_REGION": "us-east-1",
    }
    # Clear feature-related env vars
    clear_vars = [
        "BEDROCK_GUARDRAIL_ID",
        "BEDROCK_GUARDRAIL_VERSION", 
        "BEDROCK_KNOWLEDGE_BASE_ID",
        "BEDROCK_MEMORY_ID",
    ]
    with patch.dict(os.environ, env_vars, clear=False):
        for var in clear_vars:
            os.environ.pop(var, None)
        yield env_vars


@pytest.fixture
def mock_bedrock_client():
    """Fixture for mocked Bedrock client."""
    with patch("boto3.client") as mock_client:
        yield mock_client


@pytest.fixture
def mock_retriever():
    """Fixture for mocked AmazonKnowledgeBasesRetriever."""
    with patch("langchain_aws.AmazonKnowledgeBasesRetriever") as mock:
        yield mock


@pytest.fixture
def mock_memory_saver():
    """Fixture for mocked AgentCoreMemorySaver."""
    with patch("langgraph_checkpoint_aws.AgentCoreMemorySaver") as mock:
        yield mock


@pytest.fixture
def sample_documents():
    """Fixture providing sample document results."""
    class MockDocument:
        def __init__(self, content: str):
            self.page_content = content
    
    return [
        MockDocument("This is the first result about AcmeCorp products."),
        MockDocument("This is the second result about pricing."),
        MockDocument("This is the third result about support."),
    ]
