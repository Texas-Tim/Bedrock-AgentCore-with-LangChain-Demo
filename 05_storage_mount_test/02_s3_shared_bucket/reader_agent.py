"""
Experiment 02 — Reader agent.

LangGraph agent with tools that read files from a shared S3 bucket written by
writer_agent.py. Deployed as a separate AgentCore runtime.

Environment:
  SHARED_S3_BUCKET   — bucket name (required), set via `agentcore launch --env`
  SHARED_S3_PREFIX   — object key prefix (default: "shared/")
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

SHARED_S3_BUCKET = os.environ.get("SHARED_S3_BUCKET", "")
SHARED_S3_PREFIX = os.environ.get("SHARED_S3_PREFIX", "shared/")

SYSTEM_PROMPT = """You are the READER agent. You read files from a shared S3 bucket
that the WRITER agent (a different AgentCore runtime) has populated. When the user
asks what's available or asks for a file's contents, call list_shared_files or
read_file accordingly and summarize what you find."""

_agent = None


def _get_agent():
    global _agent
    if _agent is not None:
        return _agent

    import boto3
    from langchain_aws import ChatBedrock
    from langchain_core.tools import tool
    from langgraph.prebuilt import create_react_agent

    s3 = boto3.client("s3", region_name=REGION)

    @tool
    def list_shared_files() -> str:
        """List files available in the shared S3 bucket."""
        if not SHARED_S3_BUCKET:
            return "ERROR: SHARED_S3_BUCKET env var not set"
        resp = s3.list_objects_v2(Bucket=SHARED_S3_BUCKET, Prefix=SHARED_S3_PREFIX, MaxKeys=50)
        objs = resp.get("Contents", [])
        if not objs:
            return "Bucket is empty — writer hasn't written anything yet"
        return "\n".join(f"{o['Key']} ({o['Size']} bytes, modified {o['LastModified']})" for o in objs)

    @tool
    def read_file(filename: str) -> str:
        """Read the contents of a named file from the shared S3 bucket."""
        if not SHARED_S3_BUCKET:
            return "ERROR: SHARED_S3_BUCKET env var not set"
        key = f"{SHARED_S3_PREFIX.rstrip('/')}/{filename}"
        try:
            resp = s3.get_object(Bucket=SHARED_S3_BUCKET, Key=key)
            body = resp["Body"].read().decode("utf-8", errors="replace")
            meta = resp.get("Metadata", {})
            return f"Content ({len(body)} bytes, metadata={meta}):\n{body}"
        except s3.exceptions.NoSuchKey:
            return f"File not found: {key}"
        except Exception as e:
            return f"Read error: {type(e).__name__}: {e}"

    llm = ChatBedrock(model_id=MODEL_ID, region_name=REGION, streaming=True)
    _agent = create_react_agent(llm, [list_shared_files, read_file], prompt=SYSTEM_PROMPT)
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
