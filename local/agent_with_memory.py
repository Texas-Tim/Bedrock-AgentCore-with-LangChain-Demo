"""
LangGraph + Bedrock AgentCore Demo with Memory

Demonstrates streaming with create_agent and AgentCore Memory persistence.
Requires an AgentCore Memory ID - create one in the AWS Console first.
"""

from typing import AsyncGenerator
from langchain_aws import ChatBedrock
from langchain_core.tools import tool
from langchain.agents import create_agent
from langgraph_checkpoint_aws import AgentCoreMemorySaver

# Configuration
REGION = "us-east-1"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

# TODO: Replace with your AgentCore Memory ID from AWS Console
MEMORY_ID = "YOUR_MEMORY_ID"

SYSTEM_PROMPT = """You are a helpful assistant with memory capabilities.
You can remember previous conversations and user preferences.
Be concise and helpful in your responses."""


# Example tools
@tool
def get_weather(location: str) -> str:
    """Get the current weather for a location."""
    return f"The weather in {location} is 72°F and sunny."


@tool
def search_knowledge_base(query: str) -> str:
    """Search the knowledge base for information."""
    return f"Found information about: {query}"


tools = [get_weather, search_knowledge_base]

# Initialize LLM
llm = ChatBedrock(
    model_id=MODEL_ID,
    region_name=REGION,
    call_handler=None
)

# Initialize AgentCore Memory checkpointer for state persistence
checkpointer = AgentCoreMemorySaver(MEMORY_ID, region_name=REGION)

# Create the agent with memory using langchain.agents.create_agent
agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)


async def stream_response(
    prompt: str,
    actor_id: str = "default-user",
    thread_id: str = "default-session",
) -> AsyncGenerator[str, None]:
    """Stream agent response with memory persistence."""
    input_data = {"messages": [{"role": "user", "content": prompt}]}

    # Config for memory persistence
    config = {
        "configurable": {
            "thread_id": thread_id,
            "actor_id": actor_id,
        }
    }

    async for event in agent.astream(input_data, config=config, stream_mode="messages"):
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


async def main():
    import sys

    if MEMORY_ID == "YOUR_MEMORY_ID":
        print("ERROR: Please set MEMORY_ID to your AgentCore Memory ID")
        print("Create one in the AWS Console: Bedrock > AgentCore > Memory")
        sys.exit(1)

    print("LangGraph + Bedrock AgentCore Demo (with Memory)")
    print("=" * 50)
    print(f"Memory ID: {MEMORY_ID}")
    print("Type 'quit' to exit\n")

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

    print("\nGoodbye!")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
