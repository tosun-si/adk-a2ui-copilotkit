# CLAUDE.md — adk-a2ui-copilotkit

## What this repo is

An experiment in the **real, agent-driven A2UI protocol** with **Google ADK** +
**CopilotKit**. The agent itself drives the UI: it emits A2UI generative-UI
operations, rendered natively in the chat. This is the basis of an article +
video on native A2UI.

Companion to the sibling repo `football-agent-adk-copilotkit` (the "CopilotKit
lite" variant). **Same use case** — a FIFA World Cup stats agent (the lite repo
stays on Qatar 2022, this repo moved to **2026**, see `data/`) that
queries BigQuery through MCP (Agent Registry) — but a fundamentally different
UI-integration approach.

### Lite repo vs this repo

| | lite repo | this repo |
|---|---|---|
| Transport | `adk api_server` `/run` HTTP + a BFF | **native AG-UI endpoint** (`ag-ui-adk`) |
| Who builds the UI | a BFF translates a `chart` JSON fence | **the LLM** (dynamic A2UI, `render_a2ui`) |
| Chart spec | proprietary JSON tunneled in message text | A2UI declarative surface (catalog components) |
| Frontend | CopilotKit chat + `chartTagRenderers` | CopilotKit v2 + A2UI catalog renderer |

The agent code is the **same BigQuery MCP agent**, minus `visualization.md`. In
dynamic A2UI you do NOT prompt the model to emit chart JSON — the runtime
injects a `render_a2ui` tool and the frontend catalog's component descriptions
guide it.

## Architecture

```
ADK agent (BigQuery MCP via Agent Registry)  — football_a2ui_agent/agent.py
  └─ wrapped by ag-ui-adk → native AG-UI endpoint  POST /chat   — agent/server.py
        ▼ AG-UI event stream
CopilotRuntime { agents:{ default: HttpAgent(/chat) }, a2ui:{ injectA2UITool:true } }
        ▼                                            — webapp/app/api/copilotkit/route.ts
<CopilotKitProvider a2ui={{ catalog }}> + <CopilotChat/>   — webapp catalog = basic + ECharts Chart
```

There is **no BFF translation step**. The agent is a first-class AG-UI endpoint;
A2UI runs natively (the LLM drives the UI).

## Project layout

```
.
├── agent/
│   ├── football_a2ui_agent/
│   │   ├── agent.py            # BigQuery MCP agent; A2UI (a2ui.md + AGUIToolset) only if ENABLE_A2UI
│   │   ├── prompts/            # role, schema, query_workflow, business_rules, a2ui
│   │   ├── .env                # Agent Engine runtime env (telemetry), bundled by adk deploy
│   │   └── .ae_ignore          # excluded from the adk deploy source bundle
│   ├── server.py               # ag-ui-adk: ADKAgent + add_adk_fastapi_endpoint(path="/chat"), sets ENABLE_A2UI
│   ├── deploy_agent_engine.sh  # uv export → adk deploy agent_engine --otel_to_cloud
│   ├── tests/a2ui_bench.py     # A2UI reliability bench (replays the captured CopilotKit request)
│   ├── pyproject.toml          # single-package uv project; groups: agui (local only), dev
│   ├── uv.lock
│   └── Dockerfile
├── webapp/
│   ├── app/
│   │   ├── api/copilotkit/route.ts   # CopilotRuntime: HttpAgent → /chat, a2ui injectA2UITool
│   │   ├── layout.tsx                 # Providers + "@copilotkit/react-core/v2/styles.css"
│   │   └── page.tsx                   # CopilotChat (react-core/v2)
│   ├── components/
│   │   ├── A2uiCatalog.tsx     # A2UI catalog: CATALOG_ID + Chart (5 types) → ECharts
│   │   ├── EChart.tsx          # ECharts renderer (used directly, React-19 safe)
│   │   └── Providers.tsx       # CopilotKitProvider a2ui={{ catalog }}
│   └── Dockerfile
├── data/
│   ├── build_dataset.py        # openfootball (+ FBref assists) → 5 NDJSON tables + validations (stdlib)
│   ├── load_bigquery.sh        # bq load --replace into fifa_world_cup_2026
│   ├── raw/                    # openfootball 2026 files, pinned commit (see data/README.md)
│   └── schemas/                # BigQuery schemas with column descriptions (read by get_table_info)
├── scripts/
│   ├── setup_gcp.sh            # APIs (incl. telemetry.googleapis.com) + IAM for the AE service agent
│   ├── query_agent_engine.py   # smoke test / warm-up of the deployed engine
│   └── cleanup_old_engines.sh  # GC old Reasoning Engines (dry-run by default)
├── talks/demo_adk_en_action.md # talk 1 « ADK en action »: demo flow, Agent Platform ideas, empty-traces checklist
├── talks/demo_nl_to_sql.md     # talk 2 NL to SQL (DevFest Paris): Docker Compose demo flow, questions + expected answers
└── docker-compose.yaml         # adk-web (:8080) + agent (:8000 AG-UI /chat) + webapp (:3000)
```

