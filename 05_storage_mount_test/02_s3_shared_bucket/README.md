# Experiment 02: Shared S3 bucket (two agents, boto3)

**Hypothesis:** two AgentCore runtimes can share files by both pointing at the same S3 bucket over plain boto3. No VPC, no FUSE, no NFS.

**Expected result:** works every time. This is the baseline pattern — the one you'd actually ship.

## Pros and cons

| Pros | Cons |
|---|---|
| No VPC required — each agent deploys with default networking | Not a real filesystem — no POSIX semantics, no in-place edits |
| Works across accounts, regions, and even non-AgentCore clients | Writer and reader coordinate via naming conventions, not locks |
| No cold-start penalty | Higher per-request latency than a mounted filesystem |
| Deploy with vanilla `agentcore launch --env` — no API patching | Every file op is a separate S3 API call |

## Files

| File | Role |
|---|---|
| `writer_agent.py` | Agent with `write_file` and `list_shared_files` tools |
| `reader_agent.py` | Agent with `list_shared_files` and `read_file` tools |
| `Dockerfile` | Shared image for both agents (lightweight — no mount tooling) |
| `requirements.txt` | LangGraph + boto3 |
| `infra.yaml` | S3 bucket + managed policy granting bucket access |

## Step 1: Deploy shared infra

```bash
cd 02_s3_shared_bucket
export REGION=us-east-1
export STACK_NAME=agentcore-shared-s3
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws cloudformation deploy \
  --template-file infra.yaml \
  --stack-name ${STACK_NAME} \
  --capabilities CAPABILITY_NAMED_IAM \
  --region ${REGION}

export SHARED_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name ${STACK_NAME} --region ${REGION} \
  --query 'Stacks[0].Outputs[?OutputKey==`S3Bucket`].OutputValue' --output text)

export S3_POLICY_ARN=$(aws cloudformation describe-stacks \
  --stack-name ${STACK_NAME} --region ${REGION} \
  --query 'Stacks[0].Outputs[?OutputKey==`S3AccessPolicyArn`].OutputValue' --output text)

echo "Bucket: ${SHARED_BUCKET}"
echo "Policy: ${S3_POLICY_ARN}"
```

## Step 2: Deploy the writer agent

```bash
agentcore configure \
  -e writer_agent.py \
  -n s3_writer_agent \
  -r ${REGION} \
  --non-interactive \
  --disable-memory

agentcore launch --env SHARED_S3_BUCKET=${SHARED_BUCKET}
```

Attach S3 permissions to the auto-created execution role:

```bash
export WRITER_ROLE_NAME=$(grep -A 20 "s3_writer_agent:" .bedrock_agentcore.yaml \
  | grep "execution_role:" | head -1 | awk -F'role/' '{print $2}')

aws iam attach-role-policy \
  --role-name "${WRITER_ROLE_NAME}" \
  --policy-arn "${S3_POLICY_ARN}"
```

## Step 3: Deploy the reader agent

```bash
agentcore configure \
  -e reader_agent.py \
  -n s3_reader_agent \
  -r ${REGION} \
  --non-interactive \
  --disable-memory

agentcore launch --env SHARED_S3_BUCKET=${SHARED_BUCKET}

export READER_ROLE_NAME=$(grep -A 20 "s3_reader_agent:" .bedrock_agentcore.yaml \
  | grep "execution_role:" | head -1 | awk -F'role/' '{print $2}')

aws iam attach-role-policy \
  --role-name "${READER_ROLE_NAME}" \
  --policy-arn "${S3_POLICY_ARN}"
```

## Step 4: Run the end-to-end test

Get both ARNs:

```bash
export WRITER_ARN=$(grep -A 30 "s3_writer_agent:" .bedrock_agentcore.yaml \
  | grep "agent_arn:" | head -1 | awk '{print $2}')
export READER_ARN=$(grep -A 30 "s3_reader_agent:" .bedrock_agentcore.yaml \
  | grep "agent_arn:" | head -1 | awk '{print $2}')
```

Writer creates a file:

```bash
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn "${WRITER_ARN}" \
  --runtime-session-id "s3-test-$(date +%s)" \
  --payload '"Write a file called greeting.txt containing the sentence: Hello from the writer agent."' \
  --region ${REGION} \
  /tmp/writer-response.txt

cat /tmp/writer-response.txt
```

Reader picks it up:

```bash
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn "${READER_ARN}" \
  --runtime-session-id "s3-test-$(date +%s)" \
  --payload '"List the shared files, then read greeting.txt and tell me what it says."' \
  --region ${REGION} \
  /tmp/reader-response.txt

cat /tmp/reader-response.txt
```

Confirm directly against S3:

```bash
aws s3 ls s3://${SHARED_BUCKET}/shared/
aws s3 cp s3://${SHARED_BUCKET}/shared/greeting.txt -
```

## Cleanup

```bash
# Delete both agent runtimes
agentcore destroy --agent s3_writer_agent --force
agentcore destroy --agent s3_reader_agent --force

# Empty bucket so the stack can delete it
aws s3 rm s3://${SHARED_BUCKET} --recursive

# Delete infra
aws cloudformation delete-stack --stack-name ${STACK_NAME} --region ${REGION}
aws cloudformation wait stack-delete-complete --stack-name ${STACK_NAME} --region ${REGION}

# Delete CloudWatch log groups
for lg in $(aws logs describe-log-groups \
  --log-group-name-prefix /aws/bedrock-agentcore/runtimes/s3_ \
  --query 'logGroups[].logGroupName' --output text --region ${REGION}); do
  aws logs delete-log-group --log-group-name "${lg}" --region ${REGION}
done
```
