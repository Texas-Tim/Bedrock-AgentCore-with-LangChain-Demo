"""
Invoke a deployed AgentCore Runtime agent using the AWS SDK.

Usage:
    python invoke_deployed_agent.py "What is the weather in Seattle?"

Requires:
    - Agent deployed to AgentCore Runtime
    - AGENT_ARN environment variable or update the ARN below
    - AWS credentials with bedrock-agentcore:InvokeAgentRuntime permission
"""

import json
import sys
import uuid
import os

import boto3

# Replace with your deployed agent ARN (or set AGENT_ARN env var)
AGENT_ARN = os.environ.get(
    "AGENT_ARN",
    "arn:aws:bedrock-agentcore:us-east-1:YOUR_ACCOUNT_ID:runtime/YOUR_AGENT_ID",
)


def invoke_agent(prompt: str, stream: bool = False) -> str:
    """Invoke the deployed agent."""
    client = boto3.client("bedrock-agentcore")

    payload = json.dumps({"prompt": prompt}).encode()

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

    full_response = "".join(content)

    try:
        return json.loads(full_response)
    except json.JSONDecodeError:
        return full_response


def main():
    if len(sys.argv) < 2:
        print("Usage: python invoke_deployed_agent.py <prompt>")
        print('Example: python invoke_deployed_agent.py "What is the weather in Seattle?"')
        sys.exit(1)

    prompt = sys.argv[1]

    if AGENT_ARN.endswith("YOUR_AGENT_ID"):
        print("ERROR: Please set AGENT_ARN environment variable or update the script")
        print("Get the ARN from `agentcore launch` output or AWS Console")
        sys.exit(1)

    print(f"Invoking agent with prompt: {prompt}\n")
    result = invoke_agent(prompt)
    print(f"\nResponse: {result}")


if __name__ == "__main__":
    main()
