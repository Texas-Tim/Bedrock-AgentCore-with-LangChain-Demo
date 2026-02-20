"""
FastAPI server with streaming endpoint for LangGraph + Bedrock AgentCore.

Run with: uvicorn fastapi_server:app --reload --timeout-keep-alive 120

For production, configure appropriate timeouts:
    uvicorn fastapi_server:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 120
"""

import asyncio
import logging
import re
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from langchain_aws import ChatBedrock
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

REGION = "us-east-1"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

# Input validation limits
MAX_PROMPT_LENGTH = 10000  # Maximum characters in prompt
MIN_PROMPT_LENGTH = 1      # Minimum characters in prompt
STREAMING_TIMEOUT_SECONDS = 120  # Timeout for streaming responses

# Patterns that might indicate prompt injection attempts
SUSPICIOUS_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?)",
    r"disregard\s+(all\s+)?(previous|prior|above)",
    r"you\s+are\s+now\s+(a|an)\s+",
    r"new\s+instructions?:",
    r"system\s*:\s*",
]

SYSTEM_PROMPT = """You are a helpful assistant that can answer questions and use tools.
Be concise and helpful in your responses."""


# =============================================================================
# TOOLS
# =============================================================================

@tool
def get_weather(location: str) -> str:
    """Get the current weather for a location."""
    return f"The weather in {location} is 72°F and sunny."


@tool
def search_knowledge_base(query: str) -> str:
    """Search the knowledge base for information."""
    return f"Found information about: {query}"


tools = [get_weather, search_knowledge_base]

# =============================================================================
# LLM AND AGENT SETUP
# =============================================================================

llm = ChatBedrock(
    model_id=MODEL_ID,
    region_name=REGION,
)

agent = create_react_agent(
    model=llm,
    tools=tools,
    prompt=SYSTEM_PROMPT,
)

# =============================================================================
# FASTAPI APP
# =============================================================================

app = FastAPI(
    title="AgentCore Demo API",
    description="LangGraph + Bedrock AgentCore streaming API",
    version="1.0.0",
)

# Configure CORS - restrict in production
# TODO: Update allow_origins with your actual frontend domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# =============================================================================
# REQUEST VALIDATION
# =============================================================================

def check_suspicious_patterns(text: str) -> bool:
    """
    Check if text contains suspicious patterns that might indicate prompt injection.
    
    This is a basic heuristic check - not a complete security solution.
    GuardRails should be used for comprehensive content filtering.
    
    Args:
        text: The text to check
        
    Returns:
        True if suspicious patterns are found
    """
    text_lower = text.lower()
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


class ChatRequest(BaseModel):
    """Request model for chat endpoint with validation."""
    
    prompt: str = Field(
        ...,
        min_length=MIN_PROMPT_LENGTH,
        max_length=MAX_PROMPT_LENGTH,
        description="The user's message to the agent",
        examples=["What is the weather in Seattle?"],
    )
    stream: bool = Field(
        default=True,
        description="Whether to stream the response",
    )
    
    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        """Validate and sanitize the prompt."""
        # Strip leading/trailing whitespace
        v = v.strip()
        
        # Check minimum length after stripping
        if len(v) < MIN_PROMPT_LENGTH:
            raise ValueError(
                f"Prompt must be at least {MIN_PROMPT_LENGTH} character(s) after trimming whitespace"
            )
        
        # Check for null bytes (potential injection)
        if "\x00" in v:
            raise ValueError("Prompt contains invalid characters")
        
        # Log warning for suspicious patterns (but don't block - let GuardRails handle)
        if check_suspicious_patterns(v):
            logger.warning(
                "Suspicious pattern detected in prompt. "
                "Consider enabling GuardRails for content filtering."
            )
        
        return v


# =============================================================================
# STREAMING WITH TIMEOUT
# =============================================================================

async def generate_stream_with_timeout(
    prompt: str,
    timeout: float = STREAMING_TIMEOUT_SECONDS,
) -> AsyncGenerator[str, None]:
    """
    Generate streaming response with timeout protection.
    
    Args:
        prompt: The user's prompt
        timeout: Maximum time in seconds for the entire stream
        
    Yields:
        SSE-formatted response chunks
    """
    input_data = {"messages": [{"role": "user", "content": prompt}]}
    
    async def _stream():
        async for event in agent.astream(input_data, stream_mode="messages"):
            if isinstance(event, tuple) and len(event) >= 2:
                chunk, metadata = event[0], event[1]
                # Only yield AI model text responses, skip tool calls and tool results
                if metadata.get("langgraph_node") != "model":
                    continue
                if hasattr(chunk, "content") and chunk.content:
                    content = chunk.content
                    if isinstance(content, list):
                        for block in content:
                            # Only yield text blocks, skip tool_use blocks
                            if isinstance(block, dict) and block.get("type") == "text":
                                text = block.get("text", "")
                                if text:
                                    yield f"data: {text}\n\n"
                    elif isinstance(content, str) and content:
                        yield f"data: {content}\n\n"
        
        yield "data: [DONE]\n\n"
    
    try:
        # Wrap the stream with a timeout
        stream_task = _stream()
        async for chunk in stream_task:
            # Check timeout for each chunk
            try:
                yield chunk
            except asyncio.CancelledError:
                logger.warning("Stream cancelled by client")
                return
                
    except asyncio.TimeoutError:
        logger.error(f"Streaming response timed out after {timeout}s")
        yield f"data: [ERROR] Response timed out after {timeout} seconds\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"Error during streaming: {e}")
        yield "data: [ERROR] An error occurred\n\n"
        yield "data: [DONE]\n\n"


# =============================================================================
# ENDPOINTS
# =============================================================================

@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Chat endpoint with optional streaming.
    
    - Validates input prompt length and content
    - Supports streaming (SSE) and non-streaming responses
    - Includes timeout protection for streaming responses
    """
    try:
        if request.stream:
            return StreamingResponse(
                generate_stream_with_timeout(request.prompt),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # Disable nginx buffering
                },
            )
        else:
            # Non-streaming with timeout
            try:
                input_data = {"messages": [{"role": "user", "content": request.prompt}]}
                result = await asyncio.wait_for(
                    agent.ainvoke(input_data),
                    timeout=STREAMING_TIMEOUT_SECONDS,
                )
                return {"response": result["messages"][-1].content}
            except asyncio.TimeoutError:
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=f"Request timed out after {STREAMING_TIMEOUT_SECONDS} seconds",
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred processing your request",
        )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/config")
async def config():
    """Return current configuration limits (for client reference)."""
    return {
        "max_prompt_length": MAX_PROMPT_LENGTH,
        "min_prompt_length": MIN_PROMPT_LENGTH,
        "streaming_timeout_seconds": STREAMING_TIMEOUT_SECONDS,
    }