## Run locally

Needs GCP credentials (Agent Registry + BigQuery), project `gb-poc-373711`.
Run `gcloud auth application-default login` if the local ADC is expired — an
expired ADC surfaces as the agent giving **no response at all** (not a chart
error).

```bash
docker compose up --build          # all services (adk-web, agent, webapp)
docker compose up --build agent    # rebuild only the agent (prompt-only change)
docker compose up --build webapp   # rebuild only the webapp (front change)
```

Open http://localhost:3000. The agent is at http://localhost:8000/chat. ADK web
(same image, `adk web`, A2UI off) is at http://localhost:8080.

## One agent, three runtimes (`ENABLE_A2UI`)

`render_a2ui` only exists when the CopilotKit runtime injects it, so the A2UI
prompt (`a2ui.md`) and `AGUIToolset()` are wired only when `ENABLE_A2UI=true`.
`server.py` sets it (AG-UI runtime); `adk web` and Agent Engine leave it unset
→ plain-text answers, and no `ag-ui-adk` dependency on Agent Engine
(`ag-ui-adk` lives in the `agui` dependency group, excluded from the export).

## Agent Engine deploy (Agent Platform)

`agent/deploy_agent_engine.sh` (set `AGENT_ENGINE_ID` to update in place).
Upgraded to **ADK 2.14.0** on 2026-11-12 (was 2.6.0). Specifics:

- ADK 2.14's `adk deploy agent_engine` needs **`google-cloud-aiplatform>=2.2`**
  (the `agentplatform.Client.runtimes` surface); on 1.x it aborts before
  creating anything. 2.x drops `opentelemetry-exporter-gcp-trace` from the
  lock — traces use OTLP, but re-check the Traces tab after a deploy.
- **`ag-ui-adk` stays `<0.8`**: 0.8+ requires `ag-ui-protocol>=1.0`, the webapp
  is pinned to `@ag-ui/client` 0.0.53. Bump both sides together.
- **Demo engine `3830629241939034112`** (`football-stats-agent-adk`, created
  as `-test`, promoted in place on 2026-11-12) runs ADK 2.14: answers
  correctly, traces verified in the console (sessions, model/tool calls,
  prompts + SQL captured). The former demo engine `5448783803071856640` was
  deleted on 2026-09-29.

- `requirements.txt` must be IN the agent folder (`--requirements_file` is
  deprecated/ignored). Generated by `uv export --no-default-groups` — the flag
  matters: `default-groups = ["dev","agui"]`, so `--no-dev` alone would still
  ship `ag-ui-adk`. Without the file, adk writes a bare `google-adk[a2a]` →
  engine fails on missing extras.
- ADK (2.6 and 2.14) deploys via a generated Dockerfile running `adk api_server
  --otel_to_cloud`. Traces go over OTLP to **`telemetry.googleapis.com`** (not
  the legacy Cloud Trace API) → that API must be enabled and the AE service
  agent needs `roles/telemetry.tracesWriter`. This was the likely cause of the
  empty Traces tab in earlier attempts. `scripts/setup_gcp.sh` handles both.
- `--otel_to_cloud` defaults `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false` unless
  set in `.env` → set to `true` there (public dataset) to see prompts/SQL in spans.
