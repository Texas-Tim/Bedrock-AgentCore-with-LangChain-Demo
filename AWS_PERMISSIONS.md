# AWS IAM Permissions Guide

This document provides detailed IAM permission requirements for using AWS Bedrock Agents features in the AgentCore demo project.

## Table of Contents

- [Overview](#overview)
- [Basic Bedrock Permissions](#basic-bedrock-permissions)
- [GuardRails Permissions](#guardrails-permissions)
- [Knowledge Base Permissions](#knowledge-base-permissions)
- [Memory Permissions](#memory-permissions)
- [Complete IAM Policy](#complete-iam-policy)
- [Deployment Permissions](#deployment-permissions)
- [Troubleshooting Permissions](#troubleshooting-permissions)

## Overview

The AgentCore demo requires different IAM permissions depending on which features you use:

| Feature | Required Permissions |
|---------|---------------------|
| Basic Agent | `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream` |
| GuardRails | `bedrock:ApplyGuardrail`, `bedrock:GetGuardrail` |
| Knowledge Base | `bedrock:Retrieve` |
| Memory | `bedrock-agent-runtime:GetMemory`, `bedrock-agent-runtime:PutMemory` |
| Deployment | Additional permissions for ECR, CodeBuild, IAM, CloudWatch |

## Basic Bedrock Permissions

These permissions are required for all agents using AWS Bedrock LLMs.

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
    "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-*"
  ]
}
```

## GuardRails Permissions

These permissions are required when using GuardRails for content filtering.

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

### Creating GuardRails

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

## Knowledge Base Permissions

These permissions are required when using Knowledge Bases for RAG.

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

### Creating Knowledge Bases

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

## Memory Permissions

These permissions are required when using Memory for conversation persistence.

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

### Creating Memory Resources

To create and manage Memory resources in the AWS Console:

```json
{
  "Action": [
    "bedrock-agent-runtime:CreateMemory",
    "bedrock-agent-runtime:UpdateMemory",
    "bedrock-agent-runtime:DeleteMemory",
    "bedrock-agent-runtime:ListMemories"
  ],
  "Resource": "*"
}
```

## Complete IAM Policy

This policy includes all permissions needed for the AgentCore demo with all features enabled.

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
5. Name it `BedrockAgentCorePolicy`
6. Click **"Create policy"**

**Option 2: Attach to IAM Role**

1. Go to [IAM Console > Roles](https://console.aws.amazon.com/iam/home#/roles)
2. Select your role
3. Click **"Add permissions"** → **"Create inline policy"**
4. Paste the JSON policy above
5. Name it `BedrockAgentCorePolicy`
6. Click **"Create policy"**

**Option 3: Create Managed Policy**

```bash
# Save policy to file
cat > bedrock-agentcore-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    # ... paste policy here ...
  ]
}
EOF

# Create managed policy
aws iam create-policy \
  --policy-name BedrockAgentCorePolicy \
  --policy-document file://bedrock-agentcore-policy.json

# Attach to user
aws iam attach-user-policy \
  --user-name your-username \
  --policy-arn arn:aws:iam::123456789012:policy/BedrockAgentCorePolicy
```

## Deployment Permissions

Additional permissions required for deploying agents to AWS Bedrock AgentCore Runtime.

### Required Actions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRAccess",
      "Effect": "Allow",
      "Action": [
        "ecr:CreateRepository",
        "ecr:DescribeRepositories",
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CodeBuildAccess",
      "Effect": "Allow",
      "Action": [
        "codebuild:CreateProject",
        "codebuild:UpdateProject",
        "codebuild:DeleteProject",
        "codebuild:BatchGetProjects",
        "codebuild:StartBuild",
        "codebuild:BatchGetBuilds"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IAMAccess",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:GetRole",
        "iam:PassRole"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchAccess",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams"
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

### Execution Role for Deployed Agents

When agents are deployed, they run with an IAM execution role. This role needs the same Bedrock permissions as local development:

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
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

The AgentCore CLI can automatically create this role with `execution_role_auto_create: true` in `.bedrock_agentcore.yaml`.

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
        "bedrock-agent-runtime:*"
      ],
      "Resource": "*"
    }
  ]
}
```

## Additional Resources

- [AWS Bedrock IAM Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/security-iam.html)
- [IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [AWS Policy Generator](https://awspolicygen.s3.amazonaws.com/policygen.html)
- [IAM Policy Simulator](https://policysim.aws.amazon.com/)

---

**Need Help?** If you're still experiencing permission issues, check CloudWatch Logs for detailed error messages or open an AWS Support case.
