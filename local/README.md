# Run LangGraph Agent Locally with AWS Bedrock

Run AI agents on your local machine using AWS Bedrock for LLM inference. Includes options for CLI, memory persistence, and HTTP API.

## Prerequisites

1. **AWS CLI** configured with credentials (`aws configure`)
2. **Bedrock Model Access** enabled for Claude Sonnet 4
3. **Python 3.10+**

## Step 1: Set Up Environment

```bash
cd agentcore_demo/local

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Verify AWS Access

Test that your credentials work with Bedrock:

```bash
aws bedrock list-foundation-models --region us-east-1 --query "modelSummaries[?contains(modelId, 'claude')].[modelId]" --output table
```

If this fails, check:
- AWS credentials are configured (`aws configure`)
- Bedrock model access is enabled in AWS Console

## Usage Options

### Option A: Basic CLI Agent

Interactive command-line agent with streaming responses:

```bash
python agent.py
```

Type your questions and see token-by-token streaming. Type `quit` or `exit` to stop.

### Option B: Agent with Memory Persistence

Conversations persist across sessions using AgentCore Memory:

**Setup:**
1. Go to [Bedrock Console](https://console.aws.amazon.com/bedrock) → AgentCore → Memory
2. Create a new Memory and copy the Memory ID
3. Edit `agent_with_memory.py` and set your `MEMORY_ID`:

```python
MEMORY_ID = "your-memory-id-here"
```

**Run:**
```bash
python agent_with_memory.py
```

Conversations are stored by `actor_id` and `thread_id`. Same IDs = continued conversation.

### Option C: FastAPI HTTP Server

REST API with Server-Sent Events (SSE) streaming:

```bash
# Start the server
uvicorn fastapi_server:app --reload
```

**Test streaming response:**
```bash
curl -N -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is the weather in Seattle?"}'
```

**Test non-streaming response:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello!", "stream": false}'
```

**Health check:**
```bash
curl http://localhost:8000/health
```

## Files

| File | Description |
|------|-------------|
| `agent.py` | Basic streaming agent with CLI interface |
| `agent_with_memory.py` | Agent with AgentCore Memory for persistence |
| `fastapi_server.py` | HTTP API with SSE streaming endpoint |
| `requirements.txt` | Python dependencies |

## Customizing the Agent

### Add Custom Tools

Edit any agent file to add your own tools:

```python
@tool
def search_database(query: str) -> str:
    """Search the database for information."""
    # Your implementation here
    return f"Results for: {query}"

# Add to tools list
tools = [get_weather, search_knowledge_base, search_database]
```

### Change the Model

Update `MODEL_ID` in the agent file:

```python
# Claude Sonnet 4 (default)
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

# Claude Haiku (faster, cheaper)
MODEL_ID = "us.anthropic.claude-3-haiku-20240307-v1:0"

# Claude Opus (most capable)
MODEL_ID = "us.anthropic.claude-3-opus-20240229-v1:0"
```

### Modify the System Prompt

```python
SYSTEM_PROMPT = """You are a helpful assistant specialized in...
Your custom instructions here."""
```

## Streaming Implementation

The agents use `stream_mode="messages"` for reliable streaming:

```python
async for event in agent.astream(input_data, stream_mode="messages"):
    if isinstance(event, tuple) and len(event) >= 2:
        chunk, metadata = event[0], event[1]
        # Only process AI model responses, skip tool calls
        if metadata.get("langgraph_node") == "model":
            if hasattr(chunk, "content") and chunk.content:
                # Handle streaming content
```

This pattern filters out tool call/result messages and only yields the final AI response.

## Troubleshooting

**"Could not connect to endpoint" errors:**
- Check AWS credentials: `aws sts get-caller-identity`
- Verify region matches your Bedrock access

**"Access denied to model" errors:**
- Enable model access in Bedrock Console → Model access
- Wait a few minutes after enabling

**Slow responses:**
- First request may be slow (cold start)
- Consider using Claude Haiku for faster responses

## Local vs Deployed

| Feature | Local | Deployed (AgentCore) |
|---------|-------|---------------------|
| Runs on | Your machine | AWS infrastructure |
| Scaling | Manual | Auto-scaling |
| Auth | Your AWS creds | Managed IAM |
| Observability | Local logs | CloudWatch |
| Best for | Development | Production |

For production deployment, see [deployed/README.md](../deployed/README.md).
