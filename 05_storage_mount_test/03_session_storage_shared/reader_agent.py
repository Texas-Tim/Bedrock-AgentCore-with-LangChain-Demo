"""
Experiment 03 — Reader agent using AgentCore native sessionStorage.

Separate AgentCore runtime from writer_agent.py, configured with the same
`filesystemConfigurations.sessionStorage` mountPath. Tries to read files the
writer claims to have placed there.

Environment:
  MOUNT_PATH  — where sessionStorage is mounted (default: /mnt/workspace)
"""

import json
import logging
import os
from typing import AsyncGenerator

from bedrock_agentcore.runtime import BedrockAgentCoreApp

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

REGION = "us-east-1"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
MOUNT_PATH = os.environ.get("MOUNT_PATH", "/mnt/workspace")

SYSTEM_PROMPT = f"""You are the READER agent in a session-storage experiment.
AgentCore has mounted a filesystem at {MOUNT_PATH}. List and read files you
find there. If the directory is empty, say so plainly — that's a valid result
for this experiment."""

_agent = None


def _get_agent():
    global _agent
    if _agent is not None:
        return _agent

    from langchain_aws import ChatBedrock
    from langchain_core.tools import tool
    from langgraph.prebuilt import create_react_agent

    @tool
    def list_files() -> str:
        """List all files at MOUNT_PATH."""
        try:
            if not os.path.exists(MOUNT_PATH):
                return f"{MOUNT_PATH} does not exist"
            entries = os.listdir(MOUNT_PATH)
            if not entries:
                return f"{MOUNT_PATH} is empty — writer's data not visible to this agent/session"
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
    def read_file(filename: str) -> str:
        """Read a file at MOUNT_PATH/filename."""
        path = os.path.join(MOUNT_PATH, filename)
        try:
            with open(path, "r") as f:
                content = f.read()
            return (
                f"Content ({len(content)} bytes) from {path} — "
                f"hostname={os.uname().nodename}:\n{content}"
            )
        except FileNotFoundError:
            return f"File not found: {path}"
        except Exception as e:
            return f"ERROR reading {path}: {type(e).__name__}: {e}"

    @tool
    def mount_info() -> str:
        """Report mount table entries for MOUNT_PATH."""
        import subprocess

        try:
            r = subprocess.run(["mount"], capture_output=True, text=True, timeout=5)
            lines = [l for l in r.stdout.splitlines() if MOUNT_PATH in l or "workspace" in l]
            return "\n".join(lines) or f"No mount entry mentions {MOUNT_PATH}. Full table:\n{r.stdout}"
        except Exception as e:
            return f"mount error: {type(e).__name__}: {e}"

    llm = ChatBedrock(model_id=MODEL_ID, region_name=REGION, streaming=True)
    _agent = create_react_agent(llm, [list_files, read_file, mount_info], prompt=SYSTEM_PROMPT)
    return _agent


app = BedrockAgentCoreApp()


@app.entrypoint
async def handle_request(payload: dict, **kwargs) -> AsyncGenerator[str, None]:
    prompt = payload.get("prompt", "")
    if not prompt:
        yield json.dumps({"error": "No prompt provided"})
        return

    logger.info("Reader handling request: %s", prompt[:100])
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
        logger.error("Reader error: %s", e, exc_info=True)
        yield json.dumps({"error": "An error occurred processing your request"})


if __name__ == "__main__":
    app.run()
