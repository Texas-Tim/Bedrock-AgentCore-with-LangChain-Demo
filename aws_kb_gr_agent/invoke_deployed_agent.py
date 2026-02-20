"""
Invoke a deployed AgentCore Runtime agent using the AWS SDK.

This script supports all three Bedrock Agents features:
- GuardRails: Content filtering (automatic, no extra params needed)
- Knowledge Base: RAG queries (automatic via agent tools)
- Memory: Conversation persistence (via actor_id and thread_id)

Usage:
    # Basic invocation
    python invoke_deployed_agent.py "What is AcmeCorp?"
    
    # With memory (same thread for conversation continuity)
    python invoke_deployed_agent.py "My name is Alice" --thread-id my-session
    python invoke_deployed_agent.py "What is my name?" --thread-id my-session
    
    # Test Knowledge Base
    python invoke_deployed_agent.py "What products does AcmeCorp offer?"
    
    # Test GuardRails (try content that should be blocked)
    python invoke_deployed_agent.py "Give me financial advice on stocks"

Requires:
    - Agent deployed to AgentCore Runtime
    - AGENT_ARN environment variable or update the ARN below
    - AWS credentials with bedrock-agentcore:InvokeAgentRuntime permission
"""

import argparse
import json
import os
import sys
import uuid

import boto3


# Replace with your deployed agent ARN (or set AGENT_ARN env var)
AGENT_ARN = os.environ.get(
    "AGENT_ARN",
    "arn:aws:bedrock-agentcore:us-east-1:YOUR_ACCOUNT_ID:runtime/YOUR_AGENT_ID",
)


def invoke_agent(
    prompt: str,
    actor_id: str = "default-user",
    thread_id: str = None,
    stream: bool = True,
) -> str:
    """
    Invoke the deployed agent with optional memory support.
    
    Args:
        prompt: The user's message
        actor_id: User identifier for memory isolation
        thread_id: Conversation thread ID for memory persistence
        stream: Whether to stream output to console
        
    Returns:
        The agent's response
    """
    client = boto3.client("bedrock-agentcore")
    
    # Build payload with memory parameters
    payload_data = {
        "prompt": prompt,
        "actor_id": actor_id,
    }
    
    # Use provided thread_id or generate a new one
    if thread_id:
        payload_data["thread_id"] = thread_id
    else:
        payload_data["thread_id"] = str(uuid.uuid4())
    
    payload = json.dumps(payload_data).encode()
    
    response = client.invoke_agent_runtime(
        agentRuntimeArn=AGENT_ARN,
        runtimeSessionId=str(uuid.uuid4()),
        payload=payload,
        qualifier="DEFAULT",
    )
    
    # Collect response chunks
    content = []
    for chunk in response.get("response", []):
        decoded = chunk.decode("utf-8")
        content.append(decoded)
        if stream:
            print(decoded, end="", flush=True)
    
    if stream:
        print()  # Newline after streaming
    
    full_response = "".join(content)
    
    try:
        return json.loads(full_response)
    except json.JSONDecodeError:
        return full_response


def main():
    parser = argparse.ArgumentParser(
        description="Invoke a deployed AgentCore agent with KB, GuardRails, and Memory support"
    )
    parser.add_argument("prompt", help="The prompt to send to the agent")
    parser.add_argument(
        "--actor-id",
        default="default-user",
        help="User identifier for memory isolation (default: default-user)"
    )
    parser.add_argument(
        "--thread-id",
        default=None,
        help="Conversation thread ID for memory persistence (default: random UUID)"
    )
    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="Disable streaming output"
    )
    
    args = parser.parse_args()
    
    if AGENT_ARN.endswith("YOUR_AGENT_ID"):
        print("ERROR: Please set AGENT_ARN environment variable or update the script")
        print("Get the ARN from `agentcore launch` output or AWS Console")
        sys.exit(1)
    
    print(f"Invoking agent...")
    if args.thread_id:
        print(f"  Thread ID: {args.thread_id}")
        print(f"  Actor ID: {args.actor_id}")
    print(f"  Prompt: {args.prompt}\n")
    print("-" * 40)
    
    result = invoke_agent(
        prompt=args.prompt,
        actor_id=args.actor_id,
        thread_id=args.thread_id,
        stream=not args.no_stream,
    )
    
    print("-" * 40)
    
    if args.thread_id:
        print(f"\nTo continue this conversation, use: --thread-id {args.thread_id}")


if __name__ == "__main__":
    main()
