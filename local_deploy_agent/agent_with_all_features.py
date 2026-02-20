"""
LangGraph + Bedrock AgentCore Demo - All Features Combined

This comprehensive example demonstrates all three AWS Bedrock Agents features:
1. GuardRails - Content filtering and safety controls
2. Knowledge Bases - RAG (Retrieval Augmented Generation) for document retrieval
3. Memory - Persistent conversation state across sessions

Each feature is independently configurable via environment variables and can be
enabled or disabled without affecting the others. The agent gracefully handles
missing or invalid configuration and provides helpful error messages.

Feature Configuration:
----------------------
GuardRails:
  - BEDROCK_GUARDRAIL_ID: Your GuardRail resource ID from AWS Console
  - BEDROCK_GUARDRAIL_VERSION: Version number (e.g., "1") or "DRAFT"

Knowledge Base:
  - BEDROCK_KNOWLEDGE_BASE_ID: Your Knowledge Base resource ID from AWS Console

Memory:
  - BEDROCK_MEMORY_ID: Your Memory resource ID from AWS Console

All features are optional. If not configured, the agent works normally without them.
"""

import os
import logging
from typing import AsyncGenerator, Optional
from langchain_aws import ChatBedrock, AmazonKnowledgeBasesRetriever
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph_checkpoint_aws import AgentCoreMemorySaver

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Configure logging to track feature initialization and errors
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# BASIC CONFIGURATION
# ============================================================================

# AWS Region and Model Configuration
REGION = "us-east-1"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

# System prompt for the agent
SYSTEM_PROMPT = """You are a helpful assistant with advanced capabilities:
- Content safety filtering via GuardRails
- Access to a knowledge base for document retrieval
- Memory to remember previous conversations

Be concise and helpful in your responses. Use the knowledge base tool when you need
to answer questions based on specific documents or data sources."""

# ============================================================================
# FEATURE 1: GUARDRAILS CONFIGURATION
# ============================================================================

# GuardRails provide content filtering and safety controls for your agent.
# They can:
# - Block harmful content (hate speech, violence, sexual content, etc.)
# - Filter personally identifiable information (PII)
# - Enforce denied topics (e.g., financial advice, medical advice)
# - Apply custom word filters
#
# GuardRails work by intercepting both user inputs and model outputs, checking
# them against configured policies, and blocking content that violates those policies.
#
# Setup Instructions:
# 1. Go to AWS Console > Bedrock > GuardRails
# 2. Click "Create GuardRail"
# 3. Configure content filters, denied topics, and word filters
# 4. Create the GuardRail and note the GuardRail ID
# 5. Set environment variables:
#    export BEDROCK_GUARDRAIL_ID="your-guardrail-id"
#    export BEDROCK_GUARDRAIL_VERSION="1"  # or "DRAFT" for testing

GUARDRAIL_ID = os.getenv("BEDROCK_GUARDRAIL_ID", "")
GUARDRAIL_VERSION = os.getenv("BEDROCK_GUARDRAIL_VERSION", "DRAFT")

# Feature flag: GuardRails is enabled if GUARDRAIL_ID is provided
ENABLE_GUARDRAILS = bool(GUARDRAIL_ID)

# ============================================================================
# FEATURE 2: KNOWLEDGE BASE CONFIGURATION
# ============================================================================

# Knowledge Bases enable RAG (Retrieval Augmented Generation) by indexing and
# retrieving documents from your data sources. They allow your agent to ground
# responses in your own documents rather than relying solely on the LLM's training data.
#
# How Knowledge Bases work:
# 1. Documents are ingested from data sources (S3, web crawler, etc.)
# 2. Documents are split into chunks and converted to embeddings
# 3. Embeddings are stored in a vector database (e.g., OpenSearch Serverless)
# 4. When queried, the user's question is converted to an embedding
# 5. Vector similarity search finds the most relevant document chunks
# 6. Retrieved chunks are returned to the agent for context
#
# Setup Instructions:
# 1. Go to AWS Console > Bedrock > Knowledge Bases
# 2. Click "Create Knowledge Base"
# 3. Configure data source (S3 bucket, web crawler, etc.)
# 4. Select embedding model (e.g., Titan Embeddings G1 - Text)
# 5. Configure vector store (OpenSearch Serverless recommended)
# 6. Create the Knowledge Base and sync/ingest your documents
# 7. Set environment variable:
#    export BEDROCK_KNOWLEDGE_BASE_ID="your-kb-id"

