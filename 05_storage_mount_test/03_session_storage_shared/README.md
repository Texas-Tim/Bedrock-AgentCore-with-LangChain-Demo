# Experiment 03: AgentCore session-storage sharing

**Hypothesis (what we actually want to learn):** does AgentCore's `filesystemConfigurations.sessionStorage` share data across (a) different sessions on the same runtime, and (b) different runtimes pointed at the same mount path?

AWS docs suggest session storage is scoped *per session*, but that's worth confirming in practice and across runtimes.

**Expected result:** mount works (unlike experiment 01's in-container mount attempts), BUT data is scoped per-(runtime, session). The other three cells of the test matrix should all show "empty directory".

## Test matrix

| Case | Writer runtime | Reader runtime | Session ID on both | Expectation |
|---|---|---|---|---|
| A | writer | writer | **same** | Reader sees file — same session |
| B | writer | writer | **different** | Reader sees empty — session isolation within the same runtime |
| C | writer | **reader** | **same** | Reader sees empty — different runtimes don't share session storage even with matching session IDs |
| D | writer | **reader** | **different** | Reader sees empty — baseline no-sharing case |

(Case A uses a single agent invoking its own reader-ish tool. The writer agent exposes a `list_files` tool of its own, so we can run case A by invoking the writer twice in the same session.)

## Pros and cons

| Pros | Cons |
|---|---|
| Looks like a real filesystem to the agent code — `open()` just works | Per-session scoping means it's useless for cross-agent handoffs |
| No S3 API cost per operation | Requires VPC mode (NAT gateway, interface endpoints — ~$30/mo just sitting there) |
| No external infrastructure to manage (AgentCore provisions the FS) | Two-step deploy: `agentcore launch` then `aws bedrock-agentcore-control update-agent-runtime` |
| Lower per-op latency inside a session | Data likely disappears when the session ends |

## Files

| File | Role |
|---|---|
| `writer_agent.py` | Writes files at `$MOUNT_PATH`; also has `list_files` so we can test intra-runtime sharing |
| `reader_agent.py` | Second AgentCore runtime with the same mount path |
| `Dockerfile` | Shared image |
| `infra.yaml` | VPC + NAT + endpoints (required for VPC-mode AgentCore) |

## Step 1: Deploy VPC infra

```bash
cd 03_session_storage_shared
export REGION=us-east-1
export STACK_NAME=agentcore-session-storage

aws cloudformation deploy \
  --template-file infra.yaml \
  --stack-name ${STACK_NAME} \
  --capabilities CAPABILITY_NAMED_IAM \
  --region ${REGION}

export SUBNET_1=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${REGION} \
  --query 'Stacks[0].Outputs[?OutputKey==`SubnetId1`].OutputValue' --output text)
export SUBNET_2=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${REGION} \
  --query 'Stacks[0].Outputs[?OutputKey==`SubnetId2`].OutputValue' --output text)
export AC_SG=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${REGION} \
  --query 'Stacks[0].Outputs[?OutputKey==`SecurityGroupId`].OutputValue' --output text)
```

## Step 2: Deploy writer agent

```bash
agentcore configure \
  -e writer_agent.py \
  -n session_writer_agent \
  -r ${REGION} \
  --vpc \
  --subnets ${SUBNET_1},${SUBNET_2} \
  --security-groups ${AC_SG} \
  --non-interactive \
  --disable-memory

agentcore launch --env MOUNT_PATH=/mnt/workspace

export WRITER_ID=$(grep -A 30 "session_writer_agent:" .bedrock_agentcore.yaml \
  | grep "agent_id:" | head -1 | awk '{print $2}')
export WRITER_ARN=$(grep -A 30 "session_writer_agent:" .bedrock_agentcore.yaml \
  | grep "agent_arn:" | head -1 | awk '{print $2}')
```

Attach session storage:

```bash
aws bedrock-agentcore-control update-agent-runtime \
  --agent-runtime-id "${WRITER_ID}" \
  --filesystem-configurations '[{"sessionStorage":{"mountPath":"/mnt/workspace"}}]' \
  --region ${REGION}

while true; do
  STATUS=$(aws bedrock-agentcore-control get-agent-runtime \
    --agent-runtime-id "${WRITER_ID}" --query 'status' --output text --region ${REGION})
  echo "Writer status: ${STATUS}"
  [ "${STATUS}" = "ACTIVE" ] && break
  sleep 5
done
```

## Step 3: Deploy reader agent

```bash
agentcore configure \
  -e reader_agent.py \
  -n session_reader_agent \
  -r ${REGION} \
  --vpc \
  --subnets ${SUBNET_1},${SUBNET_2} \
  --security-groups ${AC_SG} \
  --non-interactive \
  --disable-memory

agentcore launch --env MOUNT_PATH=/mnt/workspace

export READER_ID=$(grep -A 30 "session_reader_agent:" .bedrock_agentcore.yaml \
  | grep "agent_id:" | head -1 | awk '{print $2}')
export READER_ARN=$(grep -A 30 "session_reader_agent:" .bedrock_agentcore.yaml \
  | grep "agent_arn:" | head -1 | awk '{print $2}')

aws bedrock-agentcore-control update-agent-runtime \
  --agent-runtime-id "${READER_ID}" \
  --filesystem-configurations '[{"sessionStorage":{"mountPath":"/mnt/workspace"}}]' \
  --region ${REGION}

while true; do
  STATUS=$(aws bedrock-agentcore-control get-agent-runtime \
    --agent-runtime-id "${READER_ID}" --query 'status' --output text --region ${REGION})
  echo "Reader status: ${STATUS}"
  [ "${STATUS}" = "ACTIVE" ] && break
  sleep 5
done
```

## Step 4: Run the test matrix

### Case A — same runtime, same session (expect HIT)

```bash
SESSION_A="case-a-$(date +%s)"

aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn "${WRITER_ARN}" \
  --runtime-session-id "${SESSION_A}" \
  --payload '"Write a file called ping.txt containing the text HELLO-A, then tell me exactly what you wrote."' \
  --region ${REGION} /tmp/case-a-write.txt

aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn "${WRITER_ARN}" \
  --runtime-session-id "${SESSION_A}" \
  --payload '"List the files you can see at the mount path, and read ping.txt if it exists."' \
  --region ${REGION} /tmp/case-a-read.txt

echo "=== Case A (same writer, same session) ==="
cat /tmp/case-a-read.txt
```

### Case B — same runtime, different sessions (expect MISS)

```bash
SESSION_B1="case-b1-$(date +%s)"
SESSION_B2="case-b2-$(date +%s)"

aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn "${WRITER_ARN}" \
  --runtime-session-id "${SESSION_B1}" \
  --payload '"Write a file called ping.txt containing HELLO-B."' \
  --region ${REGION} /tmp/case-b-write.txt

aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn "${WRITER_ARN}" \
  --runtime-session-id "${SESSION_B2}" \
  --payload '"List the files you can see at the mount path, and read ping.txt if it exists."' \
  --region ${REGION} /tmp/case-b-read.txt

echo "=== Case B (same writer, different sessions) ==="
cat /tmp/case-b-read.txt
```

### Case C — different runtimes, same session ID (expect MISS)

```bash
SESSION_C="case-c-$(date +%s)"

aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn "${WRITER_ARN}" \
  --runtime-session-id "${SESSION_C}" \
  --payload '"Write a file called ping.txt containing HELLO-C."' \
  --region ${REGION} /tmp/case-c-write.txt

aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn "${READER_ARN}" \
  --runtime-session-id "${SESSION_C}" \
  --payload '"List the files you can see at the mount path, and read ping.txt if it exists."' \
  --region ${REGION} /tmp/case-c-read.txt

echo "=== Case C (different runtimes, same session ID) ==="
cat /tmp/case-c-read.txt
```

### Case D — different runtimes, different sessions (expect MISS)

```bash
SESSION_D1="case-d1-$(date +%s)"
SESSION_D2="case-d2-$(date +%s)"

aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn "${WRITER_ARN}" \
  --runtime-session-id "${SESSION_D1}" \
  --payload '"Write a file called ping.txt containing HELLO-D."' \
  --region ${REGION} /tmp/case-d-write.txt

aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn "${READER_ARN}" \
  --runtime-session-id "${SESSION_D2}" \
  --payload '"List the files you can see at the mount path, and read ping.txt if it exists."' \
  --region ${REGION} /tmp/case-d-read.txt

echo "=== Case D (different runtimes, different sessions) ==="
cat /tmp/case-d-read.txt
```

### Interpreting the results

Fill in your observed outcomes in the top-level README's comparison table. The usual result:

- Case A: reader sees `ping.txt` with `HELLO-A` → session storage works within a single session
- Cases B/C/D: reader sees empty directory → session storage is scoped per-session

If Case C returns a hit, that's genuinely surprising and worth documenting — it would mean the session-ID alone scopes storage across runtimes.

## Cleanup

```bash
agentcore destroy --agent session_writer_agent --force
agentcore destroy --agent session_reader_agent --force

# Delete CloudWatch log groups
for lg in $(aws logs describe-log-groups \
  --log-group-name-prefix /aws/bedrock-agentcore/runtimes/session_ \
  --query 'logGroups[].logGroupName' --output text --region ${REGION}); do
  aws logs delete-log-group --log-group-name "${lg}" --region ${REGION}
done

# Delete VPC stack (NAT + endpoints go here)
aws cloudformation delete-stack --stack-name ${STACK_NAME} --region ${REGION}
aws cloudformation wait stack-delete-complete --stack-name ${STACK_NAME} --region ${REGION}
```

## Documentation

- [AgentCore session storage](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-persistent-filesystems.html)
- [AgentCore VPC configuration](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-vpc.html)
- [Session storage blog post](https://aws.amazon.com/blogs/machine-learning/persist-session-state-with-filesystem-configuration-and-execute-shell-commands/)
