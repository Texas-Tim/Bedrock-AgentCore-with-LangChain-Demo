"""
LangGraph Agent for Bedrock AgentCore Runtime Deployment

Uses BedrockAgentCoreApp wrapper for compatibility with agentcore CLI.
"""

import os
import json
import logging
from typing import AsyncGenerator, Optional

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from langchain_aws import ChatBedrock, AmazonKnowledgeBasesRetriever
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
REGION = "us-east-1"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

# GuardRails Configuration
# GuardRails provide content filtering and safety controls for your agent.
# They can block harmful content, filter PII, enforce denied topics, and more.
# To use GuardRails:
# 1. Create a GuardRail in AWS Bedrock Console
# 2. Set BEDROCK_GUARDRAIL_ID environment variable to your GuardRail ID
# 3. Set BEDROCK_GUARDRAIL_VERSION environment variable to version number or "DRAFT"
GUARDRAIL_ID = os.getenv("BEDROCK_GUARDRAIL_ID", "")
GUARDRAIL_VERSION = os.getenv("BEDROCK_GUARDRAIL_VERSION", "DRAFT")

# Knowledge Base Configuration
# Knowledge Bases enable RAG (Retrieval Augmented Generation) by indexing and retrieving documents.
# They allow your agent to ground responses in your own data sources.
# To use Knowledge Bases:
# 1. Create a Knowledge Base in AWS Bedrock Console
# 2. Configure data source (S3, web crawler, etc.) and embedding model
# 3. Sync/ingest your documents into the Knowledge Base
# 4. Set BEDROCK_KNOWLEDGE_BASE_ID environment variable to your Knowledge Base ID
KNOWLEDGE_BASE_ID = os.getenv("BEDROCK_KNOWLEDGE_BASE_ID", "")

SYSTEM_PROMPT = """You are a helpful assistant deployed on AWS Bedrock AgentCore.
You can answer questions and use tools to help users.
Be concise and helpful in your responses."""


# Define tools
@tool
def get_weather(location: str) -> str:
    """Get the current weather for a location."""
    return f"The weather in {location} is 72°F and sunny."


