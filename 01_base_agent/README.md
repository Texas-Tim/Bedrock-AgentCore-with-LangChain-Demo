# Lab 1: Deploy a LangGraph Agent to AWS Bedrock AgentCore

## Table of Contents

- [Prerequisites](#prerequisites)
- [Part 1: Review the Agent Code](#part-1-review-the-agent-code-skip-to-part-3-for-deployment)
- [Part 2: Deploy to AgentCore](#part-2-deploy-to-agentcore)
- [Part 3: Test the Agent](#part-3-test-the-deployed-agent)
- [Cleanup](#cleanup)
- [Troubleshooting](#troubleshooting)
- [Resources](#additional-resources)

---

By the end of this lab, you will:
1. Understand the AgentCore deployment workflow
2. Deploy a LangGraph agent to AgentCore Runtime
3. Test the deployed agent via CLI and SDK

## Prerequisites

- **AWS Account** with Bedrock AgentCore access
- **AWS CLI** configured with credentials (`aws configure`)
- **Python 3.10+**
- **AgentCore Starter Toolkit** 

Navigate to local directory
```bash
cd 01_base_agent
pip install -r requirements.txt
```

Verify AWS credentials
```bash
aws sts get-caller-identity
```

Verify Bedrock model access
```bash
aws bedrock list-foundation-models --region us-east-1 \
  --query "modelSummaries[?contains(modelID, 'claude')].[modelId]" \
  --output table
```
Note: If you don't see your expected model, this lab uses: `anthropic.claude-sonnet-4-5`, then ensure you have the proper permissions set up in IAM

---

## Part 1: Review the Agent Code (skip to Part 3 for deployment)

Open `agent.py` and review the structure. The agent is built using four key components:

### Key Component 1: BedrockAgentCoreApp

`BedrockAgentCoreApp` is the deployment wrapper that enables your agent to run on AWS Bedrock AgentCore. It provides:

- **HTTP endpoint handling** - Routes incoming requests to your agent
- **Streaming support** - Enables token-by-token response streaming
- **Lifecycle management** - Handles startup, shutdown, and health checks
- **Container integration** - Works seamlessly with the AgentCore Docker runtime

[AgentCore Runtime Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-runtime.html)

---

### Key Component 2: ChatBedrock

`ChatBedrock` is LangChain's integration with Amazon Bedrock foundation models. It provides:

- **Model abstraction** - Unified interface for Claude, Titan, and other Bedrock models
- **Streaming** - Native support for token streaming
- **Tool calling** - Automatic handling of function/tool calls
- **Cross-region inference** - The `us.` prefix enables routing to available capacity

Configuration options include:
- `temperature` - Controls response randomness (0-1)
- `max_tokens` - Maximum response length
- `guardrails` - Attach Bedrock Guardrails (covered in Lab 2)

[ChatBedrock Documentation](https://python.langchain.com/docs/integrations/chat/bedrock/) | [Bedrock Models](https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html)

---

### Key Component 3: create_react_agent

```python
from langgraph.prebuilt import create_react_agent

agent = create_react_agent(
  model=llm,
  tools=[get_weather, calculate],
  prompt=SYSTEM_PROMPT,
)
```

The agent loop:
```
User Query -> Thought -> Action (tool call) -> Observation -> Thought -> ... -> Final Answer
```

Key parameters:
- `model` - The LLM that powers reasoning
- `tools` - List of callable tools (functions decorated with `@tool`)
- `prompt` - System instructions that guide behavior
- `checkpointer` - Optional memory persistence (covered in Lab 2)

[LangGraph ReAct Agent](https://langchain-ai.github.io/langgraph/concepts/agentic_concepts/#react-agent) | [create_react_agent API](https://langchain-ai.github.io/langgraph/reference/prebuilt/#langgraph.prebuilt.chat_agent_executor.create_react_agent)

---

### Key Component 4: @app.entrypoint

```python
@app.entrypoint
async def handle_request(payload: dict, **kwargs) -> AsyncGenerator[str, None]:
    prompt = payload.get("prompt", "")
    # ... process and stream response
    async for event in agent.astream(input_data, stream_mode="messages"):
      yield text # Stream tokens back to caller
```

The `@app.entrypoint` decorator marks the main request handler for AgentCore. This function:

- **Receives requests** - AgentCore routes all invocations here
- **Must be async** - Required for streaming support
- **Yields responses** - Uses python generators for token streaming
- **Handles errors** - Catches exceptions and returns error messages

The handler extracts the prompt, invokes the LangGraph agent, and streams response tokens back to teh caller. The `stream_mode="messages"` parameter enables chunk-by-chunk streaming.

### Tools

The agent has two simple tools demonstrating the `@tool` decorator pattern:

```python
@tool
def get_weather(location: str) -> str:
    """Get the current weather for a location."""
    return f"The weather in {location} is 72°F and sunny."

@tool 
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression. Example: calculate('2+2')"""
    # ... safe math evaluation
```

Tools extend the agent's capabilities beyond text generation. Each tool requires: 
- **Type hints** - Parameters must have type annotations
- **Docstring** - The agent reads this to understand when/how to use the tool
- **Return value** - Results are passed back to the agent for reasoning

[LangChain Tools](https://python.langchain.com/docs/concepts/tools/) | [Custom Tools Guide](https://python.langchain.com/docs/how_to/custom_tools/)



## Part 2: Deploy to AgentCore

The AgentCore deployment process packages your agent as a Docker container and deploys it to AWS-managed infrastructure. The CLI handles the complexity of ECR, CodeBuild, and runtime configuration.

### Step 2.1: Configure Deployment

```bash
agentcore configure \
 -e agent.py \
 -n langgraph_demo \
 -r us-east-1 \
 --non-interactive
```

**What this command does:**
| Flag | Purpose |
|------|---------|
| `-e agent.py` | Specifies the entrypoint file containing your `BedrockAgentCoreApp` |
| `-n langgraph_lab_agent` | Sets the agent name (used in ARN and Cloudwatch logs) |
| `-r us-east-1` | AWS region for deployment |
| `--non-interactive` | Skips prompts, uses defaults |

**Generated files:**


This creates `.bedrock_agentcore.yaml` - your deployment configuration

```yaml
# Example structure
agent_name: langgraph_lab_agent
region: us-east-1
entrypoint: agent.py
runtime:
  memory: 512        # MB of memory allocated
  timeout: 300       # Request timeout in seconds
```

You can edit this file to customize:
- **Memory allocations** - Increase for larger models or complex tools
- **Timeout settings** - Extend for long-running operations
- **Environment variables** - Add secrets or configuration (used in Lab 2)

[AgentCore Configuration Reference](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-deploy.html)

---

### Step 2.2: Deploy to AWS
**Note:** The AgentCore CLI offers two deployment commands:
- `agentcore launch` - Container-based deployment using Docker and CodeBuild. We are using containers for this deployment
- `agentcore deploy` - ZIP-based deployment that packages dependencies without Docker

```bash
agentcore launch
```

**Deployment timeline:** First deployment takes 5-10 minutes. Subsequent deployments are faster due to Docker layer caching

**Monitor progress:**
- The CLI shows real-time status updates
- For detailed logs, check AWS CodeBuild in the console
- Build failures are logged with error details

---

### Step 2.3: Save the Agent ARN

After successful deployment, the CLI outputs your Agent ARN:

```
Agent deployed successfully!
Agent ARN: arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/abc123def456
```

**Save this ARN** - you'll need it for testing and SDK invocations:

```bash
export AGENT_ARN=$(grep "agent_arn:" .bedrock_agentcore.yaml | awk '{print $2}')
export AGENT_ID=$(grep "agent_id:" .bedrock_agentcore.yaml | head -1 | awk '{print $2}')

echo "ARN: $AGENT_ARN"
echo "ID: $AGENT_ID"
```

**Understanding the ARN structure:**
```
arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/abc123def456
    |         |              |          |           |         |
    |         |              |          |           |         |__ Agent ID
    |         |              |          |           |__ Resource type
    |         |              |          |__ AWS Account ID
    |         |              |__ Region
    |         |__ Service name
    |__ ARN prefix
```

### Step 2.4: Verify Deployment Status

Check that your agent is running:

```bash
# Using the CLI
agentcore status
```

**Expected status:** `ACTIVE` or `READY` indicates the agent is ready to receive requests.

**If status is not READY:**
- `CREATING` - Deployment in progress, wait a few minutes
- `FAILED` - Check CloudWatch logs for errors
- `UPDATING` - Previous deployment still processing

[AgentCore Monitoring](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-observability.html)

---

## Part 3: Test the Deployed Agent

### Step 3.1: Test via CLI

```bash
# Test weather tool
agentcore invoke '{"prompt": "What is the weather in Seattle?"}'

# Test calculator tool
agentcore invoke '{"prompt": "What is 15*7?"}'

# Test general conversation
agentcore invoke '{"prompt": "Hello, what can you help me with?"}'
```


### Step 3.2: Test via Python SDK

```bash
python invoke_agent.py "What is the weather in Seattle?"
```

## Files

| File | Description |
|------|-------------|
| `agent.py` | Basic LangGraph agent for AgentCore |
| `invoke_agent.py` | Python client to test the agent |
| `verify_setup.py` | Verify deployment status |
| `requirements.txt` | Python dependencies |
| `Dockerfile` | Container configuration |
| `.bedrock_agentcore.yaml` | Deployment configuration |

---

## Customizing the Agent

Edit `agent.py` to add your own tools:

```python
@tool
def my_custom_tool(param: str) -> str:
    """Description of what this tool does."""
    # Your implementation
    return result

tools = [get_weather, my_custom_tool]
```

Then redeploy:

```bash
agentcore launch
```

## Cleanup

Remove all AWS resources created by this deployment:

```bash
agentcore destroy --force

# Delete Cloudwatch log groups
aws logs describe-log-groups --log-group-name-prefix /aws/bedrock-agentcore/runtimes/ --query 'logGroups[].logGroupName' --output text
```

This deletes the AgentCore Runtime agent, ECR repository, and CodeBuild project.

## Troubleshooting

**"Access denied" errors:**
- Ensure your AWS credentials have permissions for Bedrock, ECR, CodeBuild, and IAM
- Check that Bedrock model access is enabled for your chosen model

**"Model not found" errors:**
- Verify the `MODEL_ID` in `agent.py` matches an enabled model in your region
- Some models are region-specific

**Deployment fails:**
- Check CodeBuild logs in AWS Console for build errors
- Verify the agent ARN is correct

**Agent not responding**
- Check CloudWatch logs for errors

```bash
aws logs tail /aws/bedrock-agentcore/runtimes/YOUR_AGENT_ID-DEFAULT \
  --log-stream-name-prefix "$(date +%Y/%m/%d)/[runtime-logs" \
  --since 10m --region us-east-1
```

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

## Additional Resources

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Bedrock AgentCore Starter Toolkit](https://github.com/awslabs/bedrock-agentcore-starter-toolkit)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Docker Documentation](https://docs.docker.com/)
- [AWS ECR Documentation](https://docs.aws.amazon.com/ecr/)
- [AWS CodeBuild Documentation](https://docs.aws.amazon.com/codebuild/)