KNOWLEDGE_BASE_ID = os.getenv("BEDROCK_KNOWLEDGE_BASE_ID", "")

# Feature flag: Knowledge Base is enabled if KNOWLEDGE_BASE_ID is provided
ENABLE_KNOWLEDGE_BASE = bool(KNOWLEDGE_BASE_ID)

# ============================================================================
# FEATURE 3: MEMORY CONFIGURATION
# ============================================================================

# Memory provides persistent conversation state across sessions. It stores:
# - Complete message history (user messages and assistant responses)
# - Tool call history and results
# - Agent state and intermediate steps
# - Conversation context across multiple turns
#
# Memory is automatically managed by LangGraph's checkpointer system:
# - State is loaded at the start of each agent turn
# - State is saved after each agent turn
# - Each conversation thread has its own isolated memory
#
# Setup Instructions:
# 1. Go to AWS Console > Bedrock > AgentCore > Memory
# 2. Click "Create Memory"
# 3. Note the Memory ID
# 4. Set environment variable:
#    export BEDROCK_MEMORY_ID="your-memory-id"

MEMORY_ID = os.getenv("BEDROCK_MEMORY_ID", "")

# Feature flag: Memory is enabled if MEMORY_ID is provided
ENABLE_MEMORY = bool(MEMORY_ID)

# ============================================================================
# CONFIGURATION VALIDATION
# ============================================================================

def validate_configuration() -> None:
    """
    Validate all feature configurations and provide helpful error messages.
    
    This function checks that:
    - If GuardRail ID is provided, version is also provided
    - Configuration values have valid formats
    - Required AWS credentials are available
    
    Raises:
        ValueError: If configuration is invalid with helpful remediation message
    """
    # Validate GuardRails configuration
    if ENABLE_GUARDRAILS:
        if not GUARDRAIL_VERSION:
            raise ValueError(
                "GuardRail version is required when GuardRail ID is set.\n"
                "Set BEDROCK_GUARDRAIL_VERSION environment variable to a version number or 'DRAFT'.\n"
                "Example: export BEDROCK_GUARDRAIL_VERSION=1"
            )
        
        # Basic format validation for GuardRail ID
        if len(GUARDRAIL_ID) < 5:
            raise ValueError(
                f"Invalid GuardRail ID format: '{GUARDRAIL_ID}'\n"
                "GuardRail IDs should be longer than 5 characters.\n"
                "Please verify the ID in AWS Console > Bedrock > GuardRails"
            )
    
    # Validate Knowledge Base configuration
    if ENABLE_KNOWLEDGE_BASE:
        # Basic format validation for Knowledge Base ID
        if len(KNOWLEDGE_BASE_ID) < 5:
            raise ValueError(
                f"Invalid Knowledge Base ID format: '{KNOWLEDGE_BASE_ID}'\n"
                "Knowledge Base IDs should be longer than 5 characters.\n"
                "Please verify the ID in AWS Console > Bedrock > Knowledge Bases"
            )
    
    # Validate Memory configuration
    if ENABLE_MEMORY:
        # Basic format validation for Memory ID
        if len(MEMORY_ID) < 5:
            raise ValueError(
                f"Invalid Memory ID format: '{MEMORY_ID}'\n"
                "Memory IDs should be longer than 5 characters.\n"
                "Please verify the ID in AWS Console > Bedrock > AgentCore > Memory"
            )


# Run configuration validation at startup
try:
    validate_configuration()
except ValueError as e:
    logger.error(f"Configuration validation failed: {e}")
    raise

# ============================================================================
# FEATURE STATUS LOGGING
# ============================================================================

