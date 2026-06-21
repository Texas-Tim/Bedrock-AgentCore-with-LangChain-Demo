"""
Experiment 01: AgentCore microVM capability probe.

Runs a set of diagnostic checks to confirm (or disprove) what the AgentCore
runtime allows inside its microVM. No LLM — this is a pure diagnostic harness
so cold starts are fast and results are unambiguous.

Checks:
  - /dev/fuse device node present
  - mount-s3 binary present and callable
  - mount.nfs4 binary present
  - Effective Linux capabilities (looking for CAP_SYS_ADMIN)
  - Process UID / GID
  - Kernel version and current mounts
  - Attempt a real mount syscall (bind mount of /tmp to /tmp/_probe) — this
    tells us whether any mount is allowed, regardless of filesystem type.
"""

import json
import logging
import os
import subprocess
from typing import AsyncGenerator

from bedrock_agentcore.runtime import BedrockAgentCoreApp

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()


def _run(cmd: list[str], timeout: int = 10) -> dict:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {"rc": r.returncode, "stdout": r.stdout.strip()[:500], "stderr": r.stderr.strip()[:500]}
    except FileNotFoundError:
        return {"rc": -1, "error": "binary not found"}
    except subprocess.TimeoutExpired:
        return {"rc": -1, "error": f"timed out after {timeout}s"}
    except Exception as e:
        return {"rc": -1, "error": f"{type(e).__name__}: {e}"}


def probe_devices() -> dict:
    try:
        entries = sorted(os.listdir("/dev"))
    except Exception as e:
        entries = [f"error: {e}"]
    return {
        "fuse_device_exists": os.path.exists("/dev/fuse"),
        "dev_entries_count": len(entries),
        "dev_entries_sample": entries[:40],
    }


def probe_binaries() -> dict:
    return {
        "mount-s3": _run(["mount-s3", "--version"]),
        "mount.nfs4": _run(["mount.nfs4", "-V"]),
        "mount": _run(["mount", "--version"]),
        "capsh": _run(["capsh", "--print"]),
    }


def probe_capabilities() -> dict:
    result = {"uid": os.getuid(), "gid": os.getgid()}
    try:
        with open("/proc/self/status", "r") as f:
            for line in f:
                if line.startswith("Cap"):
                    k, v = line.strip().split(":", 1)
                    result[k.strip()] = v.strip()
    except Exception as e:
        result["proc_status_error"] = str(e)
    return result


def probe_kernel_and_mounts() -> dict:
    uname = _run(["uname", "-a"])
    mounts = _run(["mount"])
    return {
        "uname": uname.get("stdout", uname.get("error", "")),
        "current_mounts": mounts.get("stdout", mounts.get("error", "")),
    }


def probe_mount_syscall() -> dict:
    """Attempt a harmless bind mount to see if the mount syscall is allowed at all."""
    target = "/tmp/_probe_bind"
    try:
        os.makedirs(target, exist_ok=True)
    except Exception as e:
        return {"attempted": False, "setup_error": str(e)}

    r = subprocess.run(
        ["mount", "--bind", "/tmp", target],
        capture_output=True,
        text=True,
        timeout=10,
    )
    result = {"attempted": True, "rc": r.returncode, "stderr": r.stderr.strip()[:500]}
    if r.returncode == 0:
        subprocess.run(["umount", target], capture_output=True)
        result["verdict"] = "mount syscall SUCCEEDED — microVM permits mounts"
    else:
        result["verdict"] = "mount syscall FAILED — microVM does not permit mounts (expected)"
    return result


def run_all_probes() -> dict:
    return {
        "devices": probe_devices(),
        "binaries": probe_binaries(),
        "capabilities": probe_capabilities(),
        "kernel_and_mounts": probe_kernel_and_mounts(),
        "mount_syscall": probe_mount_syscall(),
    }


@app.entrypoint
async def handle_request(payload: dict, **kwargs) -> AsyncGenerator[str, None]:
    """Runs all probes and returns results as JSON. Payload is ignored."""
    logger.info("Running microVM capability probes")
    try:
        results = run_all_probes()
        yield json.dumps(results, indent=2, default=str)
    except Exception as e:
        logger.error("Probe failed: %s", e, exc_info=True)
        yield json.dumps({"error": f"{type(e).__name__}: {e}"})


if __name__ == "__main__":
    app.run()
