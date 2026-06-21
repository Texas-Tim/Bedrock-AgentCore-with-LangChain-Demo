# Experiment 01: AgentCore microVM capability probe

**Hypothesis:** the AgentCore microVM is locked down — no `/dev/fuse`, no `CAP_SYS_ADMIN`, `mount` syscall blocked — so FUSE (S3 Mountpoint) and NFS (EFS direct) mounts are impossible inside the container.

**Expected result:** every mount-related probe fails. This is the evidence we use to justify experiments 02 and 03.

## What this probe checks

| Check | What it tells us |
|---|---|
| `/dev/fuse` present | Whether FUSE filesystems can attach at all |
| `mount-s3 --version` | Whether the binary is installed (should be — it's in the image) |
| `mount.nfs4 -V` | Whether NFS client tools are present (should be) |
| `/proc/self/status` Cap* lines | Effective/permitted Linux capabilities — looking for `CAP_SYS_ADMIN` |
| `uid`/`gid` | Whether we're running as root or a restricted user |
| `uname -a`, `mount` | Kernel version and existing mount table |
| `mount --bind /tmp /tmp/_probe_bind` | **The deciding test** — does the mount syscall itself work, regardless of filesystem? |

No LLM, no VPC, no external infrastructure — just a diagnostic HTTP endpoint that returns one big JSON blob.

## Deploy

```bash
cd 01_capability_probe
export REGION=us-east-1

agentcore configure \
  -e agent.py \
  -n capability_probe \
  -r ${REGION} \
  --non-interactive \
  --disable-memory

agentcore launch
```

## Run the probes

```bash
agentcore invoke '{}'
```

Or via the API:

```bash
export AGENT_ARN=$(grep "agent_arn:" .bedrock_agentcore.yaml | awk '{print $2}')

aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn "${AGENT_ARN}" \
  --runtime-session-id "probe-$(date +%s)" \
  --payload '{}' \
  --region ${REGION} \
  /tmp/probe-result.json

cat /tmp/probe-result.json | jq .
```

## Interpreting the result

Look at these fields in the JSON:

- `devices.fuse_device_exists` — expect `false`
- `capabilities.CapEff` — decode with `capsh --decode=<hex>`; expect no `cap_sys_admin`
- `capabilities.uid` — expect non-zero (container runs as non-root)
- `mount_syscall.rc` — expect non-zero and a stderr like `operation not permitted`
- `binaries.mount-s3.rc` and `binaries.mount.nfs4.rc` — expect `0` (binaries work, but the mount call will still fail)

If `mount_syscall.verdict` is `"mount syscall FAILED"`, the hypothesis is confirmed: you cannot do FUSE or NFS mounts inside AgentCore, even with the right binaries installed. That is why experiment 02 uses boto3 and experiment 03 uses the native `filesystemConfigurations.sessionStorage` instead.

## Cleanup

```bash
agentcore destroy --force
```
