# Lab 4: Strands Agent for Observability and Tracing

## Table of Contents

- [Prerequisites](#prerequisites)
- [Overview](#overview)
- [Part 1: Deploy Agent with Observability](#part-1-deploy-strands-agent)
- [Part 2: View Observability Dashboard](#part-2-view-observability-dashboard)
- [Part 3: Run On-Demand Evaluation](#part-3-run-on-demand-evaluation)
- [Part 4: Set Up Online Evaluation](#part-4-set-up-online-evaluation)
- [Cleanup](#cleanup)
- [Troubleshooting](#troubleshooting)
- [Resources](#additional-resources)

---

In this lab, you'll deploy a Strands agent with fully working evaluations: 
- **AgentCore Observability**: Automatic tracing, metrics, and CloudWatch dashboard
- **AgentCore Evaluations**: LLM-as-a-Judge for automated quality assessment

## Prerequisites

- **AWS Account** with Bedrock AgentCore access
- **AWS CLI** configured with credentials (`aws configure`)
- **Python 3.10+**
- **AgentCore Starter Toolkit** 

Navigate to this local directory
```bash
cd 04_strands_evaluation
pip install -r requirements.txt
```

---

## Overview

This lab uses Strands Agents instead of LangGraph

Strands Agents automatically produces spans with `strands.telemetry.tracer` scope, which the Evaluate API can parse to extract the agents responses


```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Strands Agent  │────▶│  CloudWatch      │────▶│  AgentCore          │
│  (deployed)     │     │  (Logs/Metrics)  │     │  Evaluations ✅     │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
        │                                                  │
        │ strands.telemetry.tracer                         ▼
        │ (fully supported)                       ┌─────────────────────┐
        └────────────────────────────────────────▶│  Actual Scores!     │
                                                  │  Helpfulness: 0.85  │
                                                  └─────────────────────┘
```



## Part 1: Deploy Strands Agent

### Step 1.1: Configure and Deploy

```bash
# Configure deployment
agentcore configure -e agent.py -n strands_eval_agent -r us-east-1 --non-interactive

# Build dependencies and deploy agent to AWS
agentcore launch
```

### Step 1.2: Generate Traffic

Run several queries to generate trace data:

```bash
agentcore invoke '{"prompt": "What is the weather in Seattle?"}'
agentcore invoke '{"prompt": "What is 15*7?"}'
agentcore invoke '{"prompt": "Hello, what can you help me with?"}'
```

---

## Part 2: View Observability Dashboard

### Step 2.1: Open GenAI Observability Dashboard

1. Open [CloudWatch GenAI Observability Dashboard](https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#gen-ai-observability/agent-core)
2. Select the **Bedrock AgentCore** tab
3. Find your agent (`strands_eval_agent`)

> **Note:** Observability data may take 2-5 minutes to appear after the first invocation

### Step 2.2: Explore the Dashboard

The dashboard provides three views

| View | Descripton |
|------|------------|
| **Agents View** | Lists all agents with runtime metrics |
| **Sessions View** | Shows all conversation sessions |
| **Traces View** | Detailed trace and span information |

Click on a trace to see:
- Execution timeline
- Tool invocations
- Model latency 
- Token usage

To view logs:
```bash
# Export the agent ID
export AGENT_ID=$(aws bedrock-agentcore-control list-agent-runtimes --region us-east-1 \
  --query "agentRuntimes[?agentRuntimeName=='langgraph_eval_agent'].agentRuntimeId" --output text)
echo $AGENT_ID

# View recent logs
aws logs tail /aws/bedrock-agentcore/runtimes/${AGENT_ID}-DEFAULT \
  --log-stream-name-prefix "$(date +%Y/%m/$d)/[runtime-logs" --since 1h --region us-east-1
```

---

## Part 3: Run On-Demand Evaluation

On-demand evaluation lets you assess agent quality for specific sessions using LLM-as-a-Judge

### Step 3.1: List Available Evaluators

```bash
agentcore eval evaluator list
```

You'll see built-in evaluators like:
- `Builtin.Helpfulness` - How useful is the response
- `Builtin.GoalSuccessRate` - Did the agent achieve the user's goal
- `Builtin.Correctness` - Is the response factually accurate

### Step 3.2: Run Evaluation

```bash
# Evaluate the most recent session (pulls session ID from .bedrock_agentcore.yaml)
agentcore eval run --evaluator "Builtin.Helpfulness"
```

Or run multiple evaluators

```bash
agentcore eval run \
  --evaluator "Builtin.Helpfulness" \
  --evaluator "Builtin.GoalSuccessRate" \
  --evaluator "Builtin.Correctness"
```

### Step 3.3: Save output

```bash
agentcore eval run \
  --evaluator "Builtin.Helpfulness" \
  --output results.json
```

This creates:
- `results.json` - Evaluation scores and explanations
- `results_input.json` - Input data used for evaluation

---

## Part 4: Set Up Online Evaluation

Online evaluation automatically samples live traffic and evaluates it continuously.

### Step 4.1: Create Online Evaluation Config

```bash
agentcore eval online create \
  --name strands_eval_config \
  --samplint-rate 10.0 \
  --evaluator "Builtin.Helpfulness" \
  --evaluator "Builtin.GoalSuccessRate" \
  --description "Lab 4 Strands evaluation config"
```

Parameters:
- `--sampling-rate`: Percentage of interactions to evaluate (0.01-100)
- `--evaluator`: Evaluator IDs (specify multiple times)

### Step 4.2: Verify Configuration

```bash
# List all configs
agentcore eval online list | grep strands_eval_config

# Export the config ID
export EVAL_CONFIG_ID=$(agentcore eval online list 2>/dev/null | grep -oE '[a-z_]+-[A-Za-z0-9]+' | head -1)
echo "Evaluation Config ID: $STRANDS_CONFIG_ID"

# Get details for the config
agentcore eval online get --config-id $STRANDS_CONFIG_ID
```

### Step 4.3: Generate Traffic for Evaluation

```bash
agentcore invoke '{"prompt": "What is the weather in Seattle?"}'
agentcore invoke '{"prompt": "What is 15*7?"}'
agentcore invoke '{"prompt": "Hello, what can you help me with?"}'
```

### Step 4.4: View Evaluation Results

1. Open [CloudWatch GenAI Observability Dashboard](https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#gen-ai-observability/agent-core)
2. Select your agent
3. Click the **Evaluations** tab

You'll see:
- Helpfulness scores over time
- Goal success rates
- Response quality trends

For a list of all built in evaluators, see: [Bedrock Evaluators](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/prompt-templates-builtin.html)


**Evaluator Levels**
- **TRACE**: Evaluates individual responses
- **SESSION**: Evaluates entire conversations
- **TOOL_CALL**: Evaluates tool selection and parameters

---



## Cleanup

Remove all AWS resources created by this deployment:

```bash
agentcore destroy --force

# Delete Cloudwatch log groups
for log_group in $(aws logs describe-log-groups --log-group-name-prefix /aws/bedrock-agentcore/runtimes/ --query 'logGroups[].logGroupName' --output text); do
  echo "Deleting $log_group"
  aws logs delete-log-group --log-group-name "$log_group"
done

agentcore eval online delete --config-id $STRANDS_CONFIG_ID
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

**No spans found for session**
- Wait 2-5 minutes after invocation for CloudWatch logs to populate
- Run a new invocation to generate fresh session data


## Additional Resources

- [Strands Agents Documentation](https://strandsagents.com/)
- [AgentCore Observability Guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability.html)
- [AgentCore Evaluations Guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/evaluations.html)
- [AgentCore Evaluators Guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/evaluators.html)
