"""
Lab 1: Basic LangGraph Agent for Bedrock AgentCore

This is a minimal agent that demonstrates:
- BedrockAgentCoreApp wrapper for deployment
- ChatBedrock LLM connection
- LangGraph's create_react_agent pattern
- Streaming response handling

AWS Documentation References:
- Amazon Bedrock AgentCore: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-get-started-toolkit.html
- Amazon Bedrock Models: https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html
- LangChain AWS Integration: https://docs.langchain.com/oss/python/integrations/providers/aws
"""

import json
import logging
from typing import AsyncGenerator
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from langchain_aws import ChatBedrock
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent 

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========================================================================
# Configuration
# ========================================================================
REGION = "us-east-1"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
SYSTEM_PROMPT = """You are a helpful assistant deployed on AWS Bedrock AgentCore.
You can answer questions and use tools to help users.
Be concise and helpful in your responses."""



# ========================================================================
# Tools
# ========================================================================
# Tools extend the agent's capabilities beyond text generation
# The agent decides when to call tools based on user queries and tool descriptions
# Each tool must have:
#   1. A clear function name
#   2. Type hints for parameters
#   3. A docstring expaining what it does (the agent reads this)
# Docs: https://python.langchain.com/docs/how_to/custom_tools/

@tool
def get_weather(location: str) -> str:
    """Get the current weather for a location."""
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


# ========================================================================
# Agent Setup
# ========================================================================
llm = ChatBedrock(
    model_id=MODEL_ID,
    region_name=REGION,
    # Optional parameters you can configure:
    # streaming = True,      # Enable token streaming (default: True)
    # temperature=0.7,       # Control randomness (0-1)
    # max_tokens=4096,       # Maximum response length
    # Docs: https://docs.aws.amazon.com/bedrock/latest/userguide/inference-parameters.html
)

agent = create_react_agent(
    model=llm,
    tools=[get_weather, calculate],
    prompt=SYSTEM_PROMPT
)

# BedrockAgentCoreApp wraps your agent for deployment on AWS Bedrock AgentCore
# Docs: https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-deploy.html
app = BedrockAgentCoreApp()

# The @app.entrypoint decorator marks this function as the main request handler
# AgentCore routes all incoming requests to this function
# The function must be async and yield responses for streaming support
@app.entrypoint
async def handle_request(payload: dict, **kwargs) -> AsyncGenerator[str, None]:
    """
    Main handler for AgentCore Runtime requests.

    This is the main entry point for all agent invocations. It:
    1. Extracts the user prompt from the request payload
    2. Invokes the LangGraph agent with the prompt
    3. Streams response tokens back to the caller

    Args:
        payload: Request payload containing the user's prompt
        **kwargs: Additional arguments from BedrockAgentCoreApp
        
    Yields:
        str: Response tokens streamed from the agent
    """
    prompt = payload.get("prompt", "")

    if not prompt:
        yield json.dumps({"error": "No prompt provided"})
        return

    logger.info(f"Processing request: {prompt[:50]}...")

    # LangChain v1 uses dict format for messages
    input_data = {"messages": [{"role": "user", "content": prompt}]}

    try:
        async for event in agent.astream(input_data, stream_mode="messages"):
            if isinstance(event, tuple) and len(event) >= 2:

                chunk, metadata = event[0], event[1]
                if metadata.get("langgraph_node") != "agent":
                    continue

                if hasattr(chunk, "content") and chunk.content:
                    content = chunk.content
                    if isinstance(content, list):

                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                text = block.get("text", "")
                                if text:
                                    yield text
                    elif isinstance(content, str) and content:
                        yield content

    except Exception as e:
       # Log errors for debugging
        logger.error(f"Error processing request: {e}", exc_info=True)
        yield json.dumps({"error": "An error occurred processing your request"})

# ========================================================================
# Local Development
# ========================================================================

# When run directly, start a local development server.
# This allows testing the agent locally before deploying to AgentCore
# Use: python agent.py
# Then test with: python invoke_agent.py
if __name__ == "__main__":
    app.run()
