import os
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.integrations.agent_registry import AgentRegistry

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "gb-poc-373711")
DATASET_LOCATION = os.environ.get("LOCATION", "europe-west1")  # For BigQuery Dataset
REGISTRY_LOCATION = "global"  # Agent Registry is global only for MCP servers
# Model, overridable without touching the code — handy to fall back live.
# `gemini-3.8-flash` does NOT exist in europe-west1 (404): it is served from the
# `global` endpoint, hence MODEL_LOCATION. Only the model calls are routed
# there; sessions, Agent Registry and BigQuery stay in GOOGLE_CLOUD_LOCATION.
MODEL = os.environ.get("MODEL", "gemini-2.5-flash")
MODEL_LOCATION = os.environ.get("MODEL_LOCATION")  # e.g. "global" for 3.x flash

# Same agent, three runtimes:
#   - `adk web` (local dev UI)          → ENABLE_A2UI unset → plain text answers
#   - Agent Engine (Agent Platform)     → ENABLE_A2UI unset → plain text answers
#   - ag-ui-adk server + CopilotKit     → ENABLE_A2UI=true  → dynamic A2UI charts
# The `render_a2ui` tool only exists when the CopilotKit runtime injects it, so
# the A2UI prompt + AGUIToolset are wired in only for the AG-UI runtime.
# Otherwise the model would try to call a tool that does not exist.
ENABLE_A2UI = os.environ.get("ENABLE_A2UI", "false").lower() in ("1", "true")

# System instructions are split across `prompts/*.md` files, one per concern.
#
# NOTE (A2UI dynamic mode): unlike the sibling copilotkit repo, there is NO
# `visualization.md` here. We do NOT tell the model how to hand-write chart
# JSON. In dynamic A2UI the CopilotKit runtime's A2UIMiddleware injects a
# `render_a2ui` tool (plus usage guidelines and the frontend catalog schema)
# into the agent at request time. The LLM decides when to render UI and which
# catalog components to use — driven by the components' `description` fields,
# not by a prompt. AGUIToolset() below is what surfaces that injected tool to
# the ADK agent.
PROMPTS_DIR = Path(__file__).parent / "prompts"
PROMPT_ORDER = [
    "role.md",
    "schema.md",
    "query_workflow.md",
    "business_rules.md",
]
if ENABLE_A2UI:
    # Not chart-JSON-in-text (that was the lite repo). This teaches the model to
    # call the injected render_a2ui tool with a well-formed FLAT component array
    # — needed because dynamic A2UI otherwise produces malformed components
    # ("Component 'undefined' is missing an 'id'").
    PROMPT_ORDER.append("a2ui.md")


def _load_system_instruction() -> str:
    parts = [(PROMPTS_DIR / name).read_text() for name in PROMPT_ORDER]
    return "\n\n".join(parts).replace("{{PROJECT_ID}}", PROJECT_ID)


SYSTEM_INSTRUCTION = _load_system_instruction()


def get_header(context):
    return {"x-goog-user-project": PROJECT_ID}


BIGQUERY_MCP_DISPLAY_NAME = "bigquery.googleapis.com"

# Least privilege: expose only the read-only BigQuery MCP tools to the model
# (no `execute_sql` DML/DDL, no `cancel_job`). IAM stays the real guardrail;
# this just keeps the model from even seeing write tools.
BIGQUERY_READONLY_TOOLS = [
    "list_dataset_ids",
    "list_table_ids",
    "get_dataset_info",
    "get_table_info",
    "execute_sql_readonly",
    "get_query_results",
]


def _resolve_mcp_server_name(registry: AgentRegistry, display_name: str) -> str:
    """Look up an MCP server's resource name by its display name.

    Agent Registry assigns opaque UUIDs to each MCP server, so we cannot
    hardcode the resource name. We list servers and match by `displayName`
    (e.g. `bigquery.googleapis.com`).
    """
    response = registry.list_mcp_servers()
    for server in response.get("mcpServers", []):
        if server.get("displayName") == display_name:
            return server["name"]
    raise ValueError(
        f"No MCP server with displayName {display_name!r} found in Agent Registry "
        f"(project={PROJECT_ID}, location={REGISTRY_LOCATION})."
    )


def create_agent():
    agent_registry = AgentRegistry(
        project_id=PROJECT_ID,
        location=REGISTRY_LOCATION,
        header_provider=get_header,
    )

    mcp_server_name = _resolve_mcp_server_name(
        agent_registry, BIGQUERY_MCP_DISPLAY_NAME
    )
    toolset = agent_registry.get_mcp_toolset(mcp_server_name)

    if not toolset:
        raise ValueError("Could not load BigQuery toolset from Agent Registry.")

    # ADK 2.6 prefixes every Agent Registry MCP tool with the server's cleaned
    # displayName (`bigquery_googleapis_com_execute_sql_readonly`). Gemini
    # intermittently calls the NATIVE MCP name instead (`execute_sql_readonly`)
    # → "Tool 'execute_sql_readonly' not found" (seen ~1 run out of 2 on Agent
    # Engine). With a single MCP server there is no name clash to avoid, so we
    # drop the prefix: the name the model tends to emit IS the real one.
    toolset.tool_name_prefix = None
    toolset.tool_filter = BIGQUERY_READONLY_TOOLS

    tools = [toolset]
    if ENABLE_A2UI:
        # Lazy import: ag-ui-adk is only installed for the AG-UI runtime, not in
        # the Agent Engine image.
        from ag_ui_adk import AGUIToolset

        # Surfaces the runtime-injected render_a2ui tool so the model can drive
        # the UI in dynamic A2UI mode.
        tools.append(AGUIToolset())

    model = MODEL
    if MODEL_LOCATION:
        # ADK exposes client_kwargs to reach a Gemini endpoint in another
        # location than GOOGLE_CLOUD_LOCATION.
        from google.adk.models import Gemini

        model = Gemini(model=MODEL, client_kwargs={"location": MODEL_LOCATION})

    return LlmAgent(
        model=model,
        name="football_a2ui_agent",
        description=(
            "Answers questions about Qatar 2022 FIFA World Cup using BigQuery: "
            "player stats, team rankings, goals, assists, defensive metrics, "
            "goalkeeper save percentages, and computed performance ratings."
        ),
        instruction=SYSTEM_INSTRUCTION,
        tools=tools,
    )


root_agent = create_agent()
