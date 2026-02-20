"""
Knowledge Base tool creation with retry logic.

This module provides a factory function for creating Knowledge Base
query tools with proper error handling and retry logic.
"""

import logging
from typing import Callable, Optional, TYPE_CHECKING

from botocore.exceptions import ClientError
from langchain_core.tools import tool

from shared.config import KnowledgeBaseConfig
from shared.retry import RetryConfig, with_retry

if TYPE_CHECKING:
    from langchain_aws import AmazonKnowledgeBasesRetriever

logger = logging.getLogger(__name__)

# Retry configuration for Knowledge Base operations
KB_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=10.0,
    retryable_errors={
        "ThrottlingException",
        "ServiceUnavailableException",
        "InternalServerException",
    },
)


def format_kb_error(
    error: Exception,
    kb_id: str,
    region: str,
    query: str,
) -> str:
    """
    Format a Knowledge Base error into a user-friendly message.
    
    Args:
        error: The exception that occurred
        kb_id: Knowledge Base ID
        region: AWS region
        query: The query that failed
        
    Returns:
        User-friendly error message
    """
    if isinstance(error, ClientError):
        error_code = error.response.get("Error", {}).get("Code", "")
        
        if error_code == "ResourceNotFoundException":
            logger.error(
                f"Knowledge Base not found. ID: {kb_id}, Region: {region}"
            )
            return (
                f"Knowledge Base not found (ID: {kb_id}).\n"
                "Please verify:\n"
                "1. The Knowledge Base ID is correct\n"
                "2. The Knowledge Base exists in the AWS Bedrock Console\n"
                f"3. The Knowledge Base is in the {region} region\n"
                "4. Your IAM permissions allow access"
            )
        
        elif error_code == "ValidationException":
            logger.error(
                f"Knowledge Base query validation failed. "
                f"ID: {kb_id}, Query: {query[:50]}..., Error: {error}"
            )
            return (
                f"Invalid query format: {error}\n"
                "Please ensure the query is valid text and not too long."
            )
        
        elif error_code == "AccessDeniedException":
            logger.error(f"Access denied to Knowledge Base. ID: {kb_id}")
            return (
                "Access denied to Knowledge Base.\n"
                "Please verify your IAM permissions include:\n"
                "- bedrock:Retrieve on the Knowledge Base resource"
            )
        
        elif error_code == "ThrottlingException":
            logger.warning(f"Knowledge Base query throttled. ID: {kb_id}")
            return (
                "Knowledge Base query was throttled due to rate limits.\n"
                "Please try again in a moment."
            )
        
        else:
            logger.error(
                f"Knowledge Base AWS error. Code: {error_code}, Error: {error}"
            )
            return f"Knowledge Base service error: {error_code}\nDetails: {error}"
    
    # General exception
    logger.error(f"Unexpected Knowledge Base error: {error}")
    return (
        "An unexpected error occurred while searching the knowledge base.\n"
        f"Error: {error}"
    )


def create_knowledge_base_tool(
    config: KnowledgeBaseConfig,
    region: str,
    retry_config: Optional[RetryConfig] = None,
) -> Optional[Callable]:
    """
    Create a Knowledge Base query tool if configured.
    
    This function creates a LangChain tool that queries AWS Bedrock
    Knowledge Bases using RAG (Retrieval Augmented Generation).
    
    Args:
        config: Knowledge Base configuration
        region: AWS region
        retry_config: Optional retry configuration (uses defaults if not provided)
        
    Returns:
        Tool function if Knowledge Base is configured, None otherwise
    """
    if not config.enabled:
        logger.info("Knowledge Base tool: Not created (feature disabled)")
        return None
    
    kb_id = config.knowledge_base_id
    num_results = config.num_results
    retry_cfg = retry_config or KB_RETRY_CONFIG
    
    logger.info(f"Knowledge Base tool: Created (ID: {kb_id})")
    
    @tool
    def query_knowledge_base(query: str) -> str:
        """
        Search the knowledge base for relevant information using RAG.
        
        This tool queries an AWS Bedrock Knowledge Base to retrieve relevant
        documents based on semantic similarity. Use this when you need to
        answer questions based on specific documents or data sources.
        
        Args:
            query: The search query or question
            
        Returns:
            Formatted results from the knowledge base
        """
        # Lazy import to avoid requiring langchain_aws at module load time
        from langchain_aws import AmazonKnowledgeBasesRetriever
        
        @with_retry(retry_cfg)
        def _query() -> str:
            retriever = AmazonKnowledgeBasesRetriever(
                knowledge_base_id=kb_id,
                region_name=region,
                retrieval_config={
                    "vectorSearchConfiguration": {
                        "numberOfResults": num_results
                    }
                }
            )
            
            results = retriever.get_relevant_documents(query)
            
            if not results:
                return "No relevant information found in the knowledge base."
            
            formatted = []
            for i, doc in enumerate(results, 1):
                formatted.append(f"Result {i}:\n{doc.page_content}\n")
            
            return "\n".join(formatted)
        
        try:
            return _query()
        except Exception as e:
            return format_kb_error(e, kb_id, region, query)
    
    return query_knowledge_base
