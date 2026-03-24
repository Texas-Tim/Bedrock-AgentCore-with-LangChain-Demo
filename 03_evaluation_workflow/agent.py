"""
Lab 3: LangGraph Agent for Observability & Evaluation

This agent is identical to Lab 1, but deployed separately for observability testing.
AgentCore automatically provides tracing and metrics when deployed

IMPORTANT: For AgentCore Evaluations to work, LangChain must be instrumented with OpenTelemetry.
The Evaluate API requires spans with scope 'opentelemetry.instrumentation.langchain'

Usage:
    # Deploy to AgentCore
    agentcore configure -e agent.py -n langgraph_eval_agent -r us-east-1 --non-interactive
    agentcore launch

    # Test
    agentcore invoke '{"prompt": "What is the weather in Seattle?"}'


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
from typing import AsyncGenerator
from opentelemetry.instrumentation.langchain import LangchainInstrumentor

# AgentCore Evaluations requires spans with specific scopes:
#     - 'opentelemetry.instrumentation.langchain'
#     - 'openinference.instrumentation.langchain'
#     - 'strands.telemetry.tracer'

# We use opentelemetry-instrumentation-langchain which produces spans with the 
# correct scope.
# Docs: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/getting-started-on-demand.html

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from langchain_aws import ChatBedrock
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

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

# System prompt updated to reflect available capabilities
# The agent uses this to understand what features it has access to
SYSTEM_PROMPT = """You are a helpful assistant deployed on AWS Bedrock AgentCore.
You can answer questions and use tools to help users.
Be concise and helpful in your responses."""

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

# ============================================================================
# AGENT SETUP
# ============================================================================

llm = ChatBedrock(model_id=MODEL_ID, region_name=REGION)
tools = [get_weather, calculate]

agent = create_react_agent(
    model=llm,
    tools=tools,
    prompt=SYSTEM_PROMPT,
)

# ============================================================================
# AGENTCORE APP
# ============================================================================

app = BedrockAgentCoreApp()

@app.entrypoint
async def handle_request(payload: dict, **kwargs) -> AsyncGenerator[str, None]:
    """
    Handle incoming requests with automatic tracing via AgentCore
    """
    # Extract prompt from payload
    prompt = payload.get("prompt", "")
    
    if not prompt:
        yield json.dumps({"error": "No prompt provided"})
        return

    logger.info(f"Processing: {prompt[:50]}...")
    
    input_data = {"messages": [{"role": "user", "content": prompt}]}
    
    try:
        # Stream the agent's response
        async for event in agent.astream(input_data, stream_mode="messages"):
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
        logger.error(f"Error: {e}", exc_info=True)
        yield json.dumps({"error": "An error occurred processing your request"})


# ============================================================================
# LOCAL DEVELOPMENT SUPPORT
# ============================================================================

# For local development and testing
# Run this file directly to start a local development server
if __name__ == "__main__":
    app.run()
