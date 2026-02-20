# AWS Bedrock Agents Integration Walkthrough

This comprehensive guide walks you through setting up and using three powerful AWS Bedrock Agents features in your LangGraph agents:

1. **GuardRails** - Content filtering and safety controls
2. **Knowledge Bases** - RAG (Retrieval Augmented Generation) for document retrieval
3. **Memory** - Persistent conversation state across sessions

Each feature can be enabled independently and works in both local development and deployed production environments.

## Table of Contents

- [Introduction](#introduction)
- [Prerequisites](#prerequisites)
- [GuardRails Setup](#guardrails-setup)
- [Knowledge Base Setup](#knowledge-base-setup)
- [Memory Setup](#memory-setup)
- [End-to-End Example](#end-to-end-example)
- [Troubleshooting](#troubleshooting)

## Introduction

AWS Bedrock Agents provides enterprise-grade capabilities that enhance your AI agents with safety, knowledge grounding, and conversation persistence. This walkthrough demonstrates how to integrate these features into the AgentCore demo project.

### What You'll Learn

- How to create and configure GuardRails for content safety
- How to set up Knowledge Bases for RAG capabilities
- How to enable Memory for conversation persistence
- How to combine all three features in a production-ready agent
- Best practices for testing and troubleshooting

### Architecture Overview

```
┌─────────────────┐     ┌──────────────────────┐      ┌─────────────────┐
│   Your Agent    │────▶│   ChatBedrock LLM    │────▶│   GuardRails    │
│   (LangGraph)   │     │   (Claude Sonnet)    │      │ Content Filter  │
└─────────────────┘     └──────────────────────┘      └─────────────────┘
        │                                                       │
        │                                                       ▼
        ▼                                                  ┌─────────┐
┌─────────────────┐                                        │ Bedrock │
│ Knowledge Base  │◀──────────────────────────────────────│   API   │
│  Tool (RAG)     │                                        └─────────┘
└─────────────────┘                                            │
        │                                                       │
        ▼                                                       ▼
┌─────────────────┐                                   ┌─────────────────┐
│  Memory Store   │◀─────────────────────────────────│ AgentCore       │
│  (Persistence)  │                                   │ Memory Service  │
└─────────────────┘                                   └─────────────────┘
```

## Prerequisites

Before you begin, ensure you have the following:

### 1. AWS Account and Access

- **AWS Account** with access to Amazon Bedrock
- **AWS CLI** installed and configured with credentials
  ```bash
  aws configure
  ```

### 2. IAM Permissions

Your AWS user or role needs the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:ApplyGuardrail",
        "bedrock:GetGuardrail",
        "bedrock:Retrieve",
        "bedrock-agent-runtime:GetMemory",
        "bedrock-agent-runtime:PutMemory"
      ],
      "Resource": "*"
    }
  ]
}
```

See [AWS_PERMISSIONS.md](AWS_PERMISSIONS.md) for detailed IAM configuration.

### 3. Development Environment

- **Python 3.10+** installed
- **Virtual environment** (recommended)
- **Project dependencies** installed:
  ```bash
  cd local  # or deployed/
  python -m venv .venv
  source .venv/bin/activate  # On Windows: .venv\Scripts\activate
  pip install -r requirements.txt
  ```

### 4. Verify AWS Access

Test your AWS credentials and Bedrock access:

```bash
# Verify AWS credentials
aws sts get-caller-identity

# Verify Bedrock access
aws bedrock list-foundation-models --region us-east-1 \
  --query "modelSummaries[?contains(modelId, 'claude')].[modelId]" \
  --output table
```

If these commands succeed, you're ready to proceed!

### 5. Project Structure

Ensure you have the AgentCore demo project:

```
.
├── local/                              # Local development
│   ├── agent.py                        # Basic agent
│   ├── agent_with_memory.py            # Agent with Memory
│   ├── agent_with_all_features.py      # All features combined
│   └── requirements.txt
│
├── deployed/                           # AWS deployment
│   ├── agent.py                        # Deployed agent
│   ├── agent_with_all_features.py      # All features deployed
│   └── requirements.txt
│
└── docs/                               # Documentation
    ├── BEDROCK_AGENTS_WALKTHROUGH.md   # This file
    └── AWS_PERMISSIONS.md              # IAM permissions guide
```

---

**Next Steps:** Choose which feature to set up first:
- [GuardRails Setup](#guardrails-setup) - Start with content safety
- [Knowledge Base Setup](#knowledge-base-setup) - Add RAG capabilities
- [Memory Setup](#memory-setup) - Enable conversation persistence

Each feature is independent and can be configured in any order.


## GuardRails Setup

GuardRails provide content filtering and safety controls for your AI agents. They can block harmful content, filter PII, enforce denied topics, and apply custom word filters.

### What GuardRails Do

GuardRails intercept both user inputs and model outputs, checking them against configured policies:

- **Content Filters**: Block hate speech, violence, sexual content, insults, misconduct
- **PII Filters**: Detect and redact personally identifiable information
- **Denied Topics**: Prevent discussions on specific topics (e.g., financial advice, medical advice)
- **Word Filters**: Block or redact specific words or phrases
- **Contextual Grounding**: Ensure responses are grounded in provided context (for RAG)

[guardrail-flow-example](/Images/guardrail-flow.png)

You'll notice that guardrails occur in two places, during the input, and for the LLM output. These two flows can be refined during and after creation of the guardrail.

### Step 1: Create a GuardRail in AWS Console

1. **Navigate to Bedrock Console**
   - Go to [AWS Console > Bedrock > GuardRails](https://console.aws.amazon.com/bedrock)
   - Click **"Create GuardRail"**

2. **Configure Basic Settings**
   - **Name**: `my-agent-guardrail` (or your preferred name)
   - **Description**: "Content safety for my AI agent"
   - Click **"Next"**

3. **Configure Content Filters**
   
   Content filters block harmful content across six categories. For each category, set the filter strength:
   - **None**: No filtering
   - **Low**: Block only extreme violations
   - **Medium**: Balanced filtering (recommended)
   - **High**: Strict filtering
   
   **Recommended Configuration for General Use:**
   ```
   Hate Speech:        Medium
   Insults:            Medium
   Sexual Content:     High
   Violence:           Medium
   Misconduct:         Medium
   Prompt Attacks:     High
   ```
   
   Click **"Next"**

4. **Configure Denied Topics** (Optional)
   
   Denied topics prevent the agent from discussing specific subjects.
   
   **Example: Block Financial Advice**
   - Click **"Add denied topic"**
   - **Name**: `financial-advice`
   - **Definition**: "Providing specific financial advice, investment recommendations, or stock tips"
   - **Examples**:
     - "Should I invest in Bitcoin?"
     - "What stocks should I buy?"
     - "How should I allocate my 401k?"
   
   **Example: Block Medical Advice**
   - Click **"Add denied topic"**
   - **Name**: `medical-advice`
   - **Definition**: "Providing medical diagnoses, treatment recommendations, or medication advice"
   - **Examples**:
     - "What medicine should I take for my headache?"
     - "Do I have cancer?"
     - "Should I stop taking my prescription?"
   
   Click **"Next"**

5. **Configure Word Filters** (Optional)
   
   Word filters block or redact specific words or phrases.
   
   **Example: Block Profanity**
   - Click **"Add word filter"**
   - **Action**: Block (stops the entire response) or Redact (replaces with ***)
   - **Words**: Add specific words to filter
   
   **Example: Redact PII**
   - Click **"Add word filter"**
   - **Action**: Redact
   - **Pattern**: Use regex patterns for emails, phone numbers, SSNs
   
   Click **"Next"**

6. **Configure Sensitive Information Filters** (Optional)
   
   Automatically detect and filter PII:
   - **Email addresses**
   - **Phone numbers**
   - **Social Security Numbers**
   - **Credit card numbers**
   - **Names and addresses**
   
   Select the PII types to filter and choose **Block** or **Redact**.
   
   Click **"Next"**

7. **Review and Create**
   - Review your configuration
   - Click **"Create GuardRail"**
   - **Copy the GuardRail ID** (format: `gr-abc123xyz`)
   - **Note the Version** (starts at `1`, or use `DRAFT` for testing)

### Step 2: Configure Your Agent

If you're deploying, here's how GuardRails are integrated in the agent code, you can also review [guardrails in practice](/deployed/agent_with_all_features.py):

```python
import os
from langchain_aws import ChatBedrock

# Configuration from environment variables
GUARDRAIL_ID = "gr-123abc4567"
GUARDRAIL_VERSION = "DRAFT"

# Build GuardRails configuration
guardrails_config = {
    "guardrailIdentifier": GUARDRAIL_ID,
    "guardrailVersion": GUARDRAIL_VERSION,
    "trace": "enabled"  # Enable trace for debugging
}

# Initialize LLM with GuardRails
llm = ChatBedrock(
    model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    region_name="us-east-1",
    guardrails=guardrails_config  # GuardRails applied automatically
)

# Handle GuardRails interventions
try:
    async for event in agent.astream(input_data, config=config):
        # Process streaming response
        yield process_event(event)
except Exception as e:
    error_msg = str(e).lower()
    if "guardrail" in error_msg or "intervention" in error_msg:
        yield "I apologize, but I cannot provide that response..."
```

### Step 3: Run Your Agent with GuardRails

**Local Mode:**
```bash
cd local
python agent_with_all_features.py
```

**Deployed Mode:**
```bash
cd deployed
# Add environment variables to .bedrock_agentcore.yaml
agentcore launch
```

### Example Use Cases

#### Use Case 1: PII Filtering

**Scenario**: Prevent the agent from exposing or processing sensitive personal information.

**Configuration**:
- Enable **Sensitive Information Filters** for emails, phone numbers, SSNs
- Action: **Redact**

**Test Prompt**:
```
User: My email is john.doe@example.com and my phone is 555-123-4567
```

**Expected Behavior**:
```
Assistant: I see you've provided contact information. However, I've redacted 
the sensitive details for your privacy. How can I help you today?
```
[pii-example](/Images/pii-example.png)

#### Use Case 2: Topic Restrictions

**Scenario**: Prevent the agent from providing financial or medical advice.

**Configuration**:
- Add **Denied Topic**: `financial-advice`
- Add **Denied Topic**: `medical-advice`

**Test Prompt**:
```
User: What stocks should I invest in?
```

**Expected Behavior**:
```
I apologize, but I cannot provide that response as it violates content 
safety policies. Please rephrase your request or ask something different.
```

[financial-example](/Images/financial-advice.png)


### Troubleshooting GuardRails

**Issue**: GuardRails not blocking content

**Solutions**:
- Verify `BEDROCK_GUARDRAIL_ID` is set correctly
- Check GuardRail version matches `BEDROCK_GUARDRAIL_VERSION`
- Ensure GuardRail is in "Active" state in AWS Console
- Try increasing filter strength (Low → Medium → High)
- Check CloudWatch logs for GuardRail trace information

**Issue**: Too many false positives (blocking legitimate content)

**Solutions**:
- Reduce filter strength (High → Medium → Low)
- Review and refine denied topics definitions
- Use more specific word filters instead of broad content filters
- Test with `DRAFT` version before deploying to production

**Issue**: "Access denied" errors

**Solutions**:
- Verify IAM permissions include `bedrock:ApplyGuardrail`
- Check GuardRail resource policy allows your IAM role
- Ensure GuardRail is in the same region as your agent

**Issue**: GuardRails not working in deployed mode

**Solutions**:
- Add environment variables to `.bedrock_agentcore.yaml`
- Verify IAM execution role has GuardRails permissions
- Check CloudWatch logs for initialization errors
- Redeploy after configuration changes: `agentcore launch`

### Best Practices

1. **Start with DRAFT**: Test GuardRails with `DRAFT` version before creating numbered versions
2. **Iterate on Filters**: Start with Medium strength and adjust based on testing
3. **Monitor Interventions**: Review CloudWatch logs to understand what's being blocked
4. **Version Control**: Create new versions when making significant changes
5. **Test Thoroughly**: Use diverse test prompts to validate behavior
6. **Document Policies**: Keep a record of why specific filters and topics are configured
7. **Balance Safety and Usability**: Avoid over-filtering that frustrates users

### Next Steps

- [Knowledge Base Setup](#knowledge-base-setup) - Add RAG capabilities
- [Memory Setup](#memory-setup) - Enable conversation persistence
- [End-to-End Example](#end-to-end-example) - Combine all features


## Knowledge Base Setup

Knowledge Bases enable RAG (Retrieval Augmented Generation) by indexing your documents and retrieving relevant content to ground agent responses in your own data.

### What Knowledge Bases Do

Knowledge Bases provide semantic search over your documents:

- **Document Ingestion**: Index documents from S3, web crawlers, or other data sources
- **Vector Embeddings**: Convert documents to embeddings using Bedrock embedding models
- **Semantic Search**: Find relevant content using vector similarity
- **Contextual Retrieval**: Return top-N most relevant document chunks
- **Grounded Responses**: Agent uses retrieved context to generate accurate answers

### How Knowledge Bases Work

```
1. Documents → 2. Chunking → 3. Embeddings → 4. Vector Store
                                                      ↓
User Query → Query Embedding → Vector Search → Top Results → Agent
```

### Step 1: Prepare Your Documents

Knowledge Bases support various document formats:

**Supported Formats**:
- Text files (`.txt`, `.md`)
- PDFs (`.pdf`)
- Word documents (`.doc`, `.docx`)
- HTML files (`.html`)
- CSV files (`.csv`)

**Best Practices**:
- Use clear, well-structured documents with well defined sections
- Include relevant metadata (titles, dates, authors)
- Keep documents focused on specific topics

### Step 2: Create an S3 Bucket for Your Documents

1. **Create S3 Bucket**
   ```bash
   aws s3 mb s3://my-knowledge-base-docs --region us-east-1
   ```

2. **Upload Documents**
   ```bash
   aws s3 cp ./docs/ s3://my-knowledge-base-docs/ --recursive
   ```

3. **Verify Upload**
   ```bash
   aws s3 ls s3://my-knowledge-base-docs/
   ```

### Step 3: Create a Knowledge Base in AWS Console

1. **Navigate to Bedrock Console**
   - Go to [AWS Console > Bedrock > Knowledge Bases](https://console.aws.amazon.com/bedrock)
   - Click **"Create Knowledge Base"**

2. **Configure Knowledge Base Details**
   - **Name**: `my-agent-knowledge-base`
   - **Description**: "Product documentation for my AI agent"
   - **IAM Role**: Choose "Create and use a new service role" (recommended)
   - Click **"Next"**

3. **Configure Data Source**
   
   **Option A: S3 Data Source**
   - **Data source name**: `s3-docs`
   - **S3 URI**: `s3://my-knowledge-base-docs/`
   - **Chunking strategy**: 
     - **Default chunking**: Automatic chunking (recommended for most use cases)
     - **Fixed-size chunking**: Specify chunk size (e.g., 300 tokens, 20% overlap)
     - **No chunking**: Use for pre-chunked documents
   - **Metadata**: Optional - add custom metadata fields
   
   Click **"Next"**

4. **Configure Embeddings Model**
   
   Choose an embedding model to convert documents to vectors:
   
   **Recommended Models**:
   - **Titan Embeddings G1 - Text** (Default, good balance)
     - Dimensions: 1536
     - Max tokens: 8192
     - Best for: General purpose, English text
   
   Click **"Next"**

5. **Configure Vector Store**
   
   Choose where to store document embeddings:
   
   **Option A: Amazon OpenSearch Serverless** (Recommended)
   - **Collection**: Create new or use existing
   - **Collection name**: `my-kb-collection`
   - **Encryption**: AWS managed key (default)
   - **Network**: VPC or Public (Public for easier setup)
   - **Advantages**: Fully managed, auto-scaling, no infrastructure
   
   Click **"Next"**

6. **Review and Create**
   - Review all configurations
   - Click **"Create Knowledge Base"**
   - **Copy the Knowledge Base ID** (format: `KB123ABC`)
   - Wait for creation to complete (2-5 minutes)

### Step 4: Sync Your Data Source

After creating the Knowledge Base, you need to ingest your documents:

1. **Navigate to Your Knowledge Base**
   - Go to [Bedrock > Knowledge Bases](https://console.aws.amazon.com/bedrock)
   - Click on your Knowledge Base name

2. **Sync Data Source**
   - Click on your data source (e.g., `s3-docs`)
   - Click **"Sync"**
   - Wait for sync to complete (time depends on document count)

3. **Verify Ingestion**
   - Check **"Sync history"** for status
   - View **"Documents"** tab to see ingested documents
   - Note the number of chunks created

**Sync Status**:
- **In Progress**: Documents are being processed
- **Completed**: All documents successfully ingested
- **Failed**: Check error logs for issues

### Step 5: Test Your Knowledge Base

Test retrieval directly in the AWS Console:

1. **Navigate to Your Knowledge Base**
2. **Click "Test"** tab
3. **Enter a test query**: "How do I install Widget X?"
4. **Review results**:
   - Check relevance of retrieved chunks
   - Verify source documents are correct
   - Adjust chunking strategy if needed

### Step 7: Run Your Agent with Knowledge Base

**Local Mode:**
```bash
cd local
python agent_with_all_features.py
```

**Deployed Mode:**
```bash
cd deployed
# Add BEDROCK_KNOWLEDGE_BASE_ID to .bedrock_agentcore.yaml
agentcore launch
```

### Example Use Cases

#### Use Case 1: Product Documentation Q&A

**Scenario**: Customer support agent answers questions using product documentation.

**Documents**: Product manuals, FAQs, troubleshooting guides

**Test Prompts**:
```
User: How do I reset my Widget X to factory settings?
User: What are the technical specifications of Widget X?
User: My Widget X won't turn on, what should I do?
```

**Expected Behavior**:
```
Assistant: Based on the product documentation, to reset Widget X to factory 
settings: [retrieves and cites specific steps from manual]
```

#### Use Case 2: Internal Knowledge Base

**Scenario**: Employee assistant answers questions using company policies and procedures.

**Documents**: HR policies, IT procedures, company handbook

**Test Prompts**:
```
User: What is the company's remote work policy?
User: How do I request PTO?
User: What are the IT security requirements for laptops?
```

**Expected Behavior**:
```
Assistant: According to the company handbook, the remote work policy states: 
[retrieves and summarizes relevant policy sections]
```

#### Use Case 3: Technical Documentation Search

**Scenario**: Developer assistant helps with API documentation and code examples.

**Documents**: API reference, code examples, integration guides

**Test Prompts**:
```
User: How do I authenticate with the API?
User: Show me an example of creating a user
User: What are the rate limits for the API?
```

**Expected Behavior**:
```
Assistant: Here's how to authenticate with the API based on the documentation:
[retrieves authentication section and code examples]
```

### Code Example

Here's how Knowledge Bases are integrated in the agent code:

```python
import os
from langchain_aws import AmazonKnowledgeBasesRetriever
from langchain_core.tools import tool

# Configuration from environment variable
KNOWLEDGE_BASE_ID = os.getenv("BEDROCK_KNOWLEDGE_BASE_ID", "")

@tool
def query_knowledge_base(query: str) -> str:
    """
    Search the knowledge base for relevant information using RAG.
    
    Args:
        query: The search query or question
        
    Returns:
        Formatted results from the knowledge base
    """
    try:
        # Initialize retriever
        retriever = AmazonKnowledgeBasesRetriever(
            knowledge_base_id=KNOWLEDGE_BASE_ID,
            region_name="us-east-1",
            retrieval_config={
                "vectorSearchConfiguration": {
                    "numberOfResults": 5  # Top 5 results
                }
            }
        )
        
        # Retrieve relevant documents
        results = retriever.get_relevant_documents(query)
        
        if not results:
            return "No relevant information found in the knowledge base."
        
        # Format results
        formatted = []
        for i, doc in enumerate(results, 1):
            formatted.append(f"Result {i}:\n{doc.page_content}\n")
        
        return "\n".join(formatted)
    
    except Exception as e:
        return f"Error querying knowledge base: {str(e)}"

# Add tool to agent
tools = [get_weather, query_knowledge_base]
agent = create_agent(model=llm, tools=tools, system_prompt=SYSTEM_PROMPT)
```

### Testing Your Knowledge Base

Use these test queries to validate your Knowledge Base:

**Test 1: Direct Question**
```
Prompt: What is [specific topic from your documents]?
Expected: Relevant information retrieved and cited
```

**Test 2: Multi-Document Query**
```
Prompt: Compare [topic A] and [topic B]
Expected: Information from multiple documents synthesized
```

**Test 3: Out-of-Scope Query**
```
Prompt: [Question about topic not in your documents]
Expected: "No relevant information found in the knowledge base"
```

**Test 4: Specific Detail**
```
Prompt: What is the exact value of [specific parameter/setting]?
Expected: Precise information retrieved from documentation
```

### Troubleshooting Knowledge Base

**Issue**: No results returned for queries

**Solutions**:
- Verify documents were successfully synced (check Sync history)
- Check if query matches document content (try broader queries)
- Review chunking strategy - documents may be chunked too large/small
- Increase `numberOfResults` in retrieval config
- Test query directly in AWS Console Test tab

**Issue**: Irrelevant results returned

**Solutions**:
- Improve document quality and structure
- Add more specific metadata to documents
- Adjust chunking strategy (smaller chunks for specific queries)
- Use more specific queries
- Consider using hybrid search (semantic + keyword)

**Issue**: "Knowledge Base not found" error

**Solutions**:
- Verify `BEDROCK_KNOWLEDGE_BASE_ID` is set correctly
- Check Knowledge Base exists in the correct region
- Ensure IAM permissions include `bedrock:Retrieve`
- Verify Knowledge Base is in "Active" state

**Issue**: Slow retrieval performance

**Solutions**:
- Reduce `numberOfResults` (fewer results = faster)
- Optimize document chunking (smaller chunks = faster search)
- Use OpenSearch Serverless for better performance
- Consider caching frequently accessed results

**Issue**: Documents not syncing

**Solutions**:
- Check S3 bucket permissions (Knowledge Base role needs read access)
- Verify document formats are supported
- Check CloudWatch logs for sync errors
- Ensure documents are not too large (max 50MB per document)
- Try re-syncing: Data source → Sync button

### Best Practices

1. **Document Quality**: Well-structured, clear documents produce better results
2. **Chunking Strategy**: Test different chunking sizes for your use case
3. **Regular Syncs**: Re-sync when documents are updated
4. **Monitor Usage**: Track retrieval metrics in CloudWatch
5. **Optimize Queries**: Use specific, focused queries for better results
6. **Metadata**: Add metadata to documents for better filtering
7. **Test Thoroughly**: Validate retrieval quality before production deployment
8. **Version Control**: Keep track of document versions and sync history

### Advanced Configuration

**Hybrid Search** (Semantic + Keyword):
```python
retrieval_config={
    "vectorSearchConfiguration": {
        "numberOfResults": 5,
        "overrideSearchType": "HYBRID"  # Combines semantic and keyword search
    }
}
```

**Metadata Filtering**:
```python
retrieval_config={
    "vectorSearchConfiguration": {
        "numberOfResults": 5,
        "filter": {
            "equals": {
                "key": "category",
                "value": "technical-docs"
            }
        }
    }
}
```

### Next Steps

- [Memory Setup](#memory-setup) - Enable conversation persistence
- [End-to-End Example](#end-to-end-example) - Combine all features
- [Troubleshooting](#troubleshooting) - Common issues and solutions


## Memory Setup

Memory provides persistent conversation state across sessions, allowing your agent to remember previous interactions and maintain context over multiple conversations.

### What Memory Does

Memory stores and retrieves conversation state:

- **Message History**: Complete record of user messages and assistant responses
- **Tool Call History**: Record of tool invocations and results
- **Agent State**: Intermediate steps and reasoning
- **Context Persistence**: Maintain conversation context across sessions
- **Multi-User Support**: Isolated memory for each user and conversation thread

### How Memory Works

```
Session 1:
User: "My name is Alice" → Agent: "Nice to meet you, Alice!" → [Saved to Memory]

Session 2 (later):
User: "What's my name?" → [Load from Memory] → Agent: "Your name is Alice!"
```

Memory is automatically managed by LangGraph's checkpointer system:
1. **Load**: Agent loads memory at the start of each turn
2. **Process**: Agent processes the user's message with full context
3. **Save**: Agent saves updated state after generating response

### Step 1: Create a Memory Resource in AWS Console

1. **Navigate to Bedrock Console**
   - Go to [AWS Console > Bedrock > AgentCore > Memory](https://console.aws.amazon.com/bedrock)
   - Click **"Create Memory"**

2. **Configure Memory Settings**
   - **Name**: `my-agent-memory`
   - **Description**: "Conversation persistence for my AI agent"
   - **Memory type**: Choose based on your needs:
     - **Session Memory**: Short-term memory for single sessions (default)
     - **Long-term Memory**: Persistent memory across multiple sessions
   - Click **"Create"**

3. **Copy Memory ID**
   - After creation, **copy the Memory ID** (format: `MEM123ABC`)
   - Note the region where Memory was created

### Step 2: Understand Memory Parameters

Memory uses two key parameters to organize conversations:

#### thread_id (Conversation Thread)

Identifies a specific conversation thread. Each thread has its own isolated memory.

**Usage Patterns**:
```python
# Single session per user
thread_id = "user-123-session-1"

# Multiple sessions per user
thread_id = f"user-{user_id}-session-{session_id}"

# Time-based sessions
thread_id = f"user-{user_id}-{date}"

# Topic-based sessions
thread_id = f"user-{user_id}-topic-{topic}"
```

**When to use different thread_ids**:
- New conversation topic
- Different time period (daily, weekly)
- Separate projects or contexts
- User explicitly requests "new conversation"

#### actor_id (User Identity)

Identifies the user or actor interacting with the agent.

**Usage Patterns**:
```python
# Authenticated user
actor_id = f"user-{user_id}"

# Anonymous user
actor_id = f"anonymous-{session_id}"

# Multi-tenant
actor_id = f"tenant-{tenant_id}-user-{user_id}"

# Role-based
actor_id = f"role-{role}-user-{user_id}"
```

**When to use different actor_ids**:
- Different users (always)
- Different roles or permissions
- Different tenants in multi-tenant systems

### Step 3: Configure Your Agent

Set environment variable with your Memory ID:

```bash
export BEDROCK_MEMORY_ID="MEM123ABC"
```

**For persistent configuration**:
```bash
echo 'export BEDROCK_MEMORY_ID="MEM123ABC"' >> ~/.bashrc
source ~/.bashrc
```

### Step 4: Run Your Agent with Memory

**Local Mode:**
```bash
cd local
python agent_with_all_features.py
```

**Deployed Mode:**
```bash
cd deployed
# Add BEDROCK_MEMORY_ID to .bedrock_agentcore.yaml
agentcore launch
```

### Example Use Cases

#### Use Case 1: Personalized Conversations

**Scenario**: Agent remembers user preferences and previous interactions.

**Configuration**:
```python
actor_id = "user-alice"
thread_id = "user-alice-general"
```

**Conversation**:
```
Session 1:
User: My name is Alice and I prefer concise answers
Agent: Got it, Alice! I'll keep my responses concise.

[Exit and restart]

Session 2:
User: What's my name?
Agent: Your name is Alice.

User: Do you remember my preference?
Agent: Yes, you prefer concise answers.
```

#### Use Case 2: Multi-Turn Task Completion

**Scenario**: Agent maintains context across multiple steps of a complex task.

**Configuration**:
```python
actor_id = "user-bob"
thread_id = "user-bob-project-setup"
```

**Conversation**:
```
Turn 1:
User: I need to set up a new project
Agent: Great! What type of project are you setting up?

Turn 2:
User: A Python web application
Agent: Perfect! For a Python web application, I recommend...

Turn 3:
User: What did I say I was building?
Agent: You're setting up a Python web application.
```

#### Use Case 3: Customer Support with History

**Scenario**: Support agent remembers previous support tickets and issues.

**Configuration**:
```python
actor_id = f"customer-{customer_id}"
thread_id = f"customer-{customer_id}-support-{ticket_id}"
```

**Conversation**:
```
Ticket 1:
User: My Widget X isn't working
Agent: Let me help you troubleshoot...
[Resolution steps]

Ticket 2 (later):
User: I'm having the same issue again
Agent: I see you had this issue before. Let's check if...
```

#### Use Case 4: Session-Based Conversations

**Scenario**: Separate conversations by time period (daily sessions).

**Configuration**:
```python
from datetime import date
actor_id = "user-charlie"
thread_id = f"user-charlie-{date.today()}"
```

**Behavior**:
- Each day starts a fresh conversation
- Previous days' conversations are preserved
- User can reference "yesterday's conversation" if needed

### Code Example

Here's how Memory is integrated in the agent code:

```python
import os
from langgraph_checkpoint_aws import AgentCoreMemorySaver

# Configuration from environment variable
MEMORY_ID = os.getenv("BEDROCK_MEMORY_ID", "")

# Initialize Memory checkpointer
checkpointer = AgentCoreMemorySaver(
    MEMORY_ID,
    region_name="us-east-1"
)

# Create agent with Memory
agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer  # Enable memory persistence
)

# Use agent with Memory
async def chat(prompt: str, actor_id: str, thread_id: str):
    """Chat with memory persistence."""
    input_data = {"messages": [{"role": "user", "content": prompt}]}
    
    # Config identifies which conversation to load/save
    config = {
        "configurable": {
            "thread_id": thread_id,  # Conversation thread
            "actor_id": actor_id,    # User identity
        }
    }
    
    # Agent automatically loads and saves memory
    async for event in agent.astream(input_data, config=config):
        # Process streaming response
        yield process_event(event)
```

### Testing Your Memory

Use these test scenarios to validate Memory persistence:

**Test 1: Basic Persistence**
```
Session 1:
User: Remember that my favorite color is blue
Agent: I'll remember that your favorite color is blue.

[Exit and restart with same thread_id and actor_id]

Session 2:
User: What's my favorite color?
Agent: Your favorite color is blue.
```

**Test 2: Multi-Turn Context**
```
Turn 1:
User: I'm planning a trip to Paris
Agent: That sounds exciting! When are you planning to go?

Turn 2:
User: In June
Agent: Great! June is a wonderful time to visit Paris...

Turn 3:
User: Where am I going again?
Agent: You're planning a trip to Paris in June.
```

**Test 3: Thread Isolation**
```
Thread 1 (thread_id="session-1"):
User: My name is Alice
Agent: Nice to meet you, Alice!

Thread 2 (thread_id="session-2"):
User: What's my name?
Agent: I don't have that information yet. What's your name?
```

**Test 4: Actor Isolation**
```
Actor 1 (actor_id="user-alice"):
User: My favorite food is pizza
Agent: Got it, your favorite food is pizza.

Actor 2 (actor_id="user-bob"):
User: What's my favorite food?
Agent: I don't have that information yet. What's your favorite food?
```

### Memory Limitations and Best Practices

#### Limitations

1. **Storage Limits**: Memory has storage limits per thread (check AWS documentation)
2. **Retention Period**: Memory may have retention limits (check AWS documentation)
3. **Performance**: Very long conversations may slow down retrieval
4. **Cost**: Memory storage incurs costs based on usage

#### Best Practices

1. **Thread Management**
   - Create new threads for new topics or time periods
   - Don't reuse threads indefinitely (consider daily/weekly rotation)
   - Use descriptive thread_id patterns for debugging

2. **Actor Management**
   - Use consistent actor_id format across your application
   - Include tenant/organization in multi-tenant systems
   - Consider privacy implications of storing user data

3. **Memory Hygiene**
   - Implement thread cleanup for old conversations
   - Provide users with "clear history" functionality
   - Monitor memory usage and costs

4. **Error Handling**
   - Always handle Memory initialization failures gracefully
   - Fall back to stateless mode if Memory is unavailable
   - Log Memory errors for debugging

5. **Testing**
   - Test with different thread_id and actor_id combinations
   - Verify thread isolation (no cross-contamination)
   - Test memory persistence across restarts

6. **Privacy and Security**
   - Implement data retention policies
   - Provide users with data deletion options
   - Encrypt sensitive information before storing
   - Comply with privacy regulations (GDPR, CCPA, etc.)

### Advanced Memory Patterns

#### Pattern 1: Hierarchical Threads

Organize conversations hierarchically:
```python
# Organization > Project > Session
thread_id = f"org-{org_id}-project-{project_id}-session-{session_id}"
```

#### Pattern 2: Shared Memory

Multiple actors sharing the same conversation:
```python
# Team collaboration
thread_id = f"team-{team_id}-project-{project_id}"
actor_id = f"user-{user_id}"  # Different actors, same thread
```

#### Pattern 3: Memory Summarization

For very long conversations, periodically summarize:
```python
# After N turns, create summary and start new thread
if turn_count > 50:
    summary = agent.summarize_conversation()
    new_thread_id = f"{thread_id}-continued"
    # Start new thread with summary as context
```

#### Pattern 4: Conditional Memory

Enable/disable memory based on user preference:
```python
# User opts out of memory
if user_preferences.get("enable_memory"):
    checkpointer = AgentCoreMemorySaver(MEMORY_ID)
else:
    checkpointer = None  # Stateless mode
```

### Troubleshooting Memory

**Issue**: Memory not persisting across sessions

**Solutions**:
- Verify `BEDROCK_MEMORY_ID` is set correctly
- Ensure same `thread_id` and `actor_id` are used across sessions
- Check Memory resource exists in AWS Console
- Verify IAM permissions include `bedrock-agent-runtime:GetMemory` and `PutMemory`
- Check CloudWatch logs for Memory errors

**Issue**: "Memory not found" error

**Solutions**:
- Verify Memory ID is correct
- Check Memory exists in the correct region
- Ensure Memory is in "Active" state
- Verify IAM permissions

**Issue**: Conversations mixing between users

**Solutions**:
- Verify different `actor_id` for each user
- Check thread_id generation logic
- Review config parameter passing
- Test thread isolation explicitly

**Issue**: Memory initialization fails

**Solutions**:
- Check AWS credentials are configured
- Verify IAM permissions
- Ensure Memory resource exists
- Check network connectivity to AWS
- Review CloudWatch logs for detailed errors

**Issue**: Slow performance with long conversations

**Solutions**:
- Implement thread rotation (start new threads periodically)
- Summarize old conversations
- Limit conversation history length
- Consider caching recent messages locally

### Next Steps

- [End-to-End Example](#end-to-end-example) - Combine all three features
- [Troubleshooting](#troubleshooting) - Common issues and solutions


## End-to-End Example

This section demonstrates how to use all three Bedrock Agents features together in a real-world scenario: a customer support agent with safety controls, knowledge base access, and conversation memory.

### Scenario: Customer Support Agent

**Requirements**:
- **GuardRails**: Block inappropriate content and PII
- **Knowledge Base**: Access product documentation
- **Memory**: Remember customer information and previous issues

### Step 1: Set Up All Features

Follow the setup instructions for each feature:

1. **GuardRails**: [GuardRails Setup](#guardrails-setup)
   - Create GuardRail with content filters and PII detection
   - Configure denied topics (e.g., financial advice, medical advice)

2. **Knowledge Base**: [Knowledge Base Setup](#knowledge-base-setup)
   - Upload product documentation to S3
   - Create Knowledge Base with product docs
   - Sync data source

3. **Memory**: [Memory Setup](#memory-setup)
   - Create Memory resource
   - Configure thread_id and actor_id patterns

### Step 2: Configure Environment Variables

Set all three feature IDs:

```bash
# GuardRails
export BEDROCK_GUARDRAIL_ID="gr-abc123xyz"
export BEDROCK_GUARDRAIL_VERSION="1"

# Knowledge Base
export BEDROCK_KNOWLEDGE_BASE_ID="KB123ABC"

# Memory
export BEDROCK_MEMORY_ID="MEM123ABC"
```

### Step 3: Run the Complete Agent

**Local Mode**:
```bash
cd local
python agent_with_all_features.py
```

**Deployed Mode**:
```bash
cd deployed
# Add all environment variables to .bedrock_agentcore.yaml
agentcore launch
```

### Step 4: Test the Complete Integration

#### Test Scenario 1: Normal Customer Support Flow

**Conversation**:
```
User: Hi, I'm having trouble with my Widget X
Agent: Hello! I'd be happy to help you with your Widget X. What specific 
issue are you experiencing?

User: It won't turn on
Agent: Let me check the troubleshooting guide for you.
[Agent uses query_knowledge_base tool]
Agent: According to the product documentation, here are the steps to 
troubleshoot a Widget X that won't turn on:
1. Check if the power cable is securely connected
2. Verify the power outlet is working
3. Try pressing and holding the power button for 10 seconds
4. Check if the battery is charged (if applicable)

Have you tried these steps?

User: Yes, I tried all of those
Agent: I see. Since you've tried the basic troubleshooting steps, the issue 
might require service. Let me note this in your support history.
[Memory saves this interaction]

User: Thanks for your help
Agent: You're welcome! If you have any other questions, feel free to ask.
```

**Features in Action**:
- ✅ **Memory**: Conversation context maintained across turns
- ✅ **Knowledge Base**: Retrieved troubleshooting steps from documentation
- ✅ **GuardRails**: No intervention (normal conversation)

#### Test Scenario 2: GuardRails Intervention

**Conversation**:
```
User: [Attempts to share credit card number]
Agent: I apologize, but I cannot process that information as it contains 
sensitive personal data. For your security, please do not share credit card 
numbers, social security numbers, or other sensitive information in this chat.

How else can I help you today?
```

**Features in Action**:
- ✅ **GuardRails**: Blocked PII (credit card number)
- ✅ **Memory**: Conversation continues normally after intervention
- ✅ **Knowledge Base**: Available if needed

#### Test Scenario 3: Knowledge Base + Memory

**Conversation**:
```
Session 1:
User: What are the technical specifications of Widget X?
Agent: Let me look that up for you.
[Agent uses query_knowledge_base tool]
Agent: According to the product documentation, Widget X has the following 
specifications:
- Dimensions: 10" x 5" x 3"
- Weight: 2.5 lbs
- Power: 120V AC
- Connectivity: WiFi 802.11ac, Bluetooth 5.0
[Memory saves this interaction]

[Exit and restart with same thread_id]

Session 2:
User: What were those specs you mentioned earlier?
Agent: Earlier I shared the technical specifications for Widget X:
- Dimensions: 10" x 5" x 3"
- Weight: 2.5 lbs
- Power: 120V AC
- Connectivity: WiFi 802.11ac, Bluetooth 5.0
```

**Features in Action**:
- ✅ **Knowledge Base**: Retrieved specifications from documentation
- ✅ **Memory**: Remembered previous conversation across sessions
- ✅ **GuardRails**: No intervention (normal conversation)

#### Test Scenario 4: All Features Combined

**Conversation**:
```
Session 1:
User: My name is Alice and I need help with Widget X
Agent: Nice to meet you, Alice! I'm here to help with your Widget X. 
What do you need assistance with?
[Memory saves: user name is Alice]

User: How do I connect it to WiFi?
Agent: Let me find the WiFi setup instructions for you.
[Agent uses query_knowledge_base tool]
Agent: Here's how to connect Widget X to WiFi:
1. Press the Settings button
2. Select "Network" from the menu
3. Choose "WiFi Setup"
4. Select your network and enter the password
[Memory saves: helped with WiFi setup]

User: [Attempts to ask for financial advice]
Agent: I apologize, but I cannot provide that response as it violates 
content safety policies. Please rephrase your request or ask something 
different.
[GuardRails blocks denied topic]

User: Okay, thanks for the WiFi help
Agent: You're welcome, Alice! Let me know if you need anything else.

[Exit and restart with same thread_id]

Session 2:
User: What's my name?
Agent: Your name is Alice.
[Memory retrieved from previous session]

User: What did you help me with last time?
Agent: Last time I helped you connect your Widget X to WiFi. I provided 
the step-by-step setup instructions.
[Memory retrieved from previous session]
```

**Features in Action**:
- ✅ **Memory**: Remembered user name and previous interactions across sessions
- ✅ **Knowledge Base**: Retrieved WiFi setup instructions
- ✅ **GuardRails**: Blocked denied topic (financial advice)

### Advanced Use Cases

#### Use Case 1: Multi-User Support System

**Scenario**: Support system handling multiple customers simultaneously.

**Configuration**:
```python
# Each customer gets unique actor_id and thread_id
customer_1_config = {
    "actor_id": "customer-12345",
    "thread_id": "customer-12345-ticket-001"
}

customer_2_config = {
    "actor_id": "customer-67890",
    "thread_id": "customer-67890-ticket-002"
}
```

**Benefits**:
- Isolated memory per customer
- Shared knowledge base for all customers
- Consistent safety controls via GuardRails

#### Use Case 2: Escalation with Context

**Scenario**: Agent escalates to human support with full context.

**Implementation**:
```python
# When escalation is needed
conversation_history = get_memory_history(thread_id, actor_id)
escalation_ticket = {
    "customer_id": actor_id,
    "conversation_history": conversation_history,
    "retrieved_docs": knowledge_base_results,
    "guardrail_interventions": intervention_log
}
# Send to human support system
```

**Benefits**:
- Human agent has full context
- No need for customer to repeat information
- Knowledge base results included for reference

#### Use Case 3: Proactive Support

**Scenario**: Agent proactively offers help based on memory.

**Conversation**:
```
User: Hi
Agent: Welcome back! I see you were having trouble with WiFi setup last 
time. Is everything working now, or do you need additional help?
[Memory: previous issue was WiFi setup]
```

**Benefits**:
- Personalized experience
- Faster issue resolution
- Improved customer satisfaction

#### Use Case 4: Compliance and Audit

**Scenario**: Track all interactions for compliance.

**Implementation**:
```python
# Log all interactions with features
audit_log = {
    "timestamp": datetime.now(),
    "actor_id": actor_id,
    "thread_id": thread_id,
    "guardrail_interventions": guardrail_log,
    "knowledge_base_queries": kb_query_log,
    "memory_operations": memory_op_log
}
# Store in audit system
```

**Benefits**:
- Complete audit trail
- Compliance with regulations
- Incident investigation capability

### Verification Checklist

Use this checklist to verify all features are working correctly:

#### Local Mode Verification

- [ ] **GuardRails**
  - [ ] Agent blocks inappropriate content
  - [ ] Agent redacts or blocks PII
  - [ ] Agent blocks denied topics
  - [ ] Agent continues normally after intervention

- [ ] **Knowledge Base**
  - [ ] Agent retrieves relevant documents
  - [ ] Agent cites sources correctly
  - [ ] Agent handles "no results" gracefully
  - [ ] Agent formats results clearly

- [ ] **Memory**
  - [ ] Agent remembers information within session
  - [ ] Agent remembers information across sessions
  - [ ] Different threads are isolated
  - [ ] Different actors are isolated

- [ ] **Integration**
  - [ ] All three features work together
  - [ ] No conflicts between features
  - [ ] Error handling works correctly
  - [ ] Performance is acceptable

#### Deployed Mode Verification

- [ ] **Deployment**
  - [ ] Environment variables configured in `.bedrock_agentcore.yaml`
  - [ ] Agent deploys successfully
  - [ ] Agent responds to invocations

- [ ] **GuardRails**
  - [ ] Same behavior as local mode
  - [ ] IAM permissions configured correctly
  - [ ] CloudWatch logs show GuardRails activity

- [ ] **Knowledge Base**
  - [ ] Same behavior as local mode
  - [ ] IAM permissions configured correctly
  - [ ] Retrieval performance is acceptable

- [ ] **Memory**
  - [ ] Same behavior as local mode
  - [ ] IAM permissions configured correctly
  - [ ] State persists across invocations

- [ ] **Monitoring**
  - [ ] CloudWatch logs capture all activity
  - [ ] Metrics are being recorded
  - [ ] Errors are logged appropriately

### Performance Considerations

#### Latency

**Expected Latencies** (approximate):
- **GuardRails**: +50-100ms per request
- **Knowledge Base**: +200-500ms per query
- **Memory**: +50-100ms per load/save

**Optimization Tips**:
- Cache Knowledge Base results for common queries
- Use smaller `numberOfResults` for faster retrieval
- Implement request timeouts
- Monitor and optimize slow queries

#### Cost

**Cost Factors**:
- **GuardRails**: Per request
- **Knowledge Base**: Storage + retrieval requests
- **Memory**: Storage + read/write operations
- **LLM**: Token usage (input + output)

**Cost Optimization**:
- Use GuardRails only where needed
- Optimize Knowledge Base chunking to reduce storage
- Implement memory cleanup for old threads
- Monitor usage with AWS Cost Explorer

### Next Steps

Congratulations! You've successfully integrated all three Bedrock Agents features. Here's what to do next:

1. **Customize for Your Use Case**
   - Adjust GuardRails policies for your requirements
   - Add your own documents to Knowledge Base
   - Implement your memory management strategy

2. **Deploy to Production**
   - Follow [deployed/README.md](../deployed/README.md) for deployment
   - Configure production environment variables
   - Set up monitoring and alerting

3. **Monitor and Optimize**
   - Review CloudWatch logs regularly
   - Monitor costs and usage
   - Optimize based on user feedback

4. **Expand Capabilities**
   - Add custom tools for your domain
   - Integrate with your existing systems
   - Implement advanced features (summarization, escalation, etc.)

## Troubleshooting

This section covers common issues and solutions for all three features.

### General Troubleshooting

#### Issue: "AWS credentials not configured"

**Symptoms**:
- Error: "Unable to locate credentials"
- Error: "NoCredentialsError"

**Solutions**:
1. Run `aws configure` to set up credentials
2. Verify credentials: `aws sts get-caller-identity`
3. Check environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
4. For deployed mode, verify IAM role is attached

#### Issue: "Region mismatch"

**Symptoms**:
- Resources not found
- Access denied errors

**Solutions**:
1. Verify all resources are in the same region
2. Check `REGION` variable in agent code
3. Verify AWS CLI default region: `aws configure get region`
4. Explicitly set region in code: `region_name="us-east-1"`

#### Issue: "IAM permissions denied"

**Symptoms**:
- Error: "AccessDeniedException"
- Error: "User is not authorized"

**Solutions**:
1. Review [AWS_PERMISSIONS.md](AWS_PERMISSIONS.md) for required permissions
2. Verify IAM policy is attached to user/role
3. Check resource-based policies (GuardRails, Knowledge Base, Memory)
4. Wait a few minutes for IAM changes to propagate

### Feature-Specific Troubleshooting

See individual feature sections for detailed troubleshooting:
- [GuardRails Troubleshooting](#troubleshooting-guardrails)
- [Knowledge Base Troubleshooting](#troubleshooting-knowledge-base)
- [Memory Troubleshooting](#troubleshooting-memory)

### Getting Help

If you're still experiencing issues:

1. **Check CloudWatch Logs**
   - Go to CloudWatch > Log Groups
   - Look for error messages and stack traces

2. **Review AWS Documentation**
   - [Bedrock GuardRails Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html)
   - [Bedrock Knowledge Bases Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)
   - [Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)

3. **AWS Support**
   - Open a support case in AWS Console
   - Include error messages and CloudWatch logs

4. **Community Resources**
   - AWS re:Post forums
   - GitHub issues for LangChain and LangGraph
   - Stack Overflow with `amazon-bedrock` tag

---

## Summary

You've learned how to integrate three powerful AWS Bedrock Agents features:

✅ **GuardRails** - Content safety and filtering  
✅ **Knowledge Bases** - RAG for document retrieval  
✅ **Memory** - Conversation persistence  

Each feature enhances your agent's capabilities and can be used independently or combined for maximum effectiveness.

**Key Takeaways**:
- All features are optional and independently configurable
- Features work in both local and deployed modes
- Comprehensive error handling ensures reliability
- Proper testing and monitoring are essential

**Next Steps**:
- Customize for your specific use case
- Deploy to production
- Monitor and optimize performance
- Expand with additional capabilities

Happy building! 🚀
