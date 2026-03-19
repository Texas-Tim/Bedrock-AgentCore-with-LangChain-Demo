#!/usr/bin/env python3
"""Quick test harness for Knowledge Base, GuardRails, and Memory.

Usage:
  python tests/test_kb_gr_memory.py --query "your question"

This script attempts to:
 - Query an AWS Bedrock Knowledge Base via `AmazonKnowledgeBasesRetriever` when
   `BEDROCK_KNOWLEDGE_BASE_ID` is set, otherwise falls back to a local-file
   keyword search against the `example_knowledge_base/` folder included in
   this repo.
 - List GuardRails using the AWS Bedrock client (best-effort). If the AWS
   API is not available or the SDK version differs, it prints guidance to the
   AWS Console.
 - Initialize the `AgentCoreMemorySaver` (if `BEDROCK_MEMORY_ID` is set) and
   attempt basic save/load operations if supported by the checkpointer.

The script is defensive and prints helpful troubleshooting links.

Relevant docs:
 - LangChain retrievers: https://python.langchain.com/en/latest/modules/indexes/retrievers/overview.html
 - AWS Bedrock Knowledge Bases: https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-bases.html
 - AWS Bedrock GuardRails: https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html
 - Bedrock AgentCore Memory: https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-memory.html
"""

import os
import sys
import argparse
import logging
import traceback

from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("test_kb_gr_memory")


def test_local_kb_search(query: str, kb_dir: str = "example_knowledge_base") -> str:
    """Simple fallback: search for query substring in repo KB files."""
    kb_path = Path(kb_dir)
    if not kb_path.exists():
        return f"Local KB folder not found at {kb_dir}"

    results = []
    for f in sorted(kb_path.glob("**/*")):
        if f.is_file():
            text = f.read_text(encoding="utf-8", errors="ignore")
            if query.lower() in text.lower():
                excerpt = text.lower().split(query.lower(), 1)[0][-200:]
                results.append(f"{f}: ...{excerpt}>>{query}<<...")

    if not results:
        return "No matches found in local knowledge base."
    return "\n".join(results[:10])


def test_kb_aws(query: str, kb_id: str, region: str = "us-east-1") -> str:
    """Attempt to query AWS Knowledge Base via LangChain's AmazonKnowledgeBasesRetriever.

    This is best-effort: it will print helpful errors and links if the call fails.
    """
    try:
        from langchain_aws import AmazonKnowledgeBasesRetriever
    except Exception as e:
        logger.error("langchain_aws not available or import failed: %s", e)
        return (
            "langchain_aws import failed. Install langchain_aws and check LangChain docs:\n"
            "https://python.langchain.com/en/latest/"
        )

    try:
        retriever = AmazonKnowledgeBasesRetriever(
            knowledge_base_id=kb_id,
            region_name=region,
            retrieval_config={"vectorSearchConfiguration": {"numberOfResults": 5}},
        )

        docs = retriever.get_relevant_documents(query)
        if not docs:
            return "No relevant documents returned from AWS Knowledge Base."

        out = []
        for i, d in enumerate(docs, 1):
            # `page_content` is the common property for LangChain document objects
            out.append(f"Result {i}: {getattr(d, 'page_content', str(d))[:800]}")
        return "\n\n".join(out)

    except Exception:
        logger.exception("AWS Knowledge Base query failed")
        return (
            "AWS Knowledge Base query failed. Check:\n"
            " - BEDROCK_KNOWLEDGE_BASE_ID is correct and in the correct region.\n"
            " - Your AWS credentials and IAM permissions (bedrock:Retrieve).\n"
            "Docs: https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-bases.html"
        )


def test_guardrails_list(region: str = "us-east-1") -> str:
    """Attempt to list GuardRails via boto3 bedrock client (best-effort).

    Not all SDK versions expose the same helper methods; if listing fails we
    provide a pointer to the AWS Console.
    """
    try:
        import boto3
        client = boto3.client("bedrock", region_name=region)
        # Best-effort call. Some SDK versions may not have `list_guardrails`.
        if hasattr(client, "list_guardrails"):
            resp = client.list_guardrails()
            return str(resp)
        else:
            return (
                "This boto3 Bedrock client does not expose `list_guardrails()` in this SDK;"
                " check the AWS Console: https://console.aws.amazon.com/bedrock/home"
            )
    except Exception:
        logger.exception("Failed to list GuardRails via boto3")
        return (
            "Failed to list GuardRails via boto3. Ensure AWS credentials are configured.\n"
            "If using Windows, make sure WSL/WS credentials are available to this environment.\n"
            "AWS GuardRails docs: https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html"
        )


