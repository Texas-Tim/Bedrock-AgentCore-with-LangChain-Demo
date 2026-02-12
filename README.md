# LangGraph + AWS Bedrock AgentCore Demo

Build and deploy AI agents using LangGraph with AWS Bedrock. This repo includes two approaches:

1. **Local** — Run agents on your machine, use Bedrock for LLM inference
2. **Deployed** — Deploy to AWS Bedrock AgentCore Runtime with auto-scaling and observability

## Features

### Core Capabilities
- **Streaming Responses**: Token-by-token streaming using LangGraph
- **Tool Integration**: Custom tools with automatic function calling
- **Local & Deployed**: Same code works locally and in production

### AWS Bedrock Agents Integration
- **GuardRails**: Content filtering and safety controls
- **Knowledge Bases**: RAG (Retrieval Augmented Generation) for document retrieval
- **Memory**: Persistent conversation state across sessions

See the [Bedrock Agents Walkthrough](docs/BEDROCK_AGENTS_WALKTHROUGH.md) for detailed setup instructions.

## Prerequisites

- Python 3.10+
- AWS account with Bedrock access
- AWS CLI configured (`aws configure`)
- Bedrock model access enabled (Claude Sonnet 4)

## Quick Start

### Option 1: Run Locally

```bash
cd agentcore_demo/local
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python agent.py
```

### Option 2: Deploy to AWS

```bash
cd agentcore_demo/deployed
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install bedrock-agentcore-starter-toolkit

# Configure and deploy
agentcore configure -e agent.py -n langgraph_demo -r us-east-1 --non-interactive
agentcore launch
```

## Project Structure

```
agentcore_demo/
├── local/                              # Run locally
│   ├── agent.py                        # Basic streaming agent (CLI)
│   ├── agent_with_memory.py            # With AgentCore Memory persistence
│   ├── agent_with_all_features.py      # With GuardRails, Knowledge Base, Memory
│   ├── fastapi_server.py               # HTTP API with SSE streaming
│   └── requirements.txt
│
├── deployed/                           # Deploy to AgentCore Runtime
│   ├── agent.py                        # Agent with AgentCore HTTP contract
│   ├── agent_with_all_features.py      # With GuardRails, Knowledge Base, Memory
│   ├── invoke_deployed_agent.py        # SDK client to test deployed agent
│   ├── .bedrock_agentcore.yaml.example # Deployment config template
│   ├── Dockerfile
│   └── requirements.txt
│
├── docs/                               # Documentation
│   ├── BEDROCK_AGENTS_WALKTHROUGH.md   # Comprehensive feature guide
│   └── AWS_PERMISSIONS.md              # IAM permissions reference
│
├── .gitignore
└── README.md
```

## Key Implementation Pattern

Both local and deployed agents use `stream_mode="messages"` for reliable streaming:

```python
async for event in agent.astream(input_data, stream_mode="messages"):
    if isinstance(event, tuple) and len(event) >= 2:
        chunk, metadata = event[0], event[1]
        if metadata.get("langgraph_node") == "model":
            # Process AI response chunks
```

This avoids the `tool_call_chunks` validation bug in `langchain-aws` that occurs with `astream_events()`.

## Documentation

- [Local Agent Setup](local/README.md) — CLI agent, memory persistence, FastAPI server
- [Deployed Agent Setup](deployed/README.md) — AgentCore deployment, invocation, cleanup
- [Bedrock Agents Walkthrough](docs/BEDROCK_AGENTS_WALKTHROUGH.md) — GuardRails, Knowledge Bases, Memory setup
- [AWS Permissions Guide](docs/AWS_PERMISSIONS.md) — IAM permissions reference

## License

MIT
