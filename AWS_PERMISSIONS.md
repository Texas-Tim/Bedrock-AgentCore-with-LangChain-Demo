# AWS IAM Permissions Guide

This document provides detailed IAM permission requirements for using AWS Bedrock AgentCore features in this demo project.

**AWS Documentation References:**
- [IAM Permissions for AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html)
- [AgentCore Evaluations Prerequisites](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/evaluations-prerequisites.html)
- [BedrockAgentCoreFullAccess Managed Policy](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/BedrockAgentCoreFullAccess.html)

## Table of Contents

- [Quick Start: Permissions by Lab](#quick-start-permissions-by-lab)
- [AWS Managed Policy](#aws-managed-policy)
- [Basic Bedrock Permissions](#basic-bedrock-permissions)
- [GuardRails Permissions](#guardrails-permissions)
- [Knowledge Base Permissions](#knowledge-base-permissions)
- [Memory Permissions](#memory-permissions)
- [Observability Permissions (Lab 3 & 4)](#observability-permissions-lab-3--4)
- [Complete IAM Policy](#complete-iam-policy)
- [Deployment Permissions](#deployment-permissions)
- [Troubleshooting Permissions](#troubleshooting-permissions)

---

## Quick Start: Permissions by Lab

Each lab requires different permissions. Use this table to identify what you need:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         PERMISSIONS BY LAB                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Lab 1: Base Agent                                                                │
│   ├── bedrock:InvokeModel                    (LLM calls)                        │
│   ├── bedrock:InvokeModelWithResponseStream  (Streaming)                        │
│   └── [Deployment permissions if deploying]                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Lab 2: Features (GuardRails, Knowledge Base, Memory)                             │
│   ├── All Lab 1 permissions                                                      │
│   ├── bedrock:ApplyGuardrail                 (Content filtering)                │
│   ├── bedrock:GetGuardrail                   (GuardRail config)                 │
│   ├── bedrock:Retrieve                       (Knowledge Base RAG)               │
│   ├── bedrock-agent-runtime:GetMemory        (Conversation state)               │
│   └── bedrock-agent-runtime:PutMemory        (Save state)                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Lab 3: Evaluation Workflow (LangGraph + OpenTelemetry Tracing)                   │
│   ├── All Lab 1 permissions                                                      │
│   ├── logs:CreateLogGroup                    (CloudWatch log groups)            │
│   ├── logs:CreateLogStream                   (CloudWatch log streams)           │
│   ├── logs:PutLogEvents                      (Write traces)                     │
│   ├── logs:DescribeLogGroups                 (List log groups)                  │
│   ├── xray:PutTraceSegments                  (X-Ray traces)                     │
│   ├── xray:PutTelemetryRecords               (X-Ray telemetry)                  │
│   ├── bedrock-agentcore:CreateOnlineEvaluationConfig  (Evaluation setup)        │
│   ├── bedrock-agentcore:GetOnlineEvaluationConfig     (Evaluation status)       │
│   └── bedrock-agentcore:Evaluate             (Run evaluations)                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Lab 4: Strands Agent with Working Evaluations                                    │
│   ├── All Lab 3 permissions                                                      │
│   └── (Same observability/evaluation permissions - Strands uses same APIs)      │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## AWS Managed Policy

For quick setup, AWS provides the `BedrockAgentCoreFullAccess` managed policy that grants broad permissions for all AgentCore capabilities.

**ARN:** `arn:aws:iam::aws:policy/BedrockAgentCoreFullAccess`

### Attach via Console

1. Go to [IAM Console > Users](https://console.aws.amazon.com/iam/home#/users) or [Roles](https://console.aws.amazon.com/iam/home#/roles)
2. Select your user/role
3. Click **"Add permissions"** → **"Attach policies"**
4. Search for `BedrockAgentCoreFullAccess`
5. Select and attach

### Attach via CLI

```bash
# For IAM User
aws iam attach-user-policy \
  --user-name your-username \
  --policy-arn arn:aws:iam::aws:policy/BedrockAgentCoreFullAccess

# For IAM Role
aws iam attach-role-policy \
  --role-name your-role-name \
  --policy-arn arn:aws:iam::aws:policy/BedrockAgentCoreFullAccess
```

> **Note:** This managed policy grants broad permissions. For production, create custom policies following least-privilege principles.

---

## Basic Bedrock Permissions

These permissions are required for all agents using AWS Bedrock LLMs (all labs).

### Required Actions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockBasicAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/*"
      ]
    }
  ]
}
```

### Explanation

- **`bedrock:InvokeModel`**: Required for non-streaming LLM invocations
- **`bedrock:InvokeModelWithResponseStream`**: Required for streaming LLM responses
- **Resource**: `foundation-model/*` allows access to all Bedrock foundation models

### Least Privilege Alternative

To restrict to specific models only:

```json
{
  "Resource": [
    "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-*",
    "arn:aws:bedrock:us-east-1::foundation-model/us.anthropic.claude-*"
  ]
}
```

---

## GuardRails Permissions

These permissions are required when using GuardRails for content filtering (Lab 2).

### Required Actions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "GuardRailsAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:ApplyGuardrail",
        "bedrock:GetGuardrail"
      ],
      "Resource": [
        "arn:aws:bedrock:*:*:guardrail/*"
      ]
    }
  ]
}
```

### Explanation

- **`bedrock:ApplyGuardrail`**: Required to apply GuardRails to LLM requests
- **`bedrock:GetGuardrail`**: Required to retrieve GuardRail configuration
- **Resource**: `guardrail/*` allows access to all GuardRails in your account

### Least Privilege Alternative

To restrict to specific GuardRails:

```json
{
  "Resource": [
    "arn:aws:bedrock:us-east-1:123456789012:guardrail/gr-abc123xyz"
  ]
}
```

### Creating GuardRails (Console Management)

To create and manage GuardRails in the AWS Console, you also need:

```json
{
  "Action": [
    "bedrock:CreateGuardrail",
    "bedrock:UpdateGuardrail",
    "bedrock:DeleteGuardrail",
    "bedrock:ListGuardrails"
  ],
  "Resource": "*"
}
```

---

## Knowledge Base Permissions

These permissions are required when using Knowledge Bases for RAG (Lab 2).

### Required Actions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "KnowledgeBaseAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:Retrieve"
      ],
      "Resource": [
        "arn:aws:bedrock:*:*:knowledge-base/*"
      ]
    }
  ]
}
```

### Explanation

- **`bedrock:Retrieve`**: Required to query Knowledge Bases and retrieve documents
- **Resource**: `knowledge-base/*` allows access to all Knowledge Bases in your account

### Least Privilege Alternative

To restrict to specific Knowledge Bases:

```json
{
  "Resource": [
    "arn:aws:bedrock:us-east-1:123456789012:knowledge-base/KB123ABC"
  ]
}
```

### Creating Knowledge Bases (Console Management)

To create and manage Knowledge Bases in the AWS Console, you need additional permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "KnowledgeBaseManagement",
      "Effect": "Allow",
      "Action": [
        "bedrock:CreateKnowledgeBase",
        "bedrock:UpdateKnowledgeBase",
        "bedrock:DeleteKnowledgeBase",
        "bedrock:ListKnowledgeBases",
        "bedrock:GetKnowledgeBase",
        "bedrock:CreateDataSource",
        "bedrock:UpdateDataSource",
        "bedrock:DeleteDataSource",
        "bedrock:ListDataSources",
        "bedrock:GetDataSource",
        "bedrock:StartIngestionJob",
        "bedrock:ListIngestionJobs"
      ],
      "Resource": "*"
    },
    {
      "Sid": "S3AccessForKnowledgeBase",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-knowledge-base-docs",
        "arn:aws:s3:::my-knowledge-base-docs/*"
      ]
    },
    {
      "Sid": "OpenSearchAccessForKnowledgeBase",
      "Effect": "Allow",
      "Action": [
        "aoss:APIAccessAll"
      ],
      "Resource": [
        "arn:aws:aoss:*:*:collection/*"
      ]
    }
  ]
}
```

---

## Memory Permissions

These permissions are required when using Memory for conversation persistence (Lab 2).

### Required Actions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "MemoryAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock-agent-runtime:GetMemory",
        "bedrock-agent-runtime:PutMemory"
      ],
      "Resource": [
        "arn:aws:bedrock:*:*:memory/*"
      ]
    }
  ]
}
```

### Explanation

- **`bedrock-agent-runtime:GetMemory`**: Required to retrieve conversation state
- **`bedrock-agent-runtime:PutMemory`**: Required to save conversation state
- **Resource**: `memory/*` allows access to all Memory resources in your account

### Least Privilege Alternative

To restrict to specific Memory resources:

```json
{
  "Resource": [
    "arn:aws:bedrock:us-east-1:123456789012:memory/MEM123ABC"
  ]
}
```

### Creating Memory Resources (Console Management)

To create and manage Memory resources:

```json
{
  "Action": [
    "bedrock-agentcore:CreateMemory",
    "bedrock-agentcore:DeleteMemory",
    "bedrock-agentcore:ListMemories",
    "bedrock-agentcore:GetMemory"
  ],
  "Resource": "*"
}
```

---

## Observability Permissions (Lab 3 & 4)

Lab 3 and Lab 4 use OpenTelemetry (OTEL) to send traces to CloudWatch for AgentCore Online Evaluation. These permissions enable tracing and evaluation.

**AWS Documentation:**
- [AgentCore Observability](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-observability.html)
- [AgentCore Evaluations Prerequisites](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/evaluations-prerequisites.html)

### CloudWatch Logs Permissions (Tracing)

Required for OTEL to write traces to CloudWatch:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudWatchLogsForTracing",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams"
      ],
      "Resource": [
        "arn:aws:logs:*:*:log-group:/aws/bedrock-agentcore/*",
        "arn:aws:logs:*:*:log-group:/aws/bedrock-agentcore/*:log-stream:*"
      ]
    }
  ]
}
```

### X-Ray Permissions (Distributed Tracing)

Required for X-Ray trace segments:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "XRayTracing",
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords",
        "xray:GetSamplingRules",
        "xray:GetSamplingTargets"
      ],
      "Resource": "*"
    }
  ]
}
```

### Online Evaluation Permissions

Required to create and manage AgentCore Online Evaluations:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AgentCoreEvaluations",
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:CreateEvaluator",
        "bedrock-agentcore:GetEvaluator",
        "bedrock-agentcore:ListEvaluators",
        "bedrock-agentcore:UpdateEvaluator",
        "bedrock-agentcore:DeleteEvaluator",
        "bedrock-agentcore:CreateOnlineEvaluationConfig",
        "bedrock-agentcore:GetOnlineEvaluationConfig",
        "bedrock-agentcore:ListOnlineEvaluationConfigs",
        "bedrock-agentcore:UpdateOnlineEvaluationConfig",
        "bedrock-agentcore:DeleteOnlineEvaluationConfig",
        "bedrock-agentcore:Evaluate"
      ],
      "Resource": "*"
    },
    {
      "Sid": "PassRoleForEvaluation",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "arn:aws:iam::*:role/AgentCoreEvaluationRole*",
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": "bedrock-agentcore.amazonaws.com"
        }
      }
    },
    {
      "Sid": "CloudWatchIndexPolicy",
      "Effect": "Allow",
      "Action": [
        "logs:DescribeIndexPolicies",
        "logs:PutIndexPolicy"
      ],
      "Resource": "*"
    }
  ]
}
```

### Evaluation Execution Role

AgentCore Evaluations requires a service execution role. The role needs this trust policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "TrustPolicyStatement",
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock-agentcore.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "123456789012"
        },
        "ArnLike": {
          "aws:SourceArn": [
            "arn:aws:bedrock-agentcore:us-east-1:123456789012:evaluator/*",
            "arn:aws:bedrock-agentcore:us-east-1:123456789012:online-evaluation-config/*"
          ]
        }
      }
    }
  ]
}
```

And this permissions policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudWatchLogRead",
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogGroups",
        "logs:GetQueryResults",
        "logs:StartQuery"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchLogWrite",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/bedrock-agentcore/evaluations/*"
    },
    {
      "Sid": "BedrockInvoke",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/*",
        "arn:aws:bedrock:*:*:inference-profile/*"
      ]
    }
  ]
}
```

---

## Complete IAM Policy

This policy includes all permissions needed for the AgentCore demo with all features enabled (Labs 1-4).

### For Local Development

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockLLMAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/*"
      ]
    },
    {
      "Sid": "GuardRailsAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:ApplyGuardrail",
        "bedrock:GetGuardrail"
      ],
      "Resource": [
        "arn:aws:bedrock:*:*:guardrail/*"
      ]
    },
    {
      "Sid": "KnowledgeBaseAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:Retrieve"
      ],
      "Resource": [
        "arn:aws:bedrock:*:*:knowledge-base/*"
      ]
    },
    {
      "Sid": "MemoryAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock-agent-runtime:GetMemory",
        "bedrock-agent-runtime:PutMemory"
      ],
      "Resource": [
        "arn:aws:bedrock:*:*:memory/*"
      ]
    },
    {
      "Sid": "CloudWatchLogsForTracing",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams"
      ],
      "Resource": [
        "arn:aws:logs:*:*:log-group:/aws/bedrock-agentcore/*",
        "arn:aws:logs:*:*:log-group:/aws/bedrock-agentcore/*:log-stream:*"
      ]
    },
    {
      "Sid": "XRayTracing",
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords",
        "xray:GetSamplingRules",
        "xray:GetSamplingTargets"
      ],
      "Resource": "*"
    }
  ]
}
```

### Attaching the Policy

**Option 1: Attach to IAM User**

1. Go to [IAM Console > Users](https://console.aws.amazon.com/iam/home#/users)
2. Select your user
3. Click **"Add permissions"** → **"Create inline policy"**
4. Paste the JSON policy above
5. Name it `BedrockAgentCoreLabsPolicy`
6. Click **"Create policy"**

**Option 2: Create Managed Policy via CLI**

```bash
# Save policy to file
cat > bedrock-agentcore-labs-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    ... paste policy here ...
  ]
}
EOF

# Create managed policy
aws iam create-policy \
  --policy-name BedrockAgentCoreLabsPolicy \
  --policy-document file://bedrock-agentcore-labs-policy.json

# Attach to user
aws iam attach-user-policy \
  --user-name your-username \
  --policy-arn arn:aws:iam::123456789012:policy/BedrockAgentCoreLabsPolicy
```

---

## Deployment Permissions

Additional permissions required for deploying agents to AWS Bedrock AgentCore Runtime using the starter toolkit (CLI).

**AWS Documentation:** [IAM Permissions for AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html)

### Starter Toolkit Permissions

These permissions allow the `agentcore` CLI to build and deploy your agent:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "IAMRoleManagement",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:GetRole",
        "iam:PutRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:TagRole",
        "iam:ListRolePolicies",
        "iam:ListAttachedRolePolicies"
      ],
      "Resource": [
        "arn:aws:iam::*:role/*BedrockAgentCore*",
        "arn:aws:iam::*:role/service-role/*BedrockAgentCore*"
      ]
    },
    {
      "Sid": "CodeBuildProjectAccess",
      "Effect": "Allow",
      "Action": [
        "codebuild:StartBuild",
        "codebuild:BatchGetBuilds",
        "codebuild:ListBuildsForProject",
        "codebuild:CreateProject",
        "codebuild:UpdateProject",
        "codebuild:BatchGetProjects"
      ],
      "Resource": [
        "arn:aws:codebuild:*:*:project/bedrock-agentcore-*",
        "arn:aws:codebuild:*:*:build/bedrock-agentcore-*"
      ]
    },
    {
      "Sid": "CodeBuildListAccess",
      "Effect": "Allow",
      "Action": [
        "codebuild:ListProjects"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IAMPassRoleAccess",
      "Effect": "Allow",
      "Action": [
        "iam:PassRole"
      ],
      "Resource": [
        "arn:aws:iam::*:role/AmazonBedrockAgentCore*",
        "arn:aws:iam::*:role/service-role/AmazonBedrockAgentCore*"
      ]
    },
    {
      "Sid": "CloudWatchLogsAccess",
      "Effect": "Allow",
      "Action": [
        "logs:GetLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams"
      ],
      "Resource": [
        "arn:aws:logs:*:*:log-group:/aws/bedrock-agentcore/*",
        "arn:aws:logs:*:*:log-group:/aws/codebuild/*"
      ]
    },
    {
      "Sid": "S3Access",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket",
        "s3:CreateBucket",
        "s3:PutLifecycleConfiguration"
      ],
      "Resource": [
        "arn:aws:s3:::bedrock-agentcore-*",
        "arn:aws:s3:::bedrock-agentcore-*/*"
      ]
    },
    {
      "Sid": "ECRRepositoryAccess",
      "Effect": "Allow",
      "Action": [
        "ecr:CreateRepository",
        "ecr:DescribeRepositories",
        "ecr:GetRepositoryPolicy",
        "ecr:InitiateLayerUpload",
        "ecr:CompleteLayerUpload",
        "ecr:PutImage",
        "ecr:UploadLayerPart",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:ListImages",
        "ecr:TagResource"
      ],
      "Resource": [
        "arn:aws:ecr:*:*:repository/bedrock-agentcore-*"
      ]
    },
    {
      "Sid": "ECRAuthorizationAccess",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AgentCoreAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:*"
      ],
      "Resource": "*"
    }
  ]
}
```

> **Note:** These permissions are designed for development and testing. For production, create custom policies following least-privilege principles.


### Execution Role for Deployed Agents

When agents are deployed, they run with an IAM execution role. This role needs permissions to:
- Invoke Bedrock models
- Write logs to CloudWatch
- Send traces to X-Ray
- Access ECR for container images

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockModelInvocation",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/*",
        "arn:aws:bedrock:us-east-1:123456789012:*"
      ]
    },
    {
      "Sid": "BedrockFeatures",
      "Effect": "Allow",
      "Action": [
        "bedrock:ApplyGuardrail",
        "bedrock:GetGuardrail",
        "bedrock:Retrieve",
        "bedrock-agent-runtime:GetMemory",
        "bedrock-agent-runtime:PutMemory"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:DescribeLogStreams"
      ],
      "Resource": [
        "arn:aws:logs:us-east-1:123456789012:log-group:/aws/bedrock-agentcore/runtimes/*"
      ]
    },
    {
      "Sid": "CloudWatchLogStreams",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": [
        "arn:aws:logs:us-east-1:123456789012:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*"
      ]
    },
    {
      "Sid": "CloudWatchLogGroupsDescribe",
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogGroups"
      ],
      "Resource": [
        "arn:aws:logs:us-east-1:123456789012:log-group:*"
      ]
    },
    {
      "Sid": "XRayTracing",
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords",
        "xray:GetSamplingRules",
        "xray:GetSamplingTargets"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchMetrics",
      "Effect": "Allow",
      "Action": "cloudwatch:PutMetricData",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "cloudwatch:namespace": "bedrock-agentcore"
        }
      }
    },
    {
      "Sid": "ECRImageAccess",
      "Effect": "Allow",
      "Action": [
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer"
      ],
      "Resource": [
        "arn:aws:ecr:us-east-1:123456789012:repository/*"
      ]
    },
    {
      "Sid": "ECRTokenAccess",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken"
      ],
      "Resource": "*"
    }
  ]
}
```

### Execution Role Trust Policy

The execution role must trust the AgentCore service:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AssumeRolePolicy",
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock-agentcore.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "123456789012"
        },
        "ArnLike": {
          "aws:SourceArn": "arn:aws:bedrock-agentcore:us-east-1:123456789012:*"
        }
      }
    }
  ]
}
```

> **Tip:** The AgentCore CLI can automatically create this role with `execution_role_auto_create: true` in `.bedrock_agentcore.yaml`.

---

## Troubleshooting Permissions

### Common Permission Errors

#### Error: "User is not authorized to perform: bedrock:InvokeModel"

**Cause**: Missing basic Bedrock permissions

**Solution**: Add `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` to your IAM policy

#### Error: "User is not authorized to perform: bedrock:ApplyGuardrail"

**Cause**: Missing GuardRails permissions

**Solution**: Add `bedrock:ApplyGuardrail` to your IAM policy

#### Error: "User is not authorized to perform: bedrock:Retrieve"

**Cause**: Missing Knowledge Base permissions

**Solution**: Add `bedrock:Retrieve` to your IAM policy

#### Error: "User is not authorized to perform: bedrock-agent-runtime:GetMemory"

**Cause**: Missing Memory permissions

**Solution**: Add `bedrock-agent-runtime:GetMemory` and `bedrock-agent-runtime:PutMemory` to your IAM policy

#### Error: "User is not authorized to perform: logs:CreateLogGroup"

**Cause**: Missing CloudWatch Logs permissions (Lab 3/4 tracing)

**Solution**: Add CloudWatch Logs permissions for the `/aws/bedrock-agentcore/*` log group pattern

#### Error: "Access denied to model"

**Cause**: Model access not enabled in Bedrock Console

**Solution**: 
1. Go to [Bedrock Console > Model Access](https://console.aws.amazon.com/bedrock)
2. Click **"Manage model access"**
3. Enable access to Claude Sonnet 4
4. Wait a few minutes for access to propagate

#### Error: "Resource not found" for GuardRail/Knowledge Base/Memory

**Cause**: Either the resource doesn't exist, or you don't have permission to access it

**Solution**:
1. Verify the resource ID is correct
2. Check the resource exists in the correct region
3. Verify your IAM policy includes the resource ARN
4. Check resource-based policies (if any)


### Verifying Permissions

Use the AWS CLI to test specific permissions:

```bash
# Test Bedrock model access
aws bedrock invoke-model \
  --model-id anthropic.claude-sonnet-4-20250514-v1:0 \
  --body '{"prompt":"Hello","max_tokens":10}' \
  --region us-east-1 \
  output.txt

# Test GuardRails access
aws bedrock get-guardrail \
  --guardrail-identifier gr-abc123xyz \
  --region us-east-1

# Test Knowledge Base access
aws bedrock-agent-runtime retrieve \
  --knowledge-base-id KB123ABC \
  --retrieval-query text="test query" \
  --region us-east-1

# Test Memory access
aws bedrock-agent-runtime get-memory \
  --memory-id MEM123ABC \
  --region us-east-1

# Test CloudWatch Logs access (Lab 3/4)
aws logs describe-log-groups \
  --log-group-name-prefix /aws/bedrock-agentcore/ \
  --region us-east-1
```

### IAM Policy Simulator

Use the [IAM Policy Simulator](https://policysim.aws.amazon.com/) to test permissions without making actual API calls:

1. Select your IAM user or role
2. Select the service (e.g., "Bedrock")
3. Select the action (e.g., "InvokeModel")
4. Click **"Run Simulation"**
5. Review the results

### CloudTrail for Permission Debugging

Enable CloudTrail to see detailed permission denial logs:

1. Go to [CloudTrail Console](https://console.aws.amazon.com/cloudtrail)
2. Create a trail if you don't have one
3. Look for `AccessDenied` events
4. Review the event details to see which permission was denied

---

## Best Practices

### 1. Principle of Least Privilege

Grant only the permissions needed for your use case:

```json
{
  "Resource": [
    "arn:aws:bedrock:us-east-1:123456789012:guardrail/gr-abc123xyz",
    "arn:aws:bedrock:us-east-1:123456789012:knowledge-base/KB123ABC",
    "arn:aws:bedrock:us-east-1:123456789012:memory/MEM123ABC"
  ]
}
```

### 2. Use IAM Roles for Deployed Agents

Never hardcode AWS credentials. Use IAM roles:
- **Local development**: Use IAM user credentials via `aws configure`
- **Deployed agents**: Use IAM execution roles (automatic with AgentCore)

### 3. Separate Development and Production

Use different IAM policies for development and production:
- **Development**: Broader permissions for testing
- **Production**: Strict least-privilege permissions

### 4. Regular Permission Audits

Periodically review and remove unused permissions:
- Use AWS Access Analyzer
- Review CloudTrail logs for unused permissions
- Remove permissions that haven't been used in 90+ days

### 5. Use Permission Boundaries

For multi-user environments, use permission boundaries to limit maximum permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:*",
        "bedrock-agent-runtime:*",
        "bedrock-agentcore:*"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Additional Resources

- [AWS Bedrock IAM Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/security-iam.html)
- [AgentCore Runtime Permissions](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html)
- [AgentCore Evaluations Prerequisites](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/evaluations-prerequisites.html)
- [BedrockAgentCoreFullAccess Policy](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/BedrockAgentCoreFullAccess.html)
- [IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [AWS Policy Generator](https://awspolicygen.s3.amazonaws.com/policygen.html)
- [IAM Policy Simulator](https://policysim.aws.amazon.com/)

---

**Need Help?** If you're still experiencing permission issues, check CloudWatch Logs for detailed error messages or open an AWS Support case.
