"""
Experiment 02 — Writer agent.

LangGraph agent with tools that write files to a shared S3 bucket. The reader
agent (reader_agent.py) reads from the same bucket. This is the "just use S3"
pattern — no VPC, no EFS, no FUSE — and it's the baseline that works.

Environment:
  SHARED_S3_BUCKET   — bucket name (required), set via `agentcore launch --env`
  SHARED_S3_PREFIX   — object key prefix (default: "shared/")
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

SHARED_S3_BUCKET = os.environ.get("SHARED_S3_BUCKET", "")
SHARED_S3_PREFIX = os.environ.get("SHARED_S3_PREFIX", "shared/")

SYSTEM_PROMPT = """You are the WRITER agent. You write files to a shared S3 bucket
so the READER agent (a different AgentCore runtime) can pick them up. When the user
asks you to share data, call write_file with a clear filename and the content."""

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
    def write_file(filename: str, content: str) -> str:
        """Write text content to a file in the shared S3 bucket so the reader agent can pick it up."""
        if not SHARED_S3_BUCKET:
            return "ERROR: SHARED_S3_BUCKET env var not set"
        key = f"{SHARED_S3_PREFIX.rstrip('/')}/{filename}"
        s3.put_object(
            Bucket=SHARED_S3_BUCKET,
            Key=key,
            Body=content.encode("utf-8"),
            ContentType="text/plain",
            Metadata={"written-by": "writer-agent", "written-at": str(time.time())},
        )
        return f"Wrote {len(content)} bytes to s3://{SHARED_S3_BUCKET}/{key}"

    @tool
    def list_shared_files() -> str:
        """List files currently in the shared S3 bucket."""
        if not SHARED_S3_BUCKET:
            return "ERROR: SHARED_S3_BUCKET env var not set"
        resp = s3.list_objects_v2(Bucket=SHARED_S3_BUCKET, Prefix=SHARED_S3_PREFIX, MaxKeys=50)
        objs = resp.get("Contents", [])
        if not objs:
            return "Bucket is empty"
        return "\n".join(f"{o['Key']} ({o['Size']} bytes, modified {o['LastModified']})" for o in objs)

    llm = ChatBedrock(model_id=MODEL_ID, region_name=REGION, streaming=True)
    _agent = create_react_agent(llm, [write_file, list_shared_files], prompt=SYSTEM_PROMPT)
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
