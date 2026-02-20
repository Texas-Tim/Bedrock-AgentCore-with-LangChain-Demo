# LangGraph + AWS Bedrock AgentCore Demo

Build and deploy AI agents using LangGraph with AWS Bedrock. This repo demonstrates multiple deployment approaches with varying feature sets.

## Project Structure

```
.
├── local_deploy_agent/          # Run locally on your machine
│   ├── agent.py                 # Basic streaming agent (CLI)
│   ├── agent_with_memory.py     # With AgentCore Memory persistence
│   ├── agent_with_all_features.py  # With GuardRails, KB, Memory
│   ├── fastapi_server.py        # HTTP API with SSE streaming
│   └── requirements.txt
│
├── aws_base_agent/              # Deploy basic agent to AWS
│   ├── agent.py                 # Basic agent for AgentCore Runtime
│   ├── invoke_deployed_agent.py # SDK client to test deployed agent
│   ├── Dockerfile
│   └── requirements.txt
│
├── aws_kb_gr_agent/             # Deploy agent with all features to AWS
│   ├── kb_gr_agent.py              # GuardRails, KB, Memory
│   ├── test_kb_gr_memory.py        # Test harness for features
│   └── requirements.txt
│
├── shared/                      # Shared utilities module
│   ├── config.py                # Pydantic configuration management
│   ├── knowledge_base.py        # Knowledge Base tool factory
│   ├── guardrails.py            # GuardRails configuration
│   ├── memory.py                # Memory initialization
│   └── retry.py                 # Retry logic with backoff
│
├── tests/                       # Unit tests
│   ├── test_config.py           # Configuration tests
│   ├── test_knowledge_base.py   # Knowledge Base tests
│   ├── test_guardrails.py       # GuardRails tests
│   ├── test_memory.py           # Memory tests
│   └── test_retry.py            # Retry logic tests
│
├── example_knowledge_base/      # Sample documents for Knowledge Base
│   ├── company_overview.txt
│   ├── contact_support.txt
│   ├── policies_faq.txt
│   └── products_services.txt
│
├── Images/                      # Documentation screenshots
├── AWS_PERMISSIONS.md           # IAM permissions reference
├── BEDROCK_AGENTS_WALKTHROUGH.md  # Comprehensive feature guide
├── pyproject.toml               # Project configuration
├── requirements.txt             # Root dependencies
└── README.md
```

## Features

### AWS Bedrock Agents Integration
- **GuardRails**: Content filtering and safety controls
- **Knowledge Bases**: RAG (Retrieval Augmented Generation) for document retrieval
- **Memory**: Persistent conversation state across sessions

See the [Bedrock Agents Walkthrough](BEDROCK_AGENTS_WALKTHROUGH.md) for detailed setup instructions.

## Prerequisites

- Python 3.10+
- AWS account with Bedrock access
- AWS CLI configured (`aws configure`)
- Bedrock model access enabled (Claude Sonnet 4.5)

## Quick Start

### Option 1: Run Locally

```bash
cd local_deploy_agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python agent.py
```

### Option 2: Deploy Basic Agent to AWS

```bash
cd aws_base_agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install bedrock-agentcore-starter-toolkit

# Configure and deploy
agentcore configure -e agent.py -n langgraph_demo -r us-east-1 --non-interactive
agentcore launch
```

### Option 3: Deploy Full-Featured Agent to AWS

```bash
cd aws_kb_gr_agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install bedrock-agentcore-starter-toolkit

# Set up GuardRails, Knowledge Base, Memory in AWS Console first
# Then configure environment variables in .bedrock_agentcore.yaml
agentcore configure -e kb_gr_agent.py -n langgraph_full_demo -r us-east-1 --non-interactive
agentcore launch
```

## Key Implementation Pattern

All agents use `stream_mode="messages"` for reliable streaming:

```python
async for event in agent.astream(input_data, stream_mode="messages"):
    if isinstance(event, tuple) and len(event) >= 2:
        chunk, metadata = event[0], event[1]
        if metadata.get("langgraph_node") == "model":
            # Process AI response chunks
```

This avoids the `tool_call_chunks` validation bug in `langchain-aws` that occurs with `astream_events()`.

The agents use `create_react_agent` from `langgraph.prebuilt` for the ReAct pattern implementation.

## Development

### Running Tests

```bash
# Install development dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=shared --cov-report=html

# Run specific test file
pytest tests/test_config.py
```

### Code Quality

```bash
# Type checking
mypy shared/

# Linting
ruff check .

# Format code
ruff format .
```

## Documentation

- [Local Agent Setup](local_deploy_agent/README.md) — CLI agent, memory persistence, FastAPI server
- [Basic AWS Deployment](aws_base_agent/README.md) — Deploy simple agent to AgentCore Runtime
- [Full-Featured AWS Deployment](aws_kb_gr_agent/README.md) — Deploy with GuardRails, Knowledge Base, Memory
- [Bedrock Agents Walkthrough](BEDROCK_AGENTS_WALKTHROUGH.md) — GuardRails, Knowledge Bases, Memory setup
- [AWS Permissions Guide](AWS_PERMISSIONS.md) — IAM permissions reference

## Additional Resources

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain AWS Integration](https://python.langchain.com/docs/integrations/platforms/aws)
- [Bedrock AgentCore Starter Toolkit](https://github.com/awslabs/bedrock-agentcore-starter-toolkit)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
