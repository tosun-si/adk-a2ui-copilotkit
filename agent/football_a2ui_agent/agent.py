import os
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.integrations.agent_registry import AgentRegistry

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "gb-poc-373711")
DATASET_LOCATION = os.environ.get("LOCATION", "europe-west1")  # For BigQuery Dataset
REGISTRY_LOCATION = "global"  # Agent Registry is global only for MCP servers
# Model, overridable without touching the code — handy to fall back live.
# Default = latest GA Flash (gemini-2.5-flash was retired on Vertex 2026-10-20).
# `gemini-3.8-flash` does NOT exist in europe-west1 (404): it is served from the
# `global` endpoint, hence MODEL_LOCATION="global" by default. Only the model
# calls are routed there; sessions, Agent Registry and BigQuery stay in
# GOOGLE_CLOUD_LOCATION. MODEL_LOCATION="" = use GOOGLE_CLOUD_LOCATION.
MODEL = os.environ.get("MODEL", "gemini-3.8-flash")
MODEL_LOCATION = os.environ.get("MODEL_LOCATION", "global")

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


UNAVAILABLE_MESSAGE = (
    "Je n'arrive pas à interroger BigQuery pour le moment (connexion MCP "
    "indisponible). Repose ta question dans quelques secondes."
)


def _text_response(text):
    from google.adk.models.llm_response import LlmResponse
    from google.genai import types

    return LlmResponse(content=types.Content(role="model", parts=[types.Part(text=text)]))


def require_bigquery_tools(callback_context, llm_request):
    """before_model_callback: never call the model without the BigQuery tools.

    When the MCP session to BigQuery breaks (anyio BrokenResourceError, seen
    under load), ADK logs "Failed to get tools from MCP server" and calls the
    model WITHOUT the BigQuery tools. The model, whose training predates the
    2026 tournament, then answers — or renders a chart — from memory: Bruno
    Fernandes and De Bruyne in the assists top 5, Mbappé at 7 goals. An honest
    "BigQuery unavailable" beats a confident wrong chart.
    """
    if "execute_sql_readonly" not in (llm_request.tools_dict or {}):
        return _text_response(UNAVAILABLE_MESSAGE)
    return None


def _sql_ran_this_turn(callback_context) -> bool:
    session = callback_context.session
    for event in session.events if session else []:
        if event.invocation_id != callback_context.invocation_id:
            continue
        for response in event.get_function_responses():
            if response.name == "execute_sql_readonly":
                return True
    return False


def _clean_keys(value):
    """Recursively strip stray quotes / spaces from dict keys: '"id' → 'id'."""
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            clean = key.strip().strip('"').strip("'").strip() if isinstance(key, str) else key
            # never let a repaired key overwrite a well-formed one
            out[clean if clean not in value or clean == key else key] = _clean_keys(item)
        return out
    if isinstance(value, list):
        return [_clean_keys(item) for item in value]
    return value


def repair_render_a2ui_args(callback_context, llm_response):
    """after_model_callback: repair render_a2ui arguments before they leave the agent.

    gemini-3.8-flash sometimes emits a component key with a stray escaped quote,
    `{"\"id": "chart", ...}`: the parsed key is `"id`, not `id`, and the frontend
    fails with "Component 'Chart' is missing an 'id'" (2-3 % of renders in our
    bench). A token-level glitch no prompt rule removes reliably, so it is fixed
    deterministically here. Only render_a2ui arguments are touched.
    """
    content = llm_response.content
    if not content or not content.parts:
        return None
    renders = [p.function_call for p in content.parts
               if p.function_call and p.function_call.name == "render_a2ui"]
    if not renders:
        return None
    if not _sql_ran_this_turn(callback_context):
        # A chart whose numbers did not come from BigQuery: block it.
        return _text_response(
            "Je dois d'abord interroger la base avant d'afficher un graphique. "
            "Repose ta question."
        )
    for call in renders:
        if call.args:
            args = _clean_keys(dict(call.args))
            # Same family of glitch: a Chart emitted without its `component`
            # key (1 run in 105). `chartType` only exists on our Chart.
            for comp in args.get("components") or []:
                if isinstance(comp, dict) and "component" not in comp and "chartType" in comp:
                    comp["component"] = "Chart"
            call.args = args
    return llm_response


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


def _retry_get_tools(toolset, attempts: int = 4) -> None:
    """ADK retries a failed MCP `list_tools` only ONCE; under load both attempts
    can hit a broken session (anyio BrokenResourceError) and the model is then
    called without the BigQuery tools. Retry a few more times with a backoff."""
    import asyncio

    original = toolset.get_tools

    async def get_tools(readonly_context=None):
        for attempt in range(1, attempts + 1):
            try:
                return await original(readonly_context)
            except ConnectionError:
                if attempt == attempts:
                    raise
                await asyncio.sleep(0.5 * attempt)

    toolset.get_tools = get_tools


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
    _retry_get_tools(toolset, int(os.environ.get("MCP_LIST_TOOLS_ATTEMPTS", "4")))

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
            "Answers questions about the 2026 FIFA World Cup (Canada/Mexico/USA) "
            "using BigQuery: player stats, goals, minutes, cards, clubs, "
            "match-by-match evolution, results and team rankings."
        ),
        instruction=SYSTEM_INSTRUCTION,
        tools=tools,
        before_model_callback=require_bigquery_tools,
        after_model_callback=repair_render_a2ui_args if ENABLE_A2UI else None,
    )


root_agent = create_agent()
