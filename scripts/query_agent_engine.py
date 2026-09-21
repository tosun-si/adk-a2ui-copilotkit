"""Smoke-test / warm up the deployed agent on Agent Engine.

Run it a few minutes before going on stage: it wakes the engine (scale-to-zero),
exercises the MCP → BigQuery path end to end and produces a fresh trace + session
to show in the console.

    AGENT_ENGINE_ID=1234567890 uv run python ../scripts/query_agent_engine.py
    AGENT_ENGINE_ID=... uv run python ../scripts/query_agent_engine.py "Top 5 buteurs ?"
"""

import asyncio
import os
import sys

import vertexai

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "gb-poc-373711")
LOCATION = os.environ.get("LOCATION", "europe-west1")
ENGINE_ID = os.environ["AGENT_ENGINE_ID"]
USER_ID = "gdg-paris-demo"
QUESTION = sys.argv[1] if len(sys.argv) > 1 else "Qui a marqué le plus de buts ?"


async def main() -> None:
    client = vertexai.Client(project=PROJECT_ID, location=LOCATION)
    name = f"projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{ENGINE_ID}"
    agent = client.agent_engines.get(name=name)

    session = await agent.async_create_session(user_id=USER_ID)
    print(f"Session: {session['id']}\nQ: {QUESTION}\n")

    async for event in agent.async_stream_query(
        user_id=USER_ID, session_id=session["id"], message=QUESTION
    ):
        if error := event.get("error_message"):
            sys.exit(f"  ✗ {event.get('error_code')}: {error}")
        for part in event.get("content", {}).get("parts", []):
            if call := part.get("function_call"):
                print(f"  → tool {call['name']}({call.get('args', {})})")
            elif part.get("function_response"):
                print(f"  ← {part['function_response']['name']} ok")
            elif text := part.get("text"):
                print(text, end="")
    print()


if __name__ == "__main__":
    asyncio.run(main())
