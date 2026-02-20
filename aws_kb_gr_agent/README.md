# Deploy Full-Featured LangGraph Agent to AWS Bedrock AgentCore Runtime

Deploy a LangGraph agent with GuardRails, Knowledge Base, and Memory to AWS-managed infrastructure.

## What's Included

This agent includes all three AWS Bedrock Agents features:
- **GuardRails**: Content filtering and safety controls
- **Knowledge Base**: RAG (Retrieval Augmented Generation) for document retrieval
- **Memory**: Persistent conversation state across sessions

For a simpler deployment without these features, see [../aws_base_agent/](../aws_base_agent/).

## Prerequisites

1. **AWS Account** with Bedrock AgentCore access
2. **AWS CLI** configured with credentials (`aws configure`)
3. **Bedrock Model Access** enabled for Claude Sonnet 4.5
4. **Python 3.10+**
5. **AWS Resources Created**:
   - GuardRail (optional)
   - Knowledge Base (optional)
   - Memory (optional)

See the [Bedrock Agents Walkthrough](../BEDROCK_AGENTS_WALKTHROUGH.md) for detailed setup instructions.

## Step 1: Set Up AWS Resources

Before deploying, create the AWS resources you want to use:

### 1. GuardRails (Optional)
1. Go to [Bedrock Console > GuardRails](https://console.aws.amazon.com/bedrock)
2. Create a GuardRail with content filters, PII detection, denied topics
3. Copy the GuardRail ID (format: `gr-abc123xyz`)

### 2. Knowledge Base (Optional)
1. Upload documents to S3 bucket (or use `../example_knowledge_base/`)
2. Go to [Bedrock Console > Knowledge Bases](https://console.aws.amazon.com/bedrock)
3. Create a Knowledge Base pointing to your S3 bucket
4. Sync the data source
5. Copy the Knowledge Base ID (format: `KB123ABC`)

### 3. Memory (Optional)
Memory can be created automatically during deployment or manually:

**Option A: Auto-create during deploy (recommended)**
- Run `agentcore configure` without `--disable-memory`
- Memory is created automatically during `agentcore deploy`

**Option B: Create manually**
1. Go to [Bedrock Console > AgentCore > Memory](https://console.aws.amazon.com/bedrock)
2. Create a Memory resource
3. Copy the Memory ID (format: `mem-abc123xyz`)
4. Pass via `--env BEDROCK_MEMORY_ID=mem-abc123xyz` during deploy

## Step 2: Set Up Environment

```bash
cd aws_kb_gr_agent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install AgentCore CLI toolkit
pip install bedrock-agentcore-starter-toolkit
```

## Step 3: Configure the Agent

Run the configuration wizard:

```bash
agentcore configure -e kb_gr_agent.py -n langgraph_full_demo -r us-east-1 --non-interactive
```

This creates `.bedrock_agentcore.yaml` with your AWS account details.

### What is `.bedrock_agentcore.yaml`?

This file is the deployment configuration for your agent. It tells AWS:
- **Entry point**: Which Python file contains your agent (`kb_gr_agent.py`)
- **AWS settings**: Region, IAM roles, ECR repository
- **Container config**: Platform (ARM64/x86), Docker settings
- **Network**: Public or VPC access
- **Memory**: AgentCore Memory configuration (auto-created during deploy)
- **Observability**: CloudWatch logging

Think of it as your deployment blueprint - similar to `docker-compose.yml` or a Kubernetes manifest.

## Step 4: Deploy to AWS

Deploy with environment variables for your AWS resources:

```bash
# Deploy with all features (GuardRails, Knowledge Base, Memory)
agentcore deploy \
  --env BEDROCK_GUARDRAIL_ID=your-guardrail-id \
  --env BEDROCK_GUARDRAIL_VERSION=1 \
  --env BEDROCK_KNOWLEDGE_BASE_ID=your-kb-id \
  --env BEDROCK_MEMORY_ID=your-memory-id

# Or deploy with only some features (all are optional)
agentcore deploy --env BEDROCK_KNOWLEDGE_BASE_ID=your-kb-id
```

**Note**: All features are optional. Only include `--env` flags for features you want to enable.

Alternatively, use `agentcore launch` which combines configure + deploy:

```bash
agentcore launch
```

This will:
1. Create an ECR repository for your agent container
2. Build and push the Docker image via CodeBuild
3. Deploy to AgentCore Runtime with your configured features
4. Output your Agent ARN

Save the Agent ARN from the output — you'll need it to invoke the agent.

### Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `BEDROCK_GUARDRAIL_ID` | GuardRail resource ID | `gr-abc123xyz` |
| `BEDROCK_GUARDRAIL_VERSION` | GuardRail version | `1` or `DRAFT` |
| `BEDROCK_KNOWLEDGE_BASE_ID` | Knowledge Base resource ID | `ABCDEFGHIJ` |
| `BEDROCK_MEMORY_ID` | Memory resource ID | `mem-xyz789` |

## Step 5: Test the Deployed Agent

### Using AgentCore CLI

```bash
agentcore invoke '{"prompt": "What is AcmeCorp?"}'
```

### Using Python SDK

```bash
# Set your Agent ARN (from agentcore launch output)
export AGENT_ARN="arn:aws:bedrock-agentcore:us-east-1:YOUR_ACCOUNT_ID:runtime/YOUR_AGENT_ID"

# Run the test script (copy from aws_base_agent/)
python invoke_deployed_agent.py "What is AcmeCorp?"
```

## Testing Each Feature

### Test GuardRails
```bash
# Try to trigger content filter
agentcore invoke '{"prompt": "[content that should be blocked]"}'

# Try to share PII
agentcore invoke '{"prompt": "My email is test@example.com and SSN is 123-45-6789"}'
```

### Test Knowledge Base
```bash
# Query your documents
agentcore invoke '{"prompt": "What are AcmeCorp products?"}'
agentcore invoke '{"prompt": "How do I contact support?"}'
```

### Test Memory
```bash
# First conversation
agentcore invoke '{"prompt": "My name is Alice"}'

# Later conversation (same thread_id)
agentcore invoke '{"prompt": "What is my name?"}'
```

## Files

| File | Description |
|------|-------------|
| `kb_gr_agent.py` | Agent with GuardRails, Knowledge Base, and Memory |
| `invoke_deployed_agent.py` | SDK client to test deployed agent with memory support |
| `test_kb_gr_memory.py` | Test harness for KB, GuardRails, and Memory |
| `.bedrock_agentcore.yaml` | AgentCore deployment configuration |
| `.env.example` | Example environment variables for local development |
| `Dockerfile` | Container configuration for deployment |
| `requirements.txt` | Python dependencies |

## Customizing the Agent

Edit `kb_gr_agent.py` to add your own tools:

```python
@tool
def my_custom_tool(param: str) -> str:
    """Description of what this tool does."""
    # Your implementation
    return result

tools = [get_weather, query_knowledge_base, my_custom_tool]
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

**Note**: This does NOT delete your GuardRail, Knowledge Base, or Memory resources. Delete those manually in the AWS Console if needed.

## Troubleshooting

**"Access denied" errors:**
- Ensure your AWS credentials have permissions for Bedrock, ECR, CodeBuild, and IAM
- Check [AWS Permissions Guide](../AWS_PERMISSIONS.md) for required permissions
- Verify GuardRail, Knowledge Base, and Memory permissions

**"Resource not found" errors:**
- Verify resource IDs passed via `--env` flags are correct
- Check resources exist in the same region as your deployment
- Ensure resources are in "Active" state

**GuardRails not working:**
- Verify `BEDROCK_GUARDRAIL_ID` and `BEDROCK_GUARDRAIL_VERSION` are set
- Check GuardRail is active in AWS Console
- Review CloudWatch logs for GuardRail trace information

**Knowledge Base not returning results:**
- Verify data source is synced
- Check `BEDROCK_KNOWLEDGE_BASE_ID` is correct
- Test queries directly in AWS Console

**Memory not persisting:**
- Verify `BEDROCK_MEMORY_ID` is set
- Ensure same `thread_id` and `actor_id` are used across invocations
- Check Memory resource is active

**Deployment fails:**
- Check CodeBuild logs in AWS Console for build errors
- Ensure `requirements.txt` has all dependencies
- Verify IAM execution role has necessary permissions

## Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────┐
│  Your Client    │────▶│  AgentCore Runtime   │────▶│   Bedrock   │
│  (SDK/CLI)      │     │  (Your Agent)        │     │   Claude    │
└─────────────────┘     └──────────────────────┘     └─────────────┘
                                 │                           │
                                 ├──────────────────────────▶│
                                 │      GuardRails           │
                                 │                           │
                                 ├──────────────────────────▶│
                                 │   Knowledge Base (RAG)    │
                                 │                           │
                                 └──────────────────────────▶│
                                        Memory               │
```

## Additional Resources

- [Bedrock Agents Walkthrough](../BEDROCK_AGENTS_WALKTHROUGH.md) — Detailed feature setup guide
- [AWS Permissions Guide](../AWS_PERMISSIONS.md) — IAM permissions reference
- [Example Knowledge Base](../example_knowledge_base/) — Sample documents
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Bedrock AgentCore Starter Toolkit](https://github.com/awslabs/bedrock-agentcore-starter-toolkit)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