- Pass the agent folder as an ABSOLUTE path, else `.env` is silently skipped.
- **MCP tool prefix → intermittent "Tool 'execute_sql_readonly' not found"**.
  `AgentRegistry.get_mcp_toolset` prefixes tools with the cleaned displayName
  (`bigquery_googleapis_com_execute_sql_readonly`); Gemini sometimes calls the
  native MCP name. Hit ~1 run in 2 on Agent Engine, rarely locally (don't trust
  a green local run). Fix in `agent.py`: `toolset.tool_name_prefix = None`
  (single MCP server → no clash) + `tool_filter = BIGQUERY_READONLY_TOOLS`
  (read-only tools only). Prompts use the unprefixed names.
- Player names: `player_name` keeps accents (`Kylian Mbappé`), filters go on
  `player_search_name` (lower-case ASCII) with LIKE → rule 5 in
  `prompts/query_workflow.md`.

## Reliability guards in `agent.py` (A2UI bench, 2026-11-12)

Measured with `agent/tests/a2ui_bench.py` — replays the real CopilotKit → agent
request (render_a2ui tool + catalog context, fixture in `agent/tests/fixtures/`)
15× per demo question, 5 in parallel, validating each surface. Rerun it before
a talk and after any prompt / model / ADK change.
Baseline 67/70; with all guards, 105/105 on ADK 2.6 and on 2.14.

- **MCP session drops → the model answers from memory.** "Failed to get tools
  from MCP server" (anyio BrokenResourceError) → ADK retries list_tools once,
  then calls the model WITHOUT the BigQuery tools → invented charts (De Bruyne
  in the assists top 5). 2.14 reduces it (27 → 11-16 failures per 105 runs),
  does not remove it. Guards: `_retry_get_tools` (4 attempts,
  `MCP_LIST_TOOLS_ATTEMPTS`), `require_bigquery_tools` (no BigQuery tool →
  honest "BigQuery indisponible" answer), and render_a2ui blocked when no SQL
  ran in the turn.
- **Token-level glitches in render_a2ui args** (3.8-flash): a `"id` key with a
  stray quote, or a Chart without `component` → repaired in
  `repair_render_a2ui_args` (after_model_callback). Not fixable by prompt.
- **Do NOT force a tool call** with `tool_config mode=ANY` on the first model
  call: tried, it made the model answer in tables instead of charts (86/105).
- **Model the data for the agent**: a heatmap "goals per team and stage" took
  40-90 s (2-4 SQL, home/away UNION on `matches`). The `team_matches` table
  (one row per team per match) brings it to 1 query, median 71 → 46 s under
  load, 15-45 s sequential (a bar chart is ~10 s). Full bench still 105/105.
- `server.py`: `max_concurrent_executions=200` — a run ending on render_a2ui
  stays active per thread; the default 10 blocks the agent after 10 reloads.

## Talk assets (GDG Paris)

- `talks/slides_content.py` (contenu) + `talks/generate_slides.py` (rendu, charte
  GroupBees : dégradé cyan→violet, encre #14141A, Avenir Next, puces hexagones,
  logo en footer) → `talks/slides/talk_gdg_paris_adk.pptx`
  (`uv run --with python-pptx python talks/generate_slides.py`)
- `talks/assets/` — logo + mascotte téléchargés depuis groupbees.fr,
  `logo_light.png` (logo recoloré pour les fonds sombres) et `usbc.png`
  (icône dessinée dans `usbc.svg`, rendue via Chrome headless)
- `talks/slides/deck.pdf` — export PDF (secours pour la présentation). Régénérer :
  ouvrir le pptx dans PowerPoint puis « save as PDF » (AppleScript), ou à la main
- `diagrams/adk_agent_platform_archi.excalidraw` (+ exported `.png` used by the
  architecture slide — re-export from Excalidraw after editing)
- Two talks share this repo, one demo file each: `talks/demo_adk_en_action.md`
  (GDG Cloud Paris) and `talks/demo_nl_to_sql.md` (DevFest Paris; deck lives in
  `~/my-projects/conferences/devfest_paris/2026/talk_nl_to_sql/`)

## agents-cli skills (workspace scope)

