"""
FastAPI server with streaming endpoint for LangGraph + Bedrock AgentCore.

Run with: uvicorn fastapi_server:app --reload
"""

from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_aws import ChatBedrock
from langchain_core.tools import tool
from langchain.agents import create_agent

# Configuration
REGION = "us-east-1"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

SYSTEM_PROMPT = """You are a helpful assistant that can answer questions and use tools.
Be concise and helpful in your responses."""


@tool
def get_weather(location: str) -> str:
    """Get the current weather for a location."""
    return f"The weather in {location} is 72°F and sunny."


@tool
def search_knowledge_base(query: str) -> str:
    """Search the knowledge base for information."""
    return f"Found information about: {query}"


tools = [get_weather, search_knowledge_base]

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

app = FastAPI(title="AgentCore Demo API")


class ChatRequest(BaseModel):
    prompt: str
    stream: bool = True


async def generate_stream(prompt: str) -> AsyncGenerator[str, None]:
    """Generate streaming response."""
    input_data = {"messages": [{"role": "user", "content": prompt}]}

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


@app.post("/chat")
async def chat(request: ChatRequest):
    """Chat endpoint with optional streaming."""
    if request.stream:
        return StreamingResponse(
            generate_stream(request.prompt),
            media_type="text/event-stream",
        )
    else:
        input_data = {"messages": [{"role": "user", "content": request.prompt}]}
        result = await agent.ainvoke(input_data)
        return {"response": result["messages"][-1].content}


@app.get("/health")
async def health():
    return {"status": "ok"}
