# Lab 5: File sharing between AgentCore agents

This lab answers one question: **how do two AgentCore agents share files?**

It runs three independent experiments that each test a different approach. Run them in order — experiment 01 establishes *why* the obvious approaches (FUSE / NFS) don't work, and experiments 02 and 03 are the two viable alternatives.

## The three experiments

| # | Directory | Approach | What it proves |
|---|---|---|---|
| 01 | [`01_capability_probe/`](01_capability_probe/) | Try to `mount` inside the microVM | That you *can't* — no `/dev/fuse`, no `CAP_SYS_ADMIN`, mount syscall blocked |
| 02 | [`02_s3_shared_bucket/`](02_s3_shared_bucket/) | Two agents share one S3 bucket via boto3 | Standard pattern — always works, minimal infra |
| 03 | [`03_session_storage_shared/`](03_session_storage_shared/) | Two agents point at same `filesystemConfigurations.sessionStorage` mount | Whether AgentCore-managed session storage is shareable across runtimes (likely scoped per-session) |

## Run order

```bash
# Experiment 01 — ~3 min, single agent, no VPC
cd 01_capability_probe && # follow README.md

# Experiment 02 — ~10 min, two agents + S3, no VPC
cd 02_s3_shared_bucket && # follow README.md

# Experiment 03 — ~20 min, two agents in VPC, NAT gateway (~$0.05/hr while it sits)
cd 03_session_storage_shared && # follow README.md
```

You can run any experiment standalone — they share no infrastructure.

## Comparison: when to use each

| Dimension | Experiment 02 (S3) | Experiment 03 (session storage) |
|---|---|---|
| **Cross-agent sharing** | Yes, full sharing | No (expected — per-session) |
| **Cross-region / cross-account** | Yes | No |
| **Requires VPC** | No | Yes |
| **Infra cost at rest** | ~$0 (empty bucket) | ~$32/mo (NAT gateway + endpoints) |
| **Per-operation latency** | ~10-50 ms (S3 API) | ~1-5 ms (local FS) |
| **POSIX semantics** | No | Yes |
| **Max object size** | 5 TB | Session-storage quota (AWS docs) |
| **Durability across sessions** | Durable | Session-scoped (likely wiped) |
| **Deploy complexity** | `agentcore launch --env` | `agentcore launch` + `update-agent-runtime` |

**Short version:** use experiment 02's pattern for anything that needs to be shared between agents, between sessions, or survive beyond a session. Use experiment 03's pattern only for scratch space *within* a single agent session.

## Results template

After running the experiments, fill this in:

```
Experiment 01 — microVM capability probe
  /dev/fuse exists:         [ ]
  CAP_SYS_ADMIN granted:    [ ]
  mount --bind succeeded:   [ ]
  mount-s3 binary works:    [ ]
  mount.nfs4 binary works:  [ ]

Experiment 02 — S3 shared bucket
  Writer wrote file:        [ ]
  Reader read same file:    [ ]
  Cross-agent sharing:      [ ]

Experiment 03 — session-storage sharing
  Case A (same runtime, same session):          HIT / MISS
  Case B (same runtime, different sessions):    HIT / MISS
  Case C (different runtimes, same session ID): HIT / MISS
  Case D (different runtimes, different sess.): HIT / MISS
```

## Shared prerequisites

All three experiments need:

- AWS CLI v2 configured
- Docker
- `pip install bedrock-agentcore-starter-toolkit`
- Bedrock model access for `us.anthropic.claude-sonnet-4-5-20250929-v1:0` (experiments 02 and 03 only)

See [`../AWS_PERMISSIONS.md`](../AWS_PERMISSIONS.md) for IAM details.

## Documentation

- [AgentCore session storage](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-persistent-filesystems.html)
- [AgentCore VPC configuration](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-vpc.html)
- [S3 Mountpoint (why it can't be used here)](https://docs.aws.amazon.com/AmazonS3/latest/userguide/mountpoint.html)
- [EFS mounting (why it can't be used here)](https://docs.aws.amazon.com/efs/latest/ug/mounting-fs.html)
