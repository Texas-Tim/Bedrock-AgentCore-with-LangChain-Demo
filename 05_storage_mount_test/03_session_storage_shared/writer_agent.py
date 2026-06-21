"""
Experiment 03 — Writer agent using AgentCore native sessionStorage.

AgentCore's `filesystemConfigurations.sessionStorage` attaches a filesystem at a
given mount path inside the microVM. This agent writes files into that path.
The reader agent (reader_agent.py), deployed as a separate runtime with the
SAME mountPath, will attempt to read them back.

Goal: determine whether sessionStorage is shared across (a) different sessions
on the same runtime and (b) different runtimes with matching mount paths.

Environment:
  MOUNT_PATH  — where sessionStorage is mounted (default: /mnt/workspace)
"""

import json
import logging
import os
import time
from typing import AsyncGenerator

from bedrock_agentcore.runtime import BedrockAgentCoreApp

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

REGION = "us-east-1"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
MOUNT_PATH = os.environ.get("MOUNT_PATH", "/mnt/workspace")

SYSTEM_PROMPT = f"""You are the WRITER agent in a session-storage experiment.
AgentCore has mounted a filesystem at {MOUNT_PATH}. When the user asks you to
share something, call write_file to put it there. Always confirm the full path
and the runtime session that wrote it so the operator can correlate."""

_agent = None


def _get_agent():
    global _agent
    if _agent is not None:
        return _agent

    from langchain_aws import ChatBedrock
    from langchain_core.tools import tool
    from langgraph.prebuilt import create_react_agent

    @tool
    def write_file(filename: str, content: str) -> str:
        """Write content to a file at MOUNT_PATH/filename on the session storage filesystem."""
        try:
            os.makedirs(MOUNT_PATH, exist_ok=True)
        except Exception as e:
            return f"ERROR: cannot create {MOUNT_PATH}: {type(e).__name__}: {e}"

        path = os.path.join(MOUNT_PATH, filename)
        try:
            with open(path, "w") as f:
                f.write(content)
            return (
                f"Wrote {len(content)} bytes to {path} at {time.time()}. "
                f"MOUNT_PATH={MOUNT_PATH}, hostname={os.uname().nodename}"
            )
        except Exception as e:
            return f"ERROR writing to {path}: {type(e).__name__}: {e}"

    @tool
    def list_files() -> str:
        """List all files currently at MOUNT_PATH."""
        try:
            if not os.path.exists(MOUNT_PATH):
                return f"{MOUNT_PATH} does not exist"
            entries = os.listdir(MOUNT_PATH)
            if not entries:
                return f"{MOUNT_PATH} is empty"
            details = []
            for e in sorted(entries):
                full = os.path.join(MOUNT_PATH, e)
                try:
                    st = os.stat(full)
                    details.append(f"{e} ({st.st_size} bytes, mtime={st.st_mtime})")
                except Exception as ex:
                    details.append(f"{e} (stat error: {ex})")
            return "\n".join(details)
        except Exception as e:
            return f"ERROR listing {MOUNT_PATH}: {type(e).__name__}: {e}"

    @tool
    def mount_info() -> str:
        """Report mount table entries for MOUNT_PATH — tells us what filesystem type sessionStorage is."""
        import subprocess

        try:
            r = subprocess.run(["mount"], capture_output=True, text=True, timeout=5)
            lines = [l for l in r.stdout.splitlines() if MOUNT_PATH in l or "workspace" in l]
            return "\n".join(lines) or f"No mount entry mentions {MOUNT_PATH}. Full table:\n{r.stdout}"
        except Exception as e:
            return f"mount error: {type(e).__name__}: {e}"

    llm = ChatBedrock(model_id=MODEL_ID, region_name=REGION, streaming=True)
    _agent = create_react_agent(llm, [write_file, list_files, mount_info], prompt=SYSTEM_PROMPT)
    return _agent


app = BedrockAgentCoreApp()


@app.entrypoint
async def handle_request(payload: dict, **kwargs) -> AsyncGenerator[str, None]:
    prompt = payload.get("prompt", "")
    if not prompt:
        yield json.dumps({"error": "No prompt provided"})
        return

    logger.info("Writer handling request: %s", prompt[:100])
    agent = _get_agent()
    input_data = {"messages": [{"role": "user", "content": prompt}]}

    try:
        async for event in agent.astream(input_data, stream_mode="messages"):
            if isinstance(event, tuple) and len(event) >= 2:
                chunk, metadata = event[0], event[1]
                if metadata.get("langgraph_node") != "agent":
                    continue
                content = getattr(chunk, "content", None)
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text = block.get("text", "")
                            if text:
                                yield text
                elif isinstance(content, str) and content:
                    yield content
    except Exception as e:
        logger.error("Writer error: %s", e, exc_info=True)
        yield json.dumps({"error": "An error occurred processing your request"})


if __name__ == "__main__":
    app.run()