def create_knowledge_base_tool():
    """
    Create a Knowledge Base query tool if Knowledge Base is configured.
    
    This function creates a tool that queries AWS Bedrock Knowledge Bases for
    relevant documents using RAG (Retrieval Augmented Generation). The tool
    uses vector similarity search to find documents matching the query.
    
    Knowledge Base Configuration:
    - The Knowledge Base must be created in AWS Bedrock Console first
    - Documents are indexed using an embedding model (e.g., Titan Embeddings)
    - The vector store (e.g., OpenSearch Serverless) stores document embeddings
    - Queries are converted to embeddings and matched against stored documents
    
    Returns:
        Callable tool function if Knowledge Base is configured, None otherwise
    """
    if not KNOWLEDGE_BASE_ID:
        logger.info("Knowledge Base: disabled (no BEDROCK_KNOWLEDGE_BASE_ID configured)")
        return None
    
    logger.info(f"Knowledge Base: enabled (ID: {KNOWLEDGE_BASE_ID})")
    
    @tool
    def query_knowledge_base(query: str) -> str:
        """
        Search the knowledge base for relevant information using RAG.
        
        This tool queries an AWS Bedrock Knowledge Base to retrieve relevant documents
        based on semantic similarity. Use this when you need to answer questions based
        on specific documents or data sources that have been indexed in the Knowledge Base.
        
        Args:
            query: The search query or question to find relevant documents for
            
        Returns:
            Formatted results from the knowledge base with document content
        """
        try:
            # Initialize the Knowledge Base retriever
            # AmazonKnowledgeBasesRetriever handles the vector search and document retrieval
            retriever = AmazonKnowledgeBasesRetriever(
                knowledge_base_id=KNOWLEDGE_BASE_ID,
                region_name=REGION,
                # Retrieval configuration controls how documents are searched and ranked
                retrieval_config={
                    "vectorSearchConfiguration": {
                        # numberOfResults: How many top documents to retrieve (default: 5)
                        # Higher values return more context but may include less relevant results
                        "numberOfResults": 5
                    }
                }
            )
            
            # Retrieve relevant documents using semantic similarity search
            # The query is converted to an embedding and matched against document embeddings
            results = retriever.get_relevant_documents(query)
            
            if not results:
                return "No relevant information found in the knowledge base."
            
            # Format results for the agent
            # Each result includes the document content and optional metadata
            formatted = []
            for i, doc in enumerate(results, 1):
                formatted.append(f"Result {i}:\n{doc.page_content}\n")
            
            return "\n".join(formatted)
        
        # Enhanced Error Handling for Knowledge Base Operations
        # AWS Bedrock Knowledge Base can fail for various reasons - we handle each
        # specifically to provide helpful guidance to users on how to fix issues.
        
        except Exception as e:
            # Import boto3 exceptions for specific error handling
            from botocore.exceptions import ClientError
            
            # Check if this is an AWS service error with specific error codes
            if isinstance(e, ClientError):
                error_code = e.response['Error']['Code']
                
                # ResourceNotFoundException: Knowledge Base ID doesn't exist or is inaccessible
                # This usually means:
                # 1. The Knowledge Base ID is incorrect or misspelled
                # 2. The Knowledge Base was deleted
                # 3. The Knowledge Base is in a different region
                # 4. IAM permissions don't allow access to this Knowledge Base
                if error_code == 'ResourceNotFoundException':
                    logger.error(
                        f"Knowledge Base not found. "
                        f"ID: {KNOWLEDGE_BASE_ID}, Region: {REGION}, Query: {query[:50]}..."
                    )
                    return (
                        f"Knowledge Base not found (ID: {KNOWLEDGE_BASE_ID}).\n"
                        "Please verify:\n"
                        "1. The Knowledge Base ID is correct in BEDROCK_KNOWLEDGE_BASE_ID\n"
                        "2. The Knowledge Base exists in the AWS Bedrock Console\n"
                        f"3. The Knowledge Base is in the {REGION} region\n"
                        "4. Your IAM permissions allow access to this Knowledge Base"
                    )
                
                # ValidationException: Query format or parameters are invalid
                # This usually means:
                # 1. The query string is empty or malformed
                # 2. The retrieval configuration has invalid parameters
                # 3. The query exceeds maximum length limits
                elif error_code == 'ValidationException':
                    logger.error(
                        f"Knowledge Base query validation failed. "
                        f"ID: {KNOWLEDGE_BASE_ID}, Query: {query[:50]}..., Error: {str(e)}"
                    )
                    return (
                        f"Invalid query format: {str(e)}\n"
                        "Please ensure:\n"
                        "1. The query is not empty and contains valid text\n"
                        "2. The query is not too long (max ~1000 characters)\n"
                        "3. The query doesn't contain special characters that need escaping"
                    )
                
                # AccessDeniedException: IAM permissions are insufficient
                elif error_code == 'AccessDeniedException':
                    logger.error(
                        f"Access denied to Knowledge Base. "
                        f"ID: {KNOWLEDGE_BASE_ID}, Region: {REGION}"
                    )
                    return (
                        "Access denied to Knowledge Base.\n"
                        "Please verify your IAM permissions include:\n"
                        "- bedrock:Retrieve on the Knowledge Base resource\n"
                        "- bedrock:InvokeModel for the embedding model"
                    )
                
                # ThrottlingException: Too many requests to Bedrock API
                elif error_code == 'ThrottlingException':
                    logger.warning(
                        f"Knowledge Base query throttled. "
                        f"ID: {KNOWLEDGE_BASE_ID}, Query: {query[:50]}..."
                    )
                    return (
                        "Knowledge Base query was throttled due to rate limits.\n"
                        "Please try again in a moment."
                    )
                
                # Other AWS service errors
                else:
                    logger.error(
                        f"Knowledge Base AWS service error. "
                        f"Code: {error_code}, ID: {KNOWLEDGE_BASE_ID}, Error: {str(e)}"
                    )
                    return (
                        f"Knowledge Base service error: {error_code}\n"
                        f"Details: {str(e)}"
                    )
            
            # General exceptions (network errors, timeouts, unexpected errors)
            else:
                logger.error(
                    f"Unexpected Knowledge Base error. "
                    f"ID: {KNOWLEDGE_BASE_ID}, Query: {query[:50]}..., Error: {str(e)}"
                )
                return (
                    "An unexpected error occurred while searching the knowledge base.\n"
                    f"Error: {str(e)}\n"
                    "Please check your network connection and AWS credentials."
                )
    
    return query_knowledge_base


# Initialize tools
tools = [get_weather]

# Add Knowledge Base tool if configured
kb_tool = create_knowledge_base_tool()
if kb_tool:
    tools.append(kb_tool)


def validate_guardrails_config() -> Optional[dict]:
    """
    Validate and build GuardRails configuration.
    
    GuardRails are optional - if not configured, the agent works normally.
    When configured, GuardRails provide:
    - Content filtering (hate speech, violence, sexual content, etc.)
    - PII detection and filtering
    - Denied topics enforcement
    - Custom word filters
    
    Returns:
        dict: GuardRails configuration for ChatBedrock, or None if not configured
        
    Raises:
        ValueError: If GuardRail ID is provided but version is missing
    """
    if not GUARDRAIL_ID:
        logger.info("GuardRails: disabled (no BEDROCK_GUARDRAIL_ID configured)")
        return None
    
    if not GUARDRAIL_VERSION:
        raise ValueError(
            "GuardRail version is required when GuardRail ID is set.\n"
            "Set BEDROCK_GUARDRAIL_VERSION environment variable to a version number or 'DRAFT'.\n"
            "Example: export BEDROCK_GUARDRAIL_VERSION=1"
        )
    
    logger.info(f"GuardRails: enabled (ID: {GUARDRAIL_ID}, Version: {GUARDRAIL_VERSION})")
    
    # Build GuardRails configuration for Bedrock
    # - guardrailIdentifier: The unique ID of your GuardRail resource
    # - guardrailVersion: Version number (e.g., "1", "2") or "DRAFT" for testing
    # - trace: Enable trace logging to see why content was blocked (useful for debugging)
    return {
        "guardrailIdentifier": GUARDRAIL_ID,
        "guardrailVersion": GUARDRAIL_VERSION,
        "trace": "enabled"
    }