`.claude/skills/` holds the 7 `google-agents-cli-*` skills, installed with
`uvx google-agents-cli setup --workspace --agent claude-code` (workspace scope
on purpose: nothing lands in `~/.claude/skills`). They are gitignored vendored
copies — reinstall with that command. Details in the README.

## Model choice (`MODEL` / `MODEL_LOCATION`)

`agent.py` reads both from the env — default **`gemini-3.8-flash` +
`MODEL_LOCATION=global`** since 2026-11-11 (latest GA Flash; `gemini-2.5-flash`
was retired on Vertex on 2026-10-20, so it is no longer a fallback). Newer
`gemini-3.8-flash-cyber` / `gemini-omni-1.2-flash` are specialised, not general
Flash. `MODEL_LOCATION=""` = use `GOOGLE_CLOUD_LOCATION`. Tested 2026-09-21:

- `gemini-3.8-flash` is **404 in europe-west1**; it is served from the `global`
  endpoint. `MODEL_LOCATION=global` routes ONLY the model calls there (ADK
  `Gemini(client_kwargs={"location": ...})`); sessions, Agent Registry and
  BigQuery stay in `GOOGLE_CLOUD_LOCATION`. Putting `GOOGLE_CLOUD_LOCATION` in
  the agent `.env` does NOT work: `adk deploy` ignores it when `--region` is
  passed, and the generated image bakes the region.
- On the BigQuery path 3.8 is fine (richer formatting). **On A2UI it is worse**:
  5 bar-chart runs → 2 × `Component 'Chart' is missing an 'id'` (malformed
  components) vs 2.5's 9 runs → 2 × `Catalog not found`. Radar is fine on both.
  That was the reason to stay on 2.5 for GDG Paris; 2.5 is now gone, so the
  mitigation is in `prompts/a2ui.md` (explicit WRONG/RIGHT component shape).

## Pinned versions — do NOT float these

- **`@copilotkit/*` = exactly `1.57.3`** (not `^`). A fresh install floats to
  1.64.x whose A2UI API differs from what this repo was built against.
- **`@ag-ui/client` = `0.0.53`** — must match the version `@copilotkit/runtime`
  1.57.3 expects. A newer `HttpAgent` fails to satisfy `AbstractAgent`
  (`pendingInterrupts` missing) → type error in `route.ts`.
- **`zod` = `^3.25`** (v3, NOT v4). CopilotKit is built against zod v3; a v4
  `z.object` breaks `createCatalog` at the type level (and likely runtime).
- **`echarts`** used **directly** (`import * as echarts`), not
  `echarts-for-react` — the wrapper lags on React 19. `EChart.tsx` inits on a
  ref in `useEffect` with a `ResizeObserver`.

> Full explanation of the A2UI wiring (both sides + failure causes):
> [`docs/a2ui.md`](docs/a2ui.md).

## Dynamic A2UI conventions (learned the hard way)

These are the non-obvious rules that make dynamic A2UI actually work here. Each
was a real failure we hit and fixed.

1. **The agent must carry `AGUIToolset()`** (in `agent.py` `tools=[...]`). It
   surfaces the runtime-injected `render_a2ui` tool to the ADK agent. Without
   it, the LLM has no way to render UI.

2. **Enable A2UI on BOTH ends.** Runtime: `a2ui: { injectA2UITool: true }`
   (`route.ts`). Provider: `a2ui={{ catalog }}` (`Providers.tsx`) — passing the
   catalog is what makes the middleware inject `render_a2ui` AND sends the
   catalog component schemas to the agent (`includeSchema` defaults true).

3. **Pin the `catalogId` with a LITERAL in the prompt.** The LLM fills the
   surface's `catalogId` itself and WILL hallucinate (`chart_catalog`, a URL, …)
   → `A2UI render error: Catalog not found: <x>` (the processor matches ids
   exactly). Fix: register under a short fixed id (`CATALOG_ID =
   "football_catalog"` in `A2uiCatalog.tsx`) and give that literal value in
   every `prompts/a2ui.md` example + a hard rule. Never use a placeholder like
   `<use the catalog id from context>` — the model fills it with garbage. Short
   token > long URL (copied more reliably).

