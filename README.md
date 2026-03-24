# LangGraph + AWS Bedrock AgentCore Labs

Build and deploy AI agents using LangGraph with AWS Bedrock AgentCore. This repository provides a hands-on lab experience progressing from basic deployment to production-ready agents with evaluation.

## Lab Structure
```
Lab 1: Deploy Basic Agent       Lab 2: Add Features              Lab 3: LangGraph Eval        Lab 4: Strands Eval
┌───────────────────────┐      ┌───────────────────────┐        ┌───────────────────────┐    ┌───────────────────────┐
│ • Set up environment  │─────▶│ • Create GuardRail    │───────▶│ • OpenTelemetry       │    │ • Strands Agent       │
│ • Deploy to AgentCore │      │ • Create Knowledge    │        │   Tracing             │    │ • Working Evaluations │
│ • Test via CLI/SDK    │      │   Base                │        │ • Online Evaluation   │    │ • On-demand & Online  │
│                       │      │ • Add Memory          │        │ • GenAI Dashboard     │    │ • Full API Support    │
│                       │      │ • Deploy with all     │        │ • (Known Limitations) │    │                       │
│                       │      │   features            │        │                       │    │                       │
└───────────────────────┘      └───────────────────────┘        └───────────────────────┘    └───────────────────────┘
                                                                         │                            ▲
                                                                         │    If evaluations needed   │
                                                                         └────────────────────────────┘
```

### Prerequistes

- Python 3.10+
- AWS account with Bedrock access
- AWS CLI configured (`aws configure`)

### Environment Setup

Set up a single virtual environment at the project root for all labs:

```bash
python -m venv .venv
source .venv/bin/activate
# Windows: .venv\Scripts\activate

pip install bedrock-agentcore-starter-toolkit
```

## Lab Start
You can use the quick start instructions below or open the intended lab for detailed deployment instructions. Each lab is independent of the other, so you can build in any order


### Lab 1: Deploy Basic Agent

See [Lab 1 README](01_base_agent/README.md) for detailed instructions

```bash
cd 01_base_agent

pip install -r requirements.txt

# Configure and deploy
agentcore configure \
  -e agent.py \
  -n langgraph_lab_agent \
  -r us-east-1 \
  --non-interactive

agentcore launch

# Test
agentcore invoke '{"prompt": "What is the weather in Seattle?"}'
```

### Lab 2: Add Features

See [Lab 2 README](02_features/README.md) for GuardRail, Memory and Knowledge Base creation steps

```bash
cd 02_features

# Create GuardRail, Memory and Knowledge Base first (see Lab 2 README)
# Then configure and deploy with features:

agentcore configure \
  -e agent.py \
  -n langgraph_features_agent \
  -r us-east-1 \
  --non-interactive

agentcore launch \
   --env BEDROCK_GUARDRAIL_ID=$GUARDRAIL_ID \
   --env BEDROCK_GUARDRAIL_VERSION=$GUARDRAIL_VERSION \
   --env BEDROCK_KNOWLEDGE_BASE_ID=$KNOWLEDGE_BASE_ID \
   --env BEDROCK_MEMORY_ID=$MEMORY_ID

# Test features
agentcore invoke '{"prompt": "What products do you offer?"}'
```

### Lab 3: Observability & Evaluation

See [Lab 3 README](03_evaluation_workflow/README.md) for detailed instructions

```bash
cd 03_evaluation_workflow

pip install -r requirements.txt

#configure and deploy with OpenTelemetry tracing
agentcore configure \
   -e agent.py \
   -n langgraph_eval_agent \
   -r us-east-1 \
   --non-interactive

agentcore launch

# Test the agent
agentcore invoke '{"prompt": "What is the weather in Seattle?"}'

# Create online evaluation config
agentcore eval online create \
   --name lab_eval_config \
   --sampling-rate 10.0 \
   --evaluator "Builtin.Helpfulness"
```


### Lab 4: Strands Agent with Working Evaluations

See [Lab 4 README](04_strands_evaluation/README.md) for detailed instructions

```bash
cd 04_strands_evaluation

# Configure and deploy Strands agent
agentcore configure \
   -e agent.py
   -n strands_eval_agent
   -r us-east-1
   --non-interactive

agentcore launch

# Test the agent
agentcore invoke '{"prompt": "What is the weather in Seattle?"}'

# Run evaluation
agentcore eval run --evaluator "Builtin.Helpfulness"

# Set up online evaluation
agentcore eval online create \
   --name lab_eval_config \
   --sampling-rate 10.0 \
   --evaluator "Builtin.Helpfulness"
```

## Local Development

Some labs can be run locally before deploying:

```bash
# Lab 1 - Run agent locally
cd 01_base_agent
python agent.py

# Lab 2 - Run with features (set env variables first)
cd 02_features
export BEDROCK_GUARDRAIL_ID=<GUARDRAIL_ID>
export BEDROCK_GUARDRAIL_VERSION=<GUARDRAIL_VERSION>
export BEDROCK_KNOWLEDGE_BASE_ID=<KNOWLEDGE_BASE_ID>
export BEDROCK_MEMORY_ID=<MEMORY_ID>

python agent.py
```

## Documentation
- [AWS Permissions Guide](AWS_PERMISSIONS.md)

## Resources 

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [AWS Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- [CloudWatch GenAI Observability](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-GenAI-Observability.html)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)


## Cleanup
After completing all labs:

```bash
# Delete Lab 1 agent
cd 01_base_agent
agentcore destroy --force

# Delete Lab 2 agent
cd ../02_features
agentcore destroy --force

# Delete Lab 3 agent
cd ../03_evaluation_workflow
agentcore destroy --force

# Delete Lab 4 agent
cd ../04_strands_evaluation
agentcore destroy --force

# Delete GuardRail
aws bedrock delete-guardrail --guardrail-identifier $GUARDRAIL_ID

# Delete Memory
agentcore memory delete $MEMORY_ID --region us-east-1 --wait

# Delete Knowledge Base (via console - includes vector store cleanup)

# Delete evaulation configs
agentcore eval online delete --name lab_eval_config
agentcore eval online delete --name strands_eval_config

# Delete Cloudwatch log groups (replace AGENT_ID with actual IDs)
aws logs describe-log-groups --log-group-name-prefix /aws/bedrock-agentcore/runtimes/ --query 'logGroups[].logGroupName' --output text

# aws logs delete-log-group --log-group-name /aws/bedrock-agentcore/runtimes/{AGENT_ID}-DEFAULT

# Delete S3 Bucket
aws s3 rb s3://langgraph-lab-kb-$(aws sts get-caller-identity --query Account --output text) --force
```