# Validate and get GuardRails configuration
guardrails_config = validate_guardrails_config()

# Initialize LLM with optional GuardRails
# If guardrails_config is None, the LLM works normally without content filtering
# If guardrails_config is provided, all LLM responses will be filtered by GuardRails
#
# NOTE: We conditionally pass the guardrails parameter only when it's not None
# because langchain_aws has a bug where it tries to call .get() on None
# in the _identifying_params property.
if guardrails_config:
    llm = ChatBedrock(
        model_id=MODEL_ID,
        region_name=REGION,
        guardrails=guardrails_config,
    )
else:
    llm = ChatBedrock(
        model_id=MODEL_ID,
        region_name=REGION,
    )

# Create agent using langgraph.prebuilt.create_react_agent
agent = create_react_agent(
    model=llm,
    tools=tools,
    prompt=SYSTEM_PROMPT,
)

# Create BedrockAgentCoreApp
app = BedrockAgentCoreApp()


@app.entrypoint
async def handle_request(payload: dict, **kwargs) -> AsyncGenerator[str, None]:
    """
    Main handler for AgentCore Runtime requests.
    Streams responses using agent.astream() with GuardRails intervention handling.
    
    GuardRails Intervention Handling:
    When GuardRails blocks content (either user input or model output), Bedrock raises
    an exception. This function catches these exceptions and streams a user-friendly
    message explaining that content was blocked due to safety policies.
    
    GuardRails can intervene in two scenarios:
    1. Input intervention: User's prompt violates content policies
    2. Output intervention: Model's response violates content policies
    
    In both cases, we log the intervention for monitoring and stream a helpful message
    to the user without exposing internal error details. This ensures compatibility
    with the BedrockAgentCoreApp streaming contract.
    
    Args:
        payload: Request payload containing the user's prompt
        **kwargs: Additional arguments from BedrockAgentCoreApp
        
    Yields:
        str: Response tokens from the agent, or error message if intervention occurs
    """
    prompt = payload.get("prompt", "")

    if not prompt:
        yield json.dumps({"error": "No prompt provided"})
        return

    # LangChain v1 uses dict format for messages
    input_data = {"messages": [{"role": "user", "content": prompt}]}

    try:
        async for event in agent.astream(input_data, stream_mode="messages"):
            if isinstance(event, tuple) and len(event) >= 2:
                chunk, metadata = event[0], event[1]
                # Only yield AI model text responses from the 'agent' node
                # Skip tool calls and tool results
                # Note: create_react_agent uses 'agent' as the node name, not 'model'
                if metadata.get("langgraph_node") != "agent":
                    continue
                if hasattr(chunk, "content") and chunk.content:
                    content = chunk.content
                    if isinstance(content, list):
                        for block in content:
                            # Only yield text blocks, skip tool_use blocks
                            if isinstance(block, dict) and block.get("type") == "text":
                                text = block.get("text", "")
                                if text:
                                    yield text
                    elif isinstance(content, str) and content:
                        yield content

    except Exception as e:
        # GuardRails Intervention Handling
        # When GuardRails blocks content, Bedrock raises an exception with specific
        # keywords in the error message. We detect these and provide user-friendly feedback.
        error_msg = str(e).lower()
        
        # Check if this is a GuardRails intervention
        # Common keywords: "guardrail", "intervention", "blocked", "content policy"
        if any(keyword in error_msg for keyword in ["guardrail", "intervention", "blocked"]):
            # Log the intervention for monitoring and debugging
            # Include the first 100 characters of the prompt for context
            logger.warning(
                f"GuardRails intervention occurred. "
                f"GuardRail ID: {GUARDRAIL_ID}, "
                f"Prompt preview: {prompt[:100]}..."
            )
            
            # Stream user-friendly message explaining the intervention
            # This message is intentionally generic to avoid revealing policy details
            # We stream it as plain text to maintain compatibility with BedrockAgentCoreApp
            yield (
                "I apologize, but I cannot provide that response as it violates "
                "content safety policies. Please rephrase your request or ask "
                "something different."
            )
        else:
            # For non-GuardRails errors, log with full details and return generic error
            logger.error(f"Error during streaming: {e}", exc_info=True)
            yield json.dumps({"error": "An error occurred processing your request"})


# For local development
if __name__ == "__main__":
    app.run()
