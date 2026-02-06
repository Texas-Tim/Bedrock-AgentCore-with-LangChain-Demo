"""
LangGraph Agent for Bedrock AgentCore Runtime Deployment

Uses BedrockAgentCoreApp wrapper for compatibility with agentcore CLI.
"""

import json
import logging
from typing import AsyncGenerator

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from langchain_aws import ChatBedrock
from langchain_core.tools import tool
from langchain.agents import create_agent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
REGION = "us-east-1"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

SYSTEM_PROMPT = """You are a helpful assistant deployed on AWS Bedrock AgentCore.
You can answer questions and use tools to help users.
Be concise and helpful in your responses."""


# Define tools
@tool
def get_weather(location: str) -> str:
    """Get the current weather for a location."""
    return f"The weather in {location} is 72°F and sunny."


@tool
def search_knowledge_base(query: str) -> str:
    """Search the knowledge base for information."""
    return f"Found information about: {query}"


tools = [get_weather, search_knowledge_base]

# Initialize LLM and agent
llm = ChatBedrock(
    model_id=MODEL_ID,
    region_name=REGION,
)

# Create agent using langchain.agents.create_agent
agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=SYSTEM_PROMPT,
)

# Create BedrockAgentCoreApp
app = BedrockAgentCoreApp()


@app.entrypoint
async def handle_request(payload: dict, **kwargs) -> AsyncGenerator[str, None]:
    """
    Main handler for AgentCore Runtime requests.
    Streams responses using agent.astream().
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
                                    yield text
                    elif isinstance(content, str) and content:
                        yield content

    except Exception as e:
        logger.error(f"Error during streaming: {e}", exc_info=True)
        yield json.dumps({"error": "An error occurred processing your request"})


# For local development
if __name__ == "__main__":
    app.run()
