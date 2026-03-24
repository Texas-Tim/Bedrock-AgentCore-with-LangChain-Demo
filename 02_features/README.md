# Lab 2: Add GuardRails, Knowledge Base & Memory

## Table of Contents

- [Prerequisites](#prerequisites)
- [Part 1: Create a GuardRail](#part-1-create-a-guardrail)
- [Part 2: Create a Knowledge Base](#part-2-create-a-knowledge-base)
- [Part 3: Deploy Agent with Features](#part-3-deploy-agent-with-features)
- [Part 4: Test the Features](#part-4-test-the-features)
- [Cleanup](#cleanup)
- [Troubleshooting](#troubleshooting)
- [Resources](#additional-resources)

--- 

In this lab, you'll create AWS Bedrock resources and enhance your agent with
- **GuardRails**: Content filtering and safety controls
- **Knowledge Base**: RAG (Retrieval Augmented Generation) for document retrieval
- **Memory**: Persistent conversation state

## Prerequisites

1. **AWS Account** with Bedrock AgentCore access
2. **AWS CLI** configured with credentials (`aws configure`)
3. **Python 3.10+**

Navigate to this lab directory:

```bash
cd 02_features
pip install -r requirements.txt
```

---

## Part 1: Create a GuardRail

GuardRails provide content safety controls - blocking harmful content, filtering PII, and enforcing topic restrictions. The GuardRail can be created by the console very easily, just use the following CLI guide for the parameters.

### Step 1.1: Create GuardRail (CLI)

```bash
aws bedrock create-guardrail \
  --name lab-guardrail \
  --description "GuardRail for LangGraph Lab" \
  --blocked-input-messaging "I cannot process this request due to content policies." \
  --blocked-outputs-messaging "I cannot provide this response due to content policies." \
  --content-policy-config '{
    "filtersConfig": [
      {"type": "HATE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
      {"type": "INSULTS", "inputStrength": "HIGH", "outputStrength": "HIGH"},
      {"type": "SEXUAL", "inputStrength": "HIGH", "outputStrength": "HIGH"},
      {"type": "VIOLENCE", "inputStrength": "HIGH", "outputStrength": "HIGH"}
    ]
  }' \
  --sensitive-information-policy-config '{
    "piiEntitiesConfig": [
      {"type": "EMAIL", "action": "ANONYMIZE"},
      {"type": "PHONE", "action": "ANONYMIZE"},
      {"type": "US_SOCIAL_SECURITY_NUMBER", "action": "BLOCK"}
    ]
  }'

# Save the GuardRail ID
export GUARDRAIL_ID=$(aws bedrock list-guardrails --query "guardrails[?name=='lab-guardrail'].id" --output text)
echo "GuardRail ID: $GUARDRAIL_ID"
```

### Step 1.2: Create a GuardRail Version

```bash
aws bedrock create-guardrail-version \
  --guardrail-identifier $GUARDRAIL_ID \
  --description "Version 1"

# Export version for deployment
export GUARDRAIL_VERSION="1"
echo "GuardRail ID: $GUARDRAIL_VERSION"
```

---

## Part 2: Create a Knowledge Base

Knowledge Bases enable RAG (Retrieval Augmented Generation) - your agent can search and retrieve information from your documents

### Step 2.1: Upload Documents to S3

```bash
# Create S3 bucket
aws s3 mb s3://langgraph-lab-kb-$(aws sts get-caller-identity --query Account --output text)

# Upload example documents
aws s3 sync ../example_knowledge_base/ s3://langgraph-lab-kb-$(aws sts get-caller-identity --query Account --output text)
```

### Step 2.2: Create Knowledge Base via Console

> **Why Console?** Creating a Knowledge Base via CLI requires multiple steps: creating an IAM role, setting up OpenSearch Serverless security policies, creating the collection, and configuring the data source. The console handles all of this automatically with "Quick Create."

> **Important** Ensure you're in the same AWS region as your agent and guardrail when working in the console. Check the region selector in the top-right corner.
1. Go to [Bedrock Console > Knowledge bases](https://console.aws.amazon.com/bedrock/home#/knowledge-bases)
2. Click **Create knowledge base with vector store**
3. Configure:
  - **Name**: `lab-knowledge-base`
  - **IAM role**: Create new role
  - **Data source**: S3
4. Click **Next**
5. Configure:
  - **S3 URI**: Your bucket from step 2.1
6. Click **Next**
7. Configure:
  - **Embedding model**: Titan Embeddings G1 - Text
  - **Vector database**: Quick create (OpenSearch Serverless)
8. Click **Create**
9. **Sync the data source** after creation
10. **Save the Knowledge Base ID** (format: `XXXXXXXXXX`)

```bash
export KNOWLEDGE_BASE_ID=$(aws bedrock-agent list-knowledge-bases --query "knowledgeBaseSummaries[?name=='lab-knowledge-base'].knowledgeBaseId" --output text)
echo "Knowledge Base ID: $KNOWLEDGE_BASE_ID"
```

**Vector Store Options:**
| Feature | OpenSearch Serverless | S3 (GraphRAG) |
|---------|-----------------------|---------------|
| Setup | Quick create in console | Requires additional configuration |
| Cost | Higher (serverless compute) | Lower (storage only) |
| Query Speed | Fast (optimized vector search) | Slower (on-demand processing) |
| Scalability | Auto-scales | Manual scaling |
| Best For | Production workloads, low latency | Cost-sensitive, smaller datasets |

For this lab, we use OpenSearch Serverless for simplicity and performance. For production, evaluate based on your latency and cost requirements.

---

## Part 3: Deploy Agent with Features

The agent in `agent.py` includes:
- GuardRails configuration via `BEDROCK_GUARDRAIL_ID`
- Knowledge Base tool via `BEDROCK_KNOWLEDGE_BASE_ID`
- Memory via `BEDROCK_MEMORY_ID`

### Step 3.1: Deploy with Features

```bash
# Pre-create memory ~3m
agentcore memory create langgraph_features_agent_mem --wait
export MEMORY_ID=$(aws bedrock-agentcore-control list-memories --region us-east-1 --query "memories[?contains(id, 'langgraph_features_agent')].id" --output text)
echo "Memory ID: $MEMORY_ID"

# Run the configuration wizard:
agentcore configure -e agent_with_all_features.py -n langgraph_full_demo -r us-east-1 --non-interactive

# Deploy with Memory ID to enable conversation persistence, or leave out the ID line if desired
agentcore launch \
  --env BEDROCK_GUARDRAIL_ID=$GUARDRAIL_ID \
  --env BEDROCK_GUARDRAIL_VERSION=$GUARDRAIL_VERSION \
  --env BEDROCK_KNOWLEDGE_BASE_ID=$KNOWLEDGE_BASE_ID \
  --env BEDROCK_MEMORY_ID=$MEMORY_ID
```

### Step 3.2: Add Knowledge Base Permissions

The agent's IAM role needs permission to query the Knowledge Base. Run this after deployment:

```bash
# Get the agent's execution role name (use awk to handle tab-separated output if multiple roles exist)
export AGENT_ROLE=$(aws iam list-roles --query "Roles[?contains(RoleName, 'AgentCoreSDKRuntime')].RoleName" --output text | awk '{print $1}')

# Add Knowledge Base access policy
aws iam put-role-policy \
  --role-name $AGENT_ROLE \
  --policy-name KnowledgeBaseAccessPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["bedrock:Retrieve"],
        "Resource": ["arn:aws:bedrock:us-east-1:'$(aws sts get-caller-identity --query Account --output text)':knowledge-base/*"]
      }
    ]
  }'
```

---

## Part 4: Test the Features

### Test GuardRails

```bash
# Test content filtering (should be blocked)
agentcore invoke '{"prompt": "Tell me how to hack a computer"}'

# Test PII handling (should be blocked/anonymized)
agentcore invoke '{"prompt": "My SSN is 123-45-6789"}'

# Test denied topics (if configured)
agentcore invoke '{"prompt": "Give me specific stock investment advice"}'
```

### Test Knowledge Base

```bash
# Query your documents
agentcore invoke '{"prompt": "What products does AcmeCorp offer?"}'
agentcore invoke '{"prompt": "How do I contact customer support?"}'
agentcore invoke '{"prompt": "What is the return policy?"}'
```

### Test Memory

AgentCore Memory provides persistent conversation state using LangGraph's checkpointing system. Here's how it works:

- **Stateless by default**: Without a `thread_id`, each request is independent (no conversation history)
- **thread_id**: Groups messages into a conversation. Same thread_id = same conversation context
- **Persistence**: Conversation state is stored in AgentCore's managed memory service, surviving agent restarts
- **Isolation**: Different thread_ids are completely isolated - the agent has no knowledge across threads

> **Important** GuardRails scan the entire conversation context. If blocked responses accumulate in a thread, subsequent requests may also be blocked. Use unique `thread_id` values for independent conversations, or omit `thread_id` for stateless operation

```bash
# Step 1: Introduce yourself
agentcore invoke '{"prompt": "My name is Alice and I work at TechCorp", "thread_id": "session-1"}'

# Step 2: Test recall
agentcore invoke '{"prompt": "What is my name and where do I work?", "thread_id": "session-1"}'
# Expected: Should remember that Alice works at TechCorp

# Step 3: Test isolation
agentcore invoke '{"prompt": "What is my name and where do I work?", "thread_id": "session-2"}'
# Expected: Should NOT know the name or place of occupation. Note that omitting the session would also work for our setup

```

## Cleanup

Remove all AWS resources created by this deployment:

```bash
agentcore destroy --force

# Delete GuardRail
aws bedrock delete-guardrail --guardrail-identifier $GUARDRAIL_ID

# Delete Memory
aws bedrock-agent delete-memory --memory-id $MEMORY_ID

# Delete Cloudwatch log groups
aws logs describe-log-groups --log-group-name-prefix /aws/bedrock-agentcore/runtimes/ --query 'logGroups[].logGroupName' --output text

# Delete S3 Bucket
aws s3 rb s3://langgraph-lab-kb-$(aws sts get-caller-identity --query Account --output text) --force

# Delete Knowledge Base (via console - includes vector store cleanup)
```

This deletes the AgentCore Runtime agent, ECR repository, and CodeBuild project.

## Troubleshooting

**"Access denied" errors:**
- Ensure your AWS credentials have permissions for Bedrock, ECR, CodeBuild, and IAM
- Check [AWS Permissions Guide](../AWS_PERMISSIONS.md) for required permissions
- Verify GuardRail, Knowledge Base, and Memory permissions

**"Resource not found" errors:**
- Verify resource IDs in `.bedrock_agentcore.yaml` are correct
- Check resources exist in the same region as your deployment
- Ensure resources are in "Active" state

**GuardRails not working:**
- Verify `BEDROCK_GUARDRAIL_ID` and `BEDROCK_GUARDRAIL_VERSION` are set
- Check GuardRail is active in AWS Console
- Review CloudWatch logs for GuardRail trace information

**GuardRails blocking all requests:**
- This can happen when blocked responses accumulate in a conversation thread
- The GuardRail scans the entire conversation context, including previously blocked messages
- Use a fresh `thread_id` or omit it entirely for stateless operations
- To reset, delete and recreate the memory. You will need to redeploy with a fresh memory ID

**Knowledge Base not returning results:**
- Verify data source is synced
- Check `BEDROCK_KNOWLEDGE_BASE_ID` is correct
- Test queries directly in AWS Console

**Knowledge Base returns "Access denied" or "technical issue" error**
- The agent's IAM role needs `bedrock:Retrieve` permission
- Run Step 3.4 to add the KnowledgeBaseAccessPolicy
- Verify the policy was attached: `aws iam list-role-policies --role-name $AGENT_ROLE`

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
