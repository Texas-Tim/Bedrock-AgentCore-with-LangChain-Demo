"""
LangGraph + Bedrock AgentCore Demo with Memory

Demonstrates streaming with create_agent and AgentCore Memory persistence.
Requires an AgentCore Memory ID - create one in the AWS Console first.

Memory Integration Overview:
- AgentCore Memory provides persistent conversation state across sessions
- Memory is stored in AWS Bedrock and automatically managed by LangGraph
- Each conversation is identified by a unique thread_id
- Each user is identified by a unique actor_id
- Memory persists message history, tool calls, and agent state
"""

import logging
from typing import AsyncGenerator
from langchain_aws import ChatBedrock
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph_checkpoint_aws import AgentCoreMemorySaver

# Configure logging to track memory initialization status
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
REGION = "us-east-1"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

# Memory Configuration
# TODO: Replace with your AgentCore Memory ID from AWS Console
# To create a Memory resource:
# 1. Go to AWS Console > Bedrock > AgentCore > Memory
# 2. Click "Create Memory"
# 3. Copy the Memory ID and paste it here
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
)

# Initialize AgentCore Memory checkpointer with error handling
# AgentCoreMemorySaver is a LangGraph checkpointer that stores conversation state in AWS Bedrock
# 
# Parameters:
# - MEMORY_ID: The unique identifier for your Memory resource in AWS Bedrock
# - region_name: The AWS region where your Memory resource is located
#
# What gets persisted:
# - Complete message history (user messages and assistant responses)
# - Tool call history and results
# - Agent state and intermediate steps
# - Conversation context across multiple turns
#
# Memory is automatically saved after each agent turn and loaded at the start of each turn
#
# Error Handling:
# If Memory initialization fails (invalid ID, network issues, permissions, etc.),
# the agent will fall back to stateless mode (no memory persistence).
# This ensures the agent remains functional even if Memory is unavailable.
checkpointer = None
memory_enabled = False

try:
    # Attempt to initialize Memory checkpointer
    checkpointer = AgentCoreMemorySaver(MEMORY_ID, region_name=REGION)
    memory_enabled = True
    logger.info(f"Memory enabled: Successfully initialized with Memory ID: {MEMORY_ID}")
except Exception as e:
    # Memory initialization failed - agent will run without persistence
    # Common failure reasons:
    # - Invalid or missing MEMORY_ID
    # - AWS credentials not configured
    # - Insufficient IAM permissions for bedrock-agent-runtime:GetMemory/PutMemory
    # - Network connectivity issues
    # - Memory resource doesn't exist in the specified region
    logger.warning(
        f"Memory initialization failed: {e}. "
        f"Agent will run in stateless mode (no conversation persistence)."
    )
    checkpointer = None
    memory_enabled = False

# Create the agent with memory (if available) using langgraph.prebuilt.create_react_agent
# The checkpointer parameter enables automatic state persistence
# 
# With checkpointer (memory_enabled=True):
# - Agent maintains conversation history across calls
# - State is persisted to AWS Bedrock after each turn
# - Previous messages and context are loaded automatically
#
# Without checkpointer (memory_enabled=False, fallback mode):
# - Agent is stateless - no memory between calls
# - Each call is independent with no conversation history
# - Agent still functions normally, just without persistence
agent = create_react_agent(
    model=llm,
    tools=tools,
    prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,  # None if memory initialization failed
)


async def stream_response(
    prompt: str,
    actor_id: str = "default-user",
    thread_id: str = "default-session",
) -> AsyncGenerator[str, None]:
    """
    Stream agent response with memory persistence.
    
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
    
    Memory Persistence Flow:
    ------------------------
    1. Agent receives prompt with thread_id and actor_id in config
    2. AgentCoreMemorySaver loads existing memory for this thread_id (if any)
    3. Agent processes the prompt with full conversation history
    4. Agent generates response and executes any tool calls
    5. AgentCoreMemorySaver automatically saves updated state to AWS Bedrock
    6. Next call with same thread_id will have access to this conversation history
    
    Usage Patterns:
    ---------------
    # Pattern 1: Single user, single session (simplest)
    async for token in stream_response("Hello", "user-1", "session-1"):
        print(token, end="")
    
    # Pattern 2: Single user, multiple sessions (e.g., different topics)
    async for token in stream_response("Tell me about Python", "user-1", "python-session"):
        print(token, end="")
    async for token in stream_response("Tell me about Java", "user-1", "java-session"):
        print(token, end="")
    
    # Pattern 3: Multi-user support (each user has isolated memory)
    async for token in stream_response("Hello", f"user-{user_id}", f"session-{session_id}"):
        print(token, end="")
    
    # Pattern 4: Session management (new session = fresh start)
    session_id = generate_new_session_id()
    async for token in stream_response("Start fresh", "user-1", f"session-{session_id}"):
        print(token, end="")
    """
    input_data = {"messages": [{"role": "user", "content": prompt}]}

    # Config for memory persistence
    # The "configurable" dict is passed to the AgentCoreMemorySaver checkpointer
    # to identify which conversation thread to load/save
    config = {
        "configurable": {
            # thread_id: Identifies the conversation thread
            # - Memory is loaded from and saved to this thread
            # - Different thread_ids maintain separate conversation histories
            # - Use consistent thread_id to continue a conversation
            # - Use new thread_id to start a fresh conversation
            "thread_id": thread_id,
            
            # actor_id: Identifies the user/actor
            # - Used for access control and user isolation
            # - Enables tracking which user is interacting with the agent
            # - Important for multi-user applications
            "actor_id": actor_id,
        }
    }

    # Stream the agent's response
    # The agent automatically loads memory for this thread_id before processing
    # and saves updated memory after generating the response
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
    print(f"Memory Status: {'ENABLED' if memory_enabled else 'DISABLED (running in stateless mode)'}")
    if not memory_enabled:
        print("⚠️  Memory initialization failed - agent will not remember previous conversations")
    print("Type 'quit' to exit\n")

    # Example: Single user, single session
    # All messages in this demo will be part of the same conversation thread
    # The agent will remember previous messages and maintain context
    actor_id = "demo-user"
    thread_id = "demo-session-1"
    
    # To test memory persistence:
    # 1. Run this script and have a conversation
    # 2. Exit the script (Ctrl+C or type 'quit')
    # 3. Run the script again with the same thread_id
    # 4. The agent will remember your previous conversation!
    #
    # To start a fresh conversation:
    # - Change thread_id to a new value (e.g., "demo-session-2")
    #
    # To simulate multiple users:
    # - Use different actor_id values for each user
    # - Each user can have their own thread_id values

    while True:
        try:
            prompt = input("You: ").strip()
            if prompt.lower() in ("quit", "exit", "q"):
                break
            if not prompt:
                continue

            print("Assistant: ", end="", flush=True)
            # Stream the response with memory persistence
            # The agent will remember all previous messages in this thread
            async for token in stream_response(prompt, actor_id, thread_id):
                print(token, end="", flush=True)
            print("\n")

        except KeyboardInterrupt:
            break

    print("\nGoodbye!")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
