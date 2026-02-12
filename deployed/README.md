# Deploy LangGraph Agent to AWS Bedrock AgentCore Runtime

Deploy a LangGraph agent to AWS-managed infrastructure with auto-scaling, observability, and managed identity.

## Prerequisites

1. **AWS Account** with Bedrock AgentCore access
2. **AWS CLI** configured with credentials (`aws configure`)
3. **Bedrock Model Access** enabled for Claude Sonnet 4
4. **Python 3.10+**

## Step 1: Set Up Environment

```bash
cd agentcore_demo/deployed

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install AgentCore CLI toolkit
pip install bedrock-agentcore-starter-toolkit
```

## Step 2: Configure the Agent

Run the configuration wizard:

```bash
agentcore configure -e agent.py -n langgraph_demo -r us-east-1 --non-interactive
```

This creates `.bedrock_agentcore.yaml` with your AWS account details.

**Or manually:** Copy the example template and fill in your AWS account ID:

```bash
cp .bedrock_agentcore.yaml.example .bedrock_agentcore.yaml
# Edit .bedrock_agentcore.yaml and replace YOUR_ACCOUNT_ID with your AWS account ID
```

### Configure Bedrock Agents Features (Optional)

To enable GuardRails, Knowledge Base, or Memory, add environment variables to `.bedrock_agentcore.yaml`:

```yaml
agents:
  langgraph_demo:
    entrypoint: agent.py
    environment:
      BEDROCK_GUARDRAIL_ID: "your-guardrail-id"
      BEDROCK_GUARDRAIL_VERSION: "1"
      BEDROCK_KNOWLEDGE_BASE_ID: "your-kb-id"
      BEDROCK_MEMORY_ID: "your-memory-id"
    # ... rest of configuration
```

See the [Bedrock Agents Walkthrough](../docs/BEDROCK_AGENTS_WALKTHROUGH.md) for setup instructions.

## Step 3: Deploy to AWS

```bash
agentcore launch
```

This will:
1. Create an ECR repository for your agent container
2. Build and push the Docker image via CodeBuild
3. Deploy to AgentCore Runtime
4. Output your Agent ARN

Save the Agent ARN from the output — you'll need it to invoke the agent.

## Step 4: Test the Deployed Agent

### Using AgentCore CLI

```bash
agentcore invoke '{"prompt": "What is the weather in Seattle?"}'
```

### Using Python SDK

```bash
# Set your Agent ARN (from agentcore launch output)
export AGENT_ARN="arn:aws:bedrock-agentcore:us-east-1:YOUR_ACCOUNT_ID:runtime/YOUR_AGENT_ID"

# Run the test script
python invoke_deployed_agent.py "What is the weather in Seattle?"
```

## Files

| File | Description |
|------|-------------|
| `agent.py` | LangGraph agent with `BedrockAgentCoreApp` wrapper |
| `agent_with_all_features.py` | Agent with GuardRails, Knowledge Base, and Memory |
| `invoke_deployed_agent.py` | Python SDK client to invoke deployed agent |
| `requirements.txt` | Python dependencies |
| `Dockerfile` | Container configuration for deployment |
| `.bedrock_agentcore.yaml.example` | Template for deployment configuration |

## Bedrock Agents Features

The `agent_with_all_features.py` file demonstrates three powerful AWS Bedrock Agents features:

### 1. GuardRails - Content Safety

Content filtering and safety controls for production agents:
- Block harmful content and PII
- Enforce denied topics
- Apply custom word filters

### 2. Knowledge Bases - RAG

Retrieval augmented generation for grounded responses:
- Index your documents
- Semantic search
- Cite sources

### 3. Memory - Conversation Persistence

Persistent conversation state across sessions:
- Remember previous interactions
- Multi-user support
- Automatic state management

**Learn More:** See the [Bedrock Agents Walkthrough](../docs/BEDROCK_AGENTS_WALKTHROUGH.md) for detailed setup instructions.

To deploy with these features:
1. Set up resources in AWS Console (GuardRails, Knowledge Base, Memory)
2. Add environment variables to `.bedrock_agentcore.yaml`
3. Deploy: `agentcore launch`

## Configuration Reference

The `.bedrock_agentcore.yaml` file controls deployment settings:

```yaml
agents:
  langgraph_demo:
    entrypoint: agent.py           # Your agent script
    platform: linux/arm64          # Container platform
    aws:
      region: us-east-1            # AWS region
      execution_role_auto_create: true  # Auto-create IAM role
      ecr_auto_create: true        # Auto-create ECR repo
      network_configuration:
        network_mode: PUBLIC       # Network access mode
      observability:
        enabled: true              # CloudWatch logging
```

## Customizing the Agent

Edit `agent.py` to add your own tools:

```python
@tool
def my_custom_tool(param: str) -> str:
    """Description of what this tool does."""
    # Your implementation
    return result

tools = [get_weather, search_knowledge_base, my_custom_tool]
```

Then redeploy:

```bash
agentcore launch
```

## Cleanup

Remove all AWS resources created by this deployment:

```bash
agentcore destroy
```

This deletes the AgentCore Runtime agent, ECR repository, and CodeBuild project.

## Troubleshooting

**"Access denied" errors:**
- Ensure your AWS credentials have permissions for Bedrock, ECR, CodeBuild, and IAM
- Check that Bedrock model access is enabled for Claude Sonnet 4

**"Model not found" errors:**
- Verify the `MODEL_ID` in `agent.py` matches an enabled model in your region
- Some models are region-specific

**Deployment fails:**
- Check CodeBuild logs in AWS Console for build errors
- Ensure `requirements.txt` has all dependencies

## Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────┐
│  Your Client    │────▶│  AgentCore Runtime   │────▶│   Bedrock   │
│  (SDK/CLI)      │◀────│  (Your Agent)        │◀────│   Claude    │
└─────────────────┘     └──────────────────────┘     └─────────────┘
```

AgentCore Runtime handles:
- Auto-scaling based on load
- Request routing and load balancing
- CloudWatch metrics and logging
- Managed IAM identity for Bedrock access