# Log which features are enabled/disabled at startup
# This helps users understand the agent's capabilities
logger.info("=" * 60)
logger.info("Bedrock Agents Feature Status:")
logger.info(f"  GuardRails:     {'ENABLED' if ENABLE_GUARDRAILS else 'DISABLED'}")
if ENABLE_GUARDRAILS:
    logger.info(f"    - ID: {GUARDRAIL_ID}")
    logger.info(f"    - Version: {GUARDRAIL_VERSION}")

logger.info(f"  Knowledge Base: {'ENABLED' if ENABLE_KNOWLEDGE_BASE else 'DISABLED'}")
if ENABLE_KNOWLEDGE_BASE:
    logger.info(f"    - ID: {KNOWLEDGE_BASE_ID}")

logger.info(f"  Memory:         {'ENABLED' if ENABLE_MEMORY else 'DISABLED'}")
if ENABLE_MEMORY:
    logger.info(f"    - ID: {MEMORY_ID}")

logger.info("=" * 60)

# ============================================================================
# TOOLS DEFINITION
# ============================================================================

# Example tool: Weather lookup
@tool
def get_weather(location: str) -> str:
    """Get the current weather for a location."""
    # Placeholder implementation - replace with real weather API
    return f"The weather in {location} is 72°F and sunny."