def test_memory(memory_id: str, region: str = "us-east-1") -> str:
    """Attempt to initialize `AgentCoreMemorySaver` and perform a minimal save/load.

    The concrete API of `AgentCoreMemorySaver` may vary depending on the library
    version; this test uses introspection to try common save/load methods and
    otherwise reports available attributes for manual inspection.
    """
    try:
        from langgraph_checkpoint_aws import AgentCoreMemorySaver
    except Exception as e:
        logger.error("AgentCoreMemorySaver import failed: %s", e)
        return (
            "AgentCoreMemorySaver not available. Ensure the `langgraph_checkpoint_aws`"
            " package is installed or consult your project's README."
        )

    try:
        cp = AgentCoreMemorySaver(memory_id, region_name=region)
    except Exception:
        logger.exception("Failed to initialize AgentCoreMemorySaver")
        return (
            "Failed to initialize AgentCoreMemorySaver. Check MEMORY_ID, region, and IAM permissions.\n"
            "Docs: https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-memory.html"
        )

    # Try common operations if available
    actions = []
    test_payload = {"test_key": "test_value"}

    # save-like
    for save_name in ("save_state", "save", "set", "put"):
        if hasattr(cp, save_name):
            try:
                getattr(cp, save_name)(test_payload)
                actions.append(f"Called {save_name}() successfully")
                break
            except Exception:
                actions.append(f"{save_name}() exists but raised an exception: {traceback.format_exc()}" )

    # load-like
    for load_name in ("load_state", "load", "get"):
        if hasattr(cp, load_name):
            try:
                val = getattr(cp, load_name)()
                actions.append(f"Called {load_name}() successfully, returned type: {type(val)}")
                break
            except Exception:
                actions.append(f"{load_name}() exists but raised an exception: {traceback.format_exc()}")

    if not actions:
        actions.append("No obvious save/load methods found on the checkpointer.\nAvailable attrs: " + ", ".join(sorted(dir(cp))))

    return "\n".join(actions)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default="support", help="Query string to search KB")
    parser.add_argument("--region", default=os.getenv("AWS_REGION", "us-east-1"))
    args = parser.parse_args()

    kb_id = os.getenv("BEDROCK_KNOWLEDGE_BASE_ID")
    guardrail_id = os.getenv("BEDROCK_GUARDRAIL_ID")
    memory_id = os.getenv("BEDROCK_MEMORY_ID")

    print("\n=== Knowledge Base Test ===\n")
    if kb_id:
        print(f"Using BEDROCK_KNOWLEDGE_BASE_ID={kb_id} (region={args.region})")
        print(test_kb_aws(args.query, kb_id, args.region))
    else:
        print("No BEDROCK_KNOWLEDGE_BASE_ID set; running local-file fallback against example_knowledge_base/")
        print(test_local_kb_search(args.query))

    print("\n=== GuardRails Test ===\n")
    if guardrail_id:
        print(f"BEDROCK_GUARDRAIL_ID is set: {guardrail_id}\nYou can inspect this GuardRail in the AWS Console: https://console.aws.amazon.com/bedrock/home")
    else:
        print("BEDROCK_GUARDRAIL_ID not set; attempting to list GuardRails via boto3 (best-effort):")
        print(test_guardrails_list(region=args.region))

    print("\n=== Memory Test ===\n")
    if memory_id:
        print(f"Using BEDROCK_MEMORY_ID={memory_id} (region={args.region})")
        print(test_memory(memory_id, region=args.region))
    else:
        print("BEDROCK_MEMORY_ID not set; skipping memory init test.\nIf you want to test memory, set BEDROCK_MEMORY_ID and run again.")


if __name__ == "__main__":
    main()
