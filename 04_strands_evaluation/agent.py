"""
Lab 4: Strands Agent for Observability & Evaluation

This agent demonstrates AgentCore Evaluations using Strands Agents and is exactly the same flow as Lab 3

Strands Agents automatically produces spans with scope 'strands.telemetry.tracer'

Usage:
    # Deploy to AgentCore
    agentcore configure -e agent.py -n strands_eval_agent -r us-east-1 --non-interactive
    agentcore launch

    # Test
    agentcore invoke '{"prompt": "What is the weather in Seattle?"}'

    # Run evaluation
    agentcore eval run --evaluator "Builtin.Helpfulness"


AWS Documentation References ...
- AgentCore Observability: https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-observability.html
- AgentCore Online Evaluation: https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-evaluation.html
"""

import os
import json
import logging
from typing import AsyncGenerator

from strands.telemetry import StrandsTelemetry

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.models import BedrockModel

# Initialize StrandsTelemetry to enable OTEL tracing
StrandsTelemetry().setup_otlp_exporter()

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Configure logging to track feature initialization and errors
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Attempt to load a local .env file for developer convenience (no-op in production)
# This makes it clear which environment variables the agent expects and allows
# local testing without setting global environment variables.
try:
    from dotenv import load_dotenv

    _local_dotenv = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(_local_dotenv):
        load_dotenv(_local_dotenv)
        logger.info("Loaded .env for local development")
    else:
        logger.debug("No .env file found; create agent/.env from .env.example for local testing")
except ImportError:
    pass

# ============================================================================
# CONFIGURATION
# ============================================================================

# AWS Region and Model Configuration
REGION = "us-east-1"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

# System prompt updated to reflect available capabilities
# The agent uses this to understand what features it has access to
SYSTEM_PROMPT = """You are a helpful assistant deployed on AWS Bedrock AgentCore.
You can answer questions and use tools to help users.
Be concise and helpful in your responses."""

# ============================================================================
# TOOLS DEFINITION
# ============================================================================

# Example tool: Weather lookup
@tool
def get_weather(location: str) -> str:
    """Get the current weather for a location."""
    # Placeholder implementation - replace with real weather API
    return f"The weather in {location} is 72°F and sunny."

@tool 
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression. Example: calculate('2+2')"""
    try:
        # Security: Restrict eval() to only mathematical characters to prevent code injection
        allowed = set('0123456789+-*/.() ')
        if not all(c in allowed for c in expression):
            return "Error: Only basic math operations are allowed"
        result = eval(expression, {"__builtins__": {}}, {})
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {e}"

# ============================================================================
# AGENT SETUP
# ============================================================================

model = BedrockModel(
    model_id=MODEL_ID, 
    region_name=REGION
)

tools = [get_weather, calculate]

agent = Agent(
    model=model,
    tools=tools,
    prompt=SYSTEM_PROMPT,
)

# ============================================================================
# AGENTCORE APP
# ============================================================================

app = BedrockAgentCoreApp()

@app.entrypoint
async def handle_request(payload: dict, **kwargs) -> AsyncGenerator[str, None]:
    """
    Handle incoming requests with automatic tracing via Strands
    """
    # Extract prompt from payload
    prompt = payload.get("prompt", "")
    
    if not prompt:
        yield json.dumps({"error": "No prompt provided"})
        return

    logger.info(f"Processing: {prompt[:50]}...")
    
    input_data = {"messages": [{"role": "user", "content": prompt}]}
    
    try:
        # Strands agent call - automatically traced with strands.telemetry.tracer
        response = agent(prompt)
        yield str(response)
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        yield json.dumps({"error": "An error occurred processing your request"})


# ============================================================================
# LOCAL DEVELOPMENT SUPPORT
# ============================================================================

# For local development and testing
# Run this file directly to start a local development server
if __name__ == "__main__":
    app.run()