4. **Give a concrete, valid flat-component example per chart type in
   `prompts/a2ui.md`.** In dynamic mode the LLM hand-builds the A2UI flat
   component array and gets it wrong without a template
   (`Component 'undefined' is missing an 'id'` — every component needs both
   `id` and `component`; root must be a layout component with `id:"root"`).
   The model anchors HARD on examples: it will only reliably produce chart types
   it has seen an example for, and will otherwise reply "I can't create that" —
   so a2ui.md states explicitly that all five types are supported and shows a
   radar and a heatmap example, not just a bar.

5. **Catalog component props are LLM-facing.** Their zod `.describe()` text is
   sent to the agent as schema context. Model the chart with explicit,
   self-documenting props (`chartType`, `xKey`, `yKeys`, `data`) with clear
   descriptions and per-type data-shape notes — not one opaque blob.

6. **`includeBasicCatalog: true`** so the catalog is a superset (Column, Text, …
   + our Chart) and the LLM can compose real declarative surfaces.

## The Chart component (ECharts BYOC)

One `Chart` component, five `chartType`s the LLM picks from at runtime:
`bar`, `line`, `pie`, `radar`, `heatmap`. Data shapes (documented in the prop
`.describe()` and `a2ui.md`):

- **bar / line / pie**: `[{ "name": "...", "value": <number> }, ...]`
  (multi-series bar/line: extra numeric keys listed in `yKeys`).
- **radar**: each item is ONE axis; one numeric key per entity — several keys
  compare entities overlaid, e.g.
  `[{ "name":"Buts", "mbappe":10, "messi":8 }, ...]`, `yKeys=["mbappe","messi"]`.
  Each axis has its own scale (`EChart.tsx`), so minutes and goals can share a radar.
- **heatmap**: `[{ "x": "<col>", "y": "<row>", "value": <number> }, ...]`
  (no `xKey`/`yKeys`).

Adding a chart type = extend the `chartType` enum + its data-shape description in
`A2uiCatalog.tsx`, add a `buildOption` branch in `EChart.tsx`, and add an
example to `prompts/a2ui.md` (the model needs the example to use it).

## Dynamic vs static A2UI (the article's core insight)

This repo is **dynamic** A2UI: the LLM decides when to render and hand-builds the
A2UI operations. That is powerful (the agent picks radar for a profile, heatmap
for a matrix) but **non-deterministic** — hence gotchas 3 & 4 above (hallucinated
catalogId, malformed components), mitigated by literal examples in the prompt.

The planned counterpoint is a **static agent-native** variant
(`a2ui.create_surface()` / `a2ui.render()` in Python) where the operations are
generated by deterministic code — no hallucination, at the cost of the LLM's
autonomy in choosing the UI. Dynamic-vs-static is the comparison the article
makes.

## GCP project

- Project ID: `gb-poc-373711`, region `europe-west1`
- BigQuery dataset `fifa_world_cup_2026` (europe-west1): `players`,
  `player_matches`, `team_matches`, `matches`, `teams`. Built by `data/build_dataset.py` from
  openfootball (CC0, pinned in `data/raw/`), loaded by `data/load_bigquery.sh`.
  The Qatar dataset `qatar_fifa_world_cup` is kept for the lite repo.
- Goals/minutes/cards from openfootball (matches the FIFA goalscorer list
  178/178). **Assists from a hand-made FBref CSV export**
  (`data/raw/fbref_wc2026_standard.csv`, gitignored) — Kaggle mominullptr was
  wrong (Olise 8 vs 7, Dembélé 5 goals vs 6), API-Football free plan has no 2026.
  No shots / xG / per-match assists: the prompt tells the agent to say so.
- Gemini 2.5's training predates the tournament → `role.md` forbids answering
  from memory (it would quote 2022 numbers).

## Conventions

- Personal open-source repo → commits use descriptive titles, no
  `Co-Authored-By` trailer, HEREDOC for multi-line bodies.
- Docker is the canonical local path (`docker compose up --build`). Per-service
  Dockerfiles; agent is a single-package uv build (`--no-install-project`),
  webapp is a Next standalone build.
