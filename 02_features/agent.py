"""
Lab 2: LangGraph Agent with GuardRails, Knowledge Base & Memory

This agent builds on Lab 1 by adding:
- GuardRails: Content filtering and safety controls
- Knowledge Base: RAG for document retrieval
- Memory: Persistent conversation state

Prerequisites:
- Complete Lab 1 (deploy basic agent, create GuardRail, create Knowledge Base)
- Set environment variables: BEDROCK_GUARDRAIL_ID, BEDROCK_KNOWLEDGE_BASE_ID

AWS Documentation References ...
- LangChain docs (general): https://python.langchain.com/
- LangChain integrations (search for "AmazonKnowledgeBasesRetriever"): https://python.langchain.com/
- AWS Bedrock documentation: https://docs.aws.amazon.com/bedrock/latest/userguide/what-is-bedrock.html
- AWS Bedrock Knowledge Bases: https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-bases.html
- AWS Bedrock GuardRails / safety controls: https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html
- Bedrock AgentCore runtime (Agent deployment): https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html
- LangGraph Checkpointing: https://langchain-ai.github.io/langgraph/concepts/persistence/
"""

import os
import json
import logging
from typing import AsyncGenerator, Optional

from bedrock_agentcore.runtime import BedrockAgentCoreApp
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

# Attempt to load a local .env file for developer convenience (no-op in production)
# This makes it clear which environment variables the agent expects and allows
# local testing without setting global environment variables.
try:
    from dotenv import load_dotenv

    _local_dotenv = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(_local_dotenv):
        load_dotenv(_local_dotenv)
        logger.info("Loaded .env for local development")
    else:
        logger.debug("No .env file found; create agent/.env from .env.example for local testing")
except ImportError:
    pass

# ============================================================================
# CONFIGURATION
# ============================================================================

# AWS Region and Model Configuration
REGION = "us-east-1"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
GUARDRAIL_ID = os.getenv("BEDROCK_GUARDRAIL_ID")
GUARDRAIL_VERSION = os.getenv("BEDROCK_GUARDRAIL_VERSION", "DRAFT")
KNOWLEDGE_BASE_ID = os.getenv("BEDROCK_KNOWLEDGE_BASE_ID")
MEMORY_ID = os.getenv("BEDROCK_MEMORY_ID")

# Feature flags - enable features only when properly configured
# This allows graceful degradation if a feature isn't set up
ENABLE_GUARDRAILS = bool(GUARDRAIL_ID and str(GUARDRAIL_ID).strip())
ENABLE_KNOWLEDGE_BASE = bool(KNOWLEDGE_BASE_ID and str(KNOWLEDGE_BASE_ID).strip())
ENABLE_MEMORY = bool(MEMORY_ID and str(MEMORY_ID).strip())

# System prompt updated to reflect available capabilities
# The agent uses this to understand what features it has access to
SYSTEM_PROMPT = """You are a helpful assistant deployed on AWS Bedrock AgentCore with advanced capabilities:
- Content safety filtering via GuardRails
- Access to a knowledge base for document retrieval
- Memory to remember previous conversations

Be concise and helpful in your responses. Use the knowledge base tool when you need 
to answer questions based on specific documents or data sources."""

logger.info("=" * 60)
logger.info("Lab 2 Agent - Feature Status:")
logger.info(f"  GuardRails: {'ENABLED' if ENABLE_GUARDRAILS else 'DISABLED'}")
logger.info(f"  Knowledge Base: {'ENABLED' if ENABLE_KNOWLEDGE_BASE else 'DISABLED'}")
logger.info(f"  Memory: {'ENABLED' if ENABLE_MEMORY else 'DISABLED'}")
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

@tool 
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression. Example: calculate('2+2')"""
    try:
        # Security: Restrict eval() to only mathematical characters to prevent code injection
        allowed = set('0123456789+-*/.() ')
        if not all(c in allowed for c in expression):
            return "Error: Only basic math operations are allowed"
        result = eval(expression, {"__builtins__": {}}, {})
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {e}"

def create_knowledge_base_tool() -> Optional[callable]:
    """
    Create a Knowledge Base query tool if Knowledge Base is configured.
    
    This function creates a tool that queries AWS Bedrock Knowledge Bases for
    relevant documents using RAG (Retrieval Augmented Generation). The tool
    uses vector similarity search to find documents matching the query.
    
    This tool is only created if KNOWLEDGE_BASE_ID is set.

    Docs: https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-retrieve.html
    """

    if not ENABLE_KNOWLEDGE_BASE:
        return None
    
    @tool
    def query_knowledge_base(query: str) -> str:
        """
        Search the knowledge base for relevant information using RAG.
        
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
            results = retriever.invoke(query)
            
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
            # See Botocore exceptions reference for common AWS error codes:
            # https://botocore.amazonaws.com/v1/documentation/api/latest/guide/exceptions.html
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
tools = [get_weather, calculate]
kb_tool = create_knowledge_base_tool()
if kb_tool:
    tools.append(kb_tool)