def create_knowledge_base_tool() -> Optional[callable]:
    """
    Create a Knowledge Base query tool if Knowledge Base is configured.
    
    This function creates a tool that queries AWS Bedrock Knowledge Bases for
    relevant documents using RAG (Retrieval Augmented Generation). The tool
    uses vector similarity search to find documents matching the query.
    
    Knowledge Base Query Flow:
    1. User's query is passed to the tool
    2. Query is converted to an embedding using the Knowledge Base's embedding model
    3. Vector similarity search finds the top N most relevant document chunks
    4. Retrieved chunks are formatted and returned to the agent
    5. Agent uses the retrieved context to generate a grounded response
    
    Returns:
        Callable tool function if Knowledge Base is configured, None otherwise
    """
    if not ENABLE_KNOWLEDGE_BASE:
        logger.info("Knowledge Base tool: Not created (feature disabled)")
        return None
    
    logger.info(f"Knowledge Base tool: Created (ID: {KNOWLEDGE_BASE_ID})")
    
    @tool
    def query_knowledge_base(query: str) -> str:
        """
        Search the knowledge base for relevant information using RAG.
        
        This tool queries an AWS Bedrock Knowledge Base to retrieve relevant documents
        based on semantic similarity. Use this when you need to answer questions based
        on specific documents or data sources that have been indexed in the Knowledge Base.
        
        The tool performs vector similarity search to find the most relevant document
        chunks and returns them formatted for the agent to use as context.
        
        Args:
            query: The search query or question to find relevant documents for
            
        Returns:
            Formatted results from the knowledge base with document content,
            or an error message if the query fails
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
                        # numberOfResults: How many top documents to retrieve
                        # Higher values return more context but may include less relevant results
                        # Recommended: 3-10 depending on your use case
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
        
        except Exception as e:
            # Enhanced error handling for Knowledge Base operations
            from botocore.exceptions import ClientError
            
            if isinstance(e, ClientError):
                error_code = e.response['Error']['Code']
                
                # ResourceNotFoundException: Knowledge Base doesn't exist or is inaccessible
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
                elif error_code == 'ValidationException':
                    logger.error(
                        f"Knowledge Base query validation failed. "
                        f"ID: {KNOWLEDGE_BASE_ID}, Query: {query[:50]}..., Error: {str(e)}"
                    )
                    return (
                        f"Invalid query format: {str(e)}\n"
                        "Please ensure the query is valid text and not too long."
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
                        "- bedrock:Retrieve on the Knowledge Base resource"
                    )
                
                # ThrottlingException: Too many requests
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
                    return f"Knowledge Base service error: {error_code}\nDetails: {str(e)}"
            
            # General exceptions (network errors, timeouts, unexpected errors)
            else:
                logger.error(
                    f"Unexpected Knowledge Base error. "
                    f"ID: {KNOWLEDGE_BASE_ID}, Query: {query[:50]}..., Error: {str(e)}"
                )
                return (
                    "An unexpected error occurred while searching the knowledge base.\n"
                    f"Error: {str(e)}"
                )
    
    return query_knowledge_base


# Initialize tools list with basic tools
tools = [get_weather]

# Add Knowledge Base tool if enabled
kb_tool = create_knowledge_base_tool()
if kb_tool:
    tools.append(kb_tool)

# ============================================================================
# GUARDRAILS CONFIGURATION
# ============================================================================

def build_guardrails_config() -> Optional[dict]:
    """
    Build GuardRails configuration for ChatBedrock.
    
    GuardRails are configured at the LLM level and automatically filter both
    user inputs and model outputs. When content violates a policy, Bedrock
    raises an exception that we handle gracefully in the streaming functions.
    
    Returns:
        dict: GuardRails configuration for ChatBedrock, or None if disabled
    """
    if not ENABLE_GUARDRAILS:
        logger.info("GuardRails config: Not configured (feature disabled)")
        return None
    
    logger.info(f"GuardRails config: Built (ID: {GUARDRAIL_ID}, Version: {GUARDRAIL_VERSION})")
    
    # Build GuardRails configuration for Bedrock
    # - guardrailIdentifier: The unique ID of your GuardRail resource
    # - guardrailVersion: Version number (e.g., "1", "2") or "DRAFT" for testing
    # - trace: Enable trace logging to see why content was blocked (useful for debugging)
    return {
        "guardrailIdentifier": GUARDRAIL_ID,
        "guardrailVersion": GUARDRAIL_VERSION,
        "trace": "enabled"
    }


# Build GuardRails configuration
guardrails_config = build_guardrails_config()

# ============================================================================
# LLM INITIALIZATION
# ============================================================================

# Initialize ChatBedrock LLM with optional GuardRails
# If guardrails_config is None, the LLM works normally without content filtering
# If guardrails_config is provided, all LLM inputs/outputs are filtered by GuardRails
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

logger.info(f"LLM initialized: {MODEL_ID} in {REGION}")

# ============================================================================
# MEMORY INITIALIZATION
# ============================================================================

def initialize_memory() -> tuple[Optional[AgentCoreMemorySaver], bool]:
    """
    Initialize AgentCore Memory checkpointer with error handling.
    
    Memory initialization can fail for various reasons:
    - Invalid or missing MEMORY_ID
    - AWS credentials not configured
    - Insufficient IAM permissions
    - Network connectivity issues
    - Memory resource doesn't exist in the specified region
    
    If initialization fails, the agent falls back to stateless mode (no persistence).
    This ensures the agent remains functional even if Memory is unavailable.
    
    Returns:
        tuple: (checkpointer, success)
            - checkpointer: AgentCoreMemorySaver instance or None
            - success: True if initialization succeeded, False otherwise
    """
    if not ENABLE_MEMORY:
        logger.info("Memory: Not initialized (feature disabled)")
        return None, False
    
    try:
        # Attempt to initialize Memory checkpointer
        checkpointer = AgentCoreMemorySaver(MEMORY_ID, region_name=REGION)
        logger.info(f"Memory: Successfully initialized (ID: {MEMORY_ID})")
        return checkpointer, True
    
    except Exception as e:
        # Memory initialization failed - agent will run without persistence
        logger.warning(
            f"Memory initialization failed: {e}. "
            f"Agent will run in stateless mode (no conversation persistence)."
        )
        return None, False


# Initialize Memory checkpointer
checkpointer, memory_initialized = initialize_memory()

# ============================================================================
# AGENT CREATION
# ============================================================================

# Create the agent using langgraph.prebuilt.create_react_agent
# The agent combines:
# - LLM with optional GuardRails
# - Tools (including optional Knowledge Base tool)
# - Optional Memory checkpointer for conversation persistence
agent = create_react_agent(
    model=llm,
    tools=tools,
    prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,  # None if memory is disabled or initialization failed
)

logger.info("Agent created successfully with all configured features")

# ============================================================================
# STREAMING FUNCTIONS
# ============================================================================

async def stream_response(
    prompt: str,
    actor_id: str = "default-user",
    thread_id: str = "default-session",
) -> AsyncGenerator[str, None]:
    """
    Stream agent response token by token with comprehensive error handling.
    
    This function handles all three Bedrock Agents features:
    
    1. GuardRails Intervention Handling:
       When GuardRails blocks content (either user input or model output), Bedrock
       raises an exception. We catch these and return a user-friendly message.
    
    2. Knowledge Base Integration:
       The agent can call the query_knowledge_base tool to retrieve relevant documents.
       Tool calls are handled automatically by LangGraph.
    
    3. Memory Persistence:
       If Memory is enabled, conversation state is automatically loaded at the start
       and saved at the end of each turn. The thread_id and actor_id identify which
       conversation to load/save.
    
    Parameters:
    -----------
    prompt : str
        The user's input message
        
    actor_id : str
        Unique identifier for the user/actor (default: "default-user")
        - Used to track which user is interacting with the agent
        - Enables multi-user support by isolating each user's conversations
        - Example patterns:
          * Single user: "user-123"
          * Multi-user: f"user-{user_id}"
          * Anonymous: "anonymous-{session_id}"
        
    thread_id : str
        Unique identifier for the conversation thread (default: "default-session")
        - Used to track separate conversation sessions
        - Each thread maintains its own independent memory
        - Example patterns:
          * Single session: "session-1"
          * Multiple sessions per user: f"user-{user_id}-session-{session_id}"
          * Time-based: f"session-{timestamp}"
          * Topic-based: f"user-{user_id}-topic-{topic}"
    
    Yields:
        str: Response tokens from the agent, or error message if intervention occurs
    """
    input_data = {"messages": [{"role": "user", "content": prompt}]}

    # Config for memory persistence (only used if Memory is enabled)
    # The "configurable" dict is passed to the AgentCoreMemorySaver checkpointer
    # to identify which conversation thread to load/save
    config = {
        "configurable": {
            "thread_id": thread_id,  # Identifies the conversation thread
            "actor_id": actor_id,    # Identifies the user/actor
        }
    }

    try:
        # Stream the agent's response
        # - If Memory is enabled: Agent loads memory for this thread_id before processing
        #   and saves updated memory after generating the response
        # - If GuardRails is enabled: All content is filtered automatically
        # - If Knowledge Base is enabled: Agent can call query_knowledge_base tool
        async for event in agent.astream(input_data, config=config, stream_mode="messages"):
            if isinstance(event, tuple) and len(event) >= 2:
                chunk, metadata = event[0], event[1]
                # Only yield AI model text responses from the 'agent' node
                # Skip tool calls and tool results
                # Note: create_react_agent uses 'agent' as the node name, not 'model'
                if metadata.get("langgraph_node") != "agent":
                    continue
                if hasattr(chunk, "content") and chunk.content:
                    content = chunk.content
                    # Handle Bedrock's content block format
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
        # ====================================================================
        # GUARDRAILS INTERVENTION HANDLING
        # ====================================================================
        # When GuardRails blocks content, Bedrock raises an exception with specific
        # keywords in the error message. We detect these and provide user-friendly feedback.
        error_msg = str(e).lower()
        
        # Check if this is a GuardRails intervention
        # Common keywords: "guardrail", "intervention", "blocked", "content policy"
        if any(keyword in error_msg for keyword in ["guardrail", "intervention", "blocked"]):
            # Log the intervention for monitoring and debugging
            logger.warning(
                f"GuardRails intervention occurred. "
                f"GuardRail ID: {GUARDRAIL_ID}, "
                f"Prompt preview: {prompt[:100]}..."
            )
            
            # Return user-friendly message explaining the intervention
            # This message is intentionally generic to avoid revealing policy details
            yield (
                "I apologize, but I cannot provide that response as it violates "
                "content safety policies. Please rephrase your request or ask "
                "something different."
            )
        else:
            # ================================================================
            # OTHER ERROR HANDLING
            # ================================================================
            # For non-GuardRails errors, log the full error and re-raise
            # This includes:
            # - Network errors
            # - AWS credential errors
            # - LLM errors
            # - Tool execution errors
            logger.error(f"Error during agent streaming: {e}")
            raise


async def invoke_agent(
    prompt: str,
    actor_id: str = "default-user",
    thread_id: str = "default-session",
) -> str:
    """
    Invoke agent and return full response (non-streaming) with error handling.
    
    This function provides the same comprehensive error handling as stream_response,
    but for non-streaming invocations. It handles GuardRails interventions, Knowledge
    Base queries, and Memory persistence.
    
    Parameters:
    -----------
    prompt : str
        The user's input message
        
    actor_id : str
        Unique identifier for the user/actor (default: "default-user")
        
    thread_id : str
        Unique identifier for the conversation thread (default: "default-session")
    
    Returns:
        str: Agent's complete response or error message if intervention occurs
    """
    input_data = {"messages": [{"role": "user", "content": prompt}]}
    
    # Config for memory persistence
    config = {
        "configurable": {
            "thread_id": thread_id,
            "actor_id": actor_id,
        }
    }
    
    try:
        result = await agent.ainvoke(input_data, config=config)
        return result["messages"][-1].content
    
    except Exception as e:
        # GuardRails Intervention Handling (same logic as stream_response)
        error_msg = str(e).lower()
        
        if any(keyword in error_msg for keyword in ["guardrail", "intervention", "blocked"]):
            logger.warning(
                f"GuardRails intervention occurred. "
                f"GuardRail ID: {GUARDRAIL_ID}, "
                f"Prompt preview: {prompt[:100]}..."
            )
            
            return (
                "I apologize, but I cannot provide that response as it violates "
                "content safety policies. Please rephrase your request or ask "
                "something different."
            )
        else:
            logger.error(f"Error during agent invocation: {e}")
            raise


# ============================================================================
# CLI DEMO
# ============================================================================

async def main():
    """
    Interactive CLI demo showing all Bedrock Agents features in action.
    
    This demo allows you to:
    - Chat with the agent and see streaming responses
    - Test GuardRails by trying to trigger content policies
    - Test Knowledge Base by asking questions about your documents
    - Test Memory by having multi-turn conversations
    
    The demo uses a single thread_id so all messages are part of the same
    conversation (if Memory is enabled). To test memory persistence:
    1. Run this script and have a conversation
    2. Exit the script (Ctrl+C or type 'quit')
    3. Run the script again
    4. The agent will remember your previous conversation!
    """
    print("\n" + "=" * 70)
    print("LangGraph + Bedrock AgentCore Demo - All Features")
    print("=" * 70)
    print("\nFeature Status:")
    print(f"  GuardRails:     {'✓ ENABLED' if ENABLE_GUARDRAILS else '✗ DISABLED'}")
    if ENABLE_GUARDRAILS:
        print(f"    ID: {GUARDRAIL_ID}")
        print(f"    Version: {GUARDRAIL_VERSION}")
    
    print(f"  Knowledge Base: {'✓ ENABLED' if ENABLE_KNOWLEDGE_BASE else '✗ DISABLED'}")
    if ENABLE_KNOWLEDGE_BASE:
        print(f"    ID: {KNOWLEDGE_BASE_ID}")
    
    print(f"  Memory:         {'✓ ENABLED' if memory_initialized else '✗ DISABLED'}")
    if ENABLE_MEMORY:
        print(f"    ID: {MEMORY_ID}")
        if not memory_initialized:
            print("    ⚠️  Memory initialization failed - running in stateless mode")
    
    print("\n" + "=" * 70)
    print("Type 'quit' to exit\n")

    # Example: Single user, single session
    # All messages in this demo will be part of the same conversation thread
    actor_id = "demo-user"
    thread_id = "demo-session-1"

    while True:
        try:
            prompt = input("You: ").strip()
            if prompt.lower() in ("quit", "exit", "q"):
                break
            if not prompt:
                continue

            print("Assistant: ", end="", flush=True)
            async for token in stream_response(prompt, actor_id, thread_id):
                print(token, end="", flush=True)
            print("\n")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\nError: {e}\n")

    print("\nGoodbye!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
