"""FastAPI server exposing the ADK agent as a native AG-UI endpoint.

This is the key difference from the sibling `football-agent-adk-copilotkit`
repo: there, the webapp talked to `adk api_server`'s `/run` HTTP endpoint and a
BFF translated a chart JSON fence into A2UI. Here the ADK agent is wrapped by
the official `ag-ui-adk` middleware and served as a first-class AG-UI endpoint,
streaming AG-UI Protocol events. CopilotKit connects to it directly, and A2UI
runs natively (the LLM drives the UI via the injected `render_a2ui` tool).

Run: uv run uvicorn server:app --host 0.0.0.0 --port 8000
Endpoint: POST /chat  (accepts RunAgentInput, streams AG-UI events)
"""

import os

# This server IS the A2UI runtime: turn on the A2UI prompt + AGUIToolset before
# the agent module is imported (it reads the flag at import time).
os.environ.setdefault("ENABLE_A2UI", "true")

from fastapi import FastAPI  # noqa: E402
from ag_ui_adk import ADKAgent, add_adk_fastapi_endpoint  # noqa: E402

from football_a2ui_agent.agent import root_agent  # noqa: E402

adk_agent = ADKAgent(
    adk_agent=root_agent,
    app_name="football_a2ui_agent",
    user_id="webapp-user",
    # The catalogId of generated surfaces is chosen by the host, not the model:
    # ag-ui-adk infers it from the catalog context sent by the frontend, and
    # falls back to the A2UI BASIC catalog URL when that inference misses
    # (~1 run in 4) → "A2UI render error: Catalog not found:
    # https://a2ui.org/.../basic_catalog.json". Pin it explicitly.
    # Must match CATALOG_ID in webapp/components/A2uiCatalog.tsx.
    a2ui={"default_catalog_id": "football_catalog"},
)

app = FastAPI(title="Football A2UI Agent (AG-UI)")
add_adk_fastapi_endpoint(app, adk_agent, path="/chat")