# ============================================================================
# GUARDRAILS CONFIGURATION
# ============================================================================
# GuardRails are configured at the LLM level and automatically filter both
# user inputs and model outputs. When content violates a policy, Bedrock
# raises an exception that we handle gracefully in the handle_request function.

if ENABLE_GUARDRAILS:
    # trace="enabled" logs guardrail decisions for debugging
    # Docs: https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-trace.html
    guardrails_config = {
        "guardrailIdentifier": GUARDRAIL_ID,
        "guardrailVersion": GUARDRAIL_VERSION,
        "trace": "enabled"
    }
    logger.info(f"GuardRails config: (ID: {GUARDRAIL_ID}, Version: {GUARDRAIL_VERSION})")

if guardrails_config:
    llm = ChatBedrock(
        model_id=MODEL_ID,
        region_name=REGION,
        guardrails=guardrails_config,  # Optional: None or GuardRails config dict
    )
else:
    llm = ChatBedrock(
        model_id=MODEL_ID,
        region_name=REGION,
    )
logger.info(f"LLM initialized: {MODEL_ID} in {REGION}")

# ============================================================================
# MEMORY (Conversation Persistence)
# ============================================================================
# AgentCoreMemorySaver provides persistent conversation memory using AgentCore's
# Memory service. This enables:
#     - Multi-turn conversations that remember context
#     - Session persistence across agent restarts
#     - User-specific conversation history
# Docs: https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-memory.html
# LangGraph Checkpointing: https://langchain-ai.github.io/langgraph/concepts/persistence 

checkpointer = None
if ENABLE_MEMORY:
    try:
        # Attempt to initialize Memory checkpointer
        checkpointer = AgentCoreMemorySaver(MEMORY_ID, region_name=REGION)
        logger.info(f"Memory: Successfully initialized (ID: {MEMORY_ID})")
    except Exception as e:
        # Memory initialization failed - agent will run without persistence
        # Gracefully degrade to a stateless mode if memory fails
        logger.warning(f"Memory initialization failed: {e}. Running stateless.")

agent = create_react_agent(
    model=llm,
    tools=tools,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,  # None if memory is disabled or initialization failed
)

app = BedrockAgentCoreApp()


@app.entrypoint
async def handle_request(payload: dict, **kwargs) -> AsyncGenerator[str, None]:
    """
    Parameters:
    -----------
    payload : dict
        Request payload from AgentCore Runtime containing:
        - prompt: The user's input message (required)
        - actor_id: Unique identifier for the user/actor (optional, default: "default-user")
        - thread_id: Unique identifier for the conversation thread (optional, default: "default-session")
        
    **kwargs : dict
        Additional arguments from BedrockAgentCoreApp (unused)
    
    Yields:
        str: Response tokens from the agent, or error message if intervention occurs
    """
    # Extract prompt from payload
    prompt = payload.get("prompt", "")
    
    if not prompt:
        yield json.dumps({"error": "No prompt provided"})
        return
    
    # Extract Memory configuration from payload
    # These parameters identify which conversation thread to load/save
    # - actor_id: Identifies the user (for multi-user support)
    # - thread_id: Identifies the conversation session
    actor_id = payload.get("actor_id", "default-user")
    thread_id = payload.get("thread_id")

    if not thread_id:
        import uuid 
        thread_id = f"stateless-{uuid.uuid4()}"
        logger.info(f"No thread_id provided, using stateless mode: {thread_id}")
    
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
        async for event in agent.astream(input_data, config=config, stream_mode="messages"):
            if isinstance(event, tuple) and len(event) >= 2:
                chunk, metadata = event[0], event[1]
                # Only yield AI model text responses, skip tool calls and tool results
                # This ensures we only stream the final response to the user
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
        error_msg = str(e).lower()
        
        # Check if this is a GuardRails intervention
        # Common keywords: "guardrail", "intervention", "blocked", "content policy"
        if any(keyword in error_msg for keyword in ["guardrail", "intervention", "blocked"]):
            logger.warning(
                f"GuardRails intervention occurred. "
                f"GuardRail ID: {GUARDRAIL_ID}, "
                f"Prompt preview: {prompt[:100]}..."
            )
            yield (
                "I apologize, but I cannot provide that response as it violates "
                "content safety policies. Please rephrase your request or ask "
                "something different."
            )
        else:
            # ================================================================
            # OTHER ERROR HANDLING
            # ================================================================
            # For non-GuardRails errors, log the full error and return generic error
            # This includes:
            # - Network errors
            # - AWS credential errors
            # - LLM errors
            # - Tool execution errors
            logger.error(f"Error during agent streaming: {e}", exc_info=True)
            yield json.dumps({"error": "An error occurred processing your request"})


# ============================================================================
# LOCAL DEVELOPMENT SUPPORT
# ============================================================================

# For local development and testing
# Run this file directly to start a local development server
if __name__ == "__main__":
    app.run()
