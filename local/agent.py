"""
LangGraph + Bedrock AgentCore Demo

Demonstrates streaming with create_agent and AgentCore Memory integration.
"""

from typing import AsyncGenerator
from langchain_aws import ChatBedrock
from langchain_core.tools import tool
from langchain.agents import create_agent

# Configuration
REGION = "us-east-1"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

SYSTEM_PROMPT = """You are a helpful assistant that can answer questions and use tools.
Be concise and helpful in your responses."""


# Example tools
@tool
def get_weather(location: str) -> str:
    """Get the current weather for a location."""
    # Placeholder - replace with real implementation
    return f"The weather in {location} is 72°F and sunny."


@tool
def search_knowledge_base(query: str) -> str:
    """Search the knowledge base for information."""
    # Placeholder - replace with real implementation
    return f"Found information about: {query}"


# Initialize tools
tools = [get_weather, search_knowledge_base]

# Initialize LLM
llm = ChatBedrock(
    model_id=MODEL_ID,
    region_name=REGION,
)

# Create the agent using langchain.agents.create_agent
agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=SYSTEM_PROMPT,
)


async def stream_response(prompt: str) -> AsyncGenerator[str, None]:
    """Stream agent response token by token."""
    input_data = {"messages": [{"role": "user", "content": prompt}]}

    async for event in agent.astream(input_data, stream_mode="messages"):
        if isinstance(event, tuple) and len(event) >= 2:
            chunk, metadata = event[0], event[1]
            # Only yield AI model text responses, skip tool calls and tool results
            if metadata.get("langgraph_node") != "model":
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


async def invoke_agent(prompt: str) -> str:
    """Invoke agent and return full response (non-streaming)."""
    input_data = {"messages": [{"role": "user", "content": prompt}]}
    result = await agent.ainvoke(input_data)
    return result["messages"][-1].content


# CLI demo
async def main():
    import sys

    print("LangGraph + Bedrock AgentCore Demo")
    print("=" * 40)
    print("Type 'quit' to exit\n")

    while True:
        try:
            prompt = input("You: ").strip()
            if prompt.lower() in ("quit", "exit", "q"):
                break
            if not prompt:
                continue

            print("Assistant: ", end="", flush=True)
            async for token in stream_response(prompt):
                print(token, end="", flush=True)
            print("\n")

        except KeyboardInterrupt:
            break

    print("\nGoodbye!")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
