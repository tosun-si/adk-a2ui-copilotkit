# How A2UI works in this repo

How the agent ends up drawing a chart in the browser — the Python side, the
frontend side, and what travels between them. Everything here was verified
against the running stack (ADK 2.6, `ag-ui-adk` 0.7.0, CopilotKit 1.57.3).

## The idea in one paragraph

The model does not return HTML or JavaScript. It returns a **declarative
description of a UI**, made of components the frontend declared in advance. The
frontend renders them with its own React code. So the agent *drives* the UI; it
does not *generate* it. It can only show what you allowed it to show.

## The round trip

```
Browser                    Next.js runtime              ADK agent (Python)
   │                             │                              │
   │ question ──────────────────▶│                              │
   │                             │ AG-UI request ──────────────▶│
   │                             │  + injectA2UITool            │
   │                             │  + catalog schema            │ BigQuery via MCP
   │                             │                              │◀────────────────
   │                             │◀── AG-UI event stream ───────│
   │◀── text + A2UI operations ──│    (text, tool calls,        │
   │                             │     createSurface, …)        │
   ▼
A2UI processor → resolves catalogId → our <Chart> renderer → ECharts canvas
```

## Python side

### `agent.py` — A2UI is opt-in

```python
ENABLE_A2UI = os.environ.get("ENABLE_A2UI", "false").lower() in ("1", "true")

if ENABLE_A2UI:
    PROMPT_ORDER.append("a2ui.md")   # how to build a valid A2UI surface
    tools.append(AGUIToolset())      # bridge to the client-injected tools
```

`AGUIToolset()` defines no tool of its own. It is a **bridge**: it exposes to the
ADK agent whatever tools the client injects at request time. Without it the
agent has no way to know that rendering UI is even possible.

The flag exists because the same agent runs in three places. `adk web` and Agent
Engine have no CopilotKit runtime in front of them, so the injected tool never
exists there — instructing the model to call it would only produce failures.

| Runtime | `ENABLE_A2UI` | Behaviour |
|---|---|---|
| `adk web` | unset | plain text answers |
| Agent Engine | unset | plain text answers |
| `server.py` (AG-UI) | `true` | dynamic A2UI charts |

### `server.py` — the agent becomes an AG-UI endpoint

```python
adk_agent = ADKAgent(
    adk_agent=root_agent,
    app_name="football_a2ui_agent",
    user_id="webapp-user",
    a2ui={"default_catalog_id": "football_catalog"},
)
add_adk_fastapi_endpoint(app, adk_agent, path="/chat")
```

`ag-ui-adk` turns the ADK agent into an endpoint that **streams AG-UI events**
(text deltas, tool calls, UI operations) instead of returning a JSON response.
That is the whole difference with the sibling "lite" repo: no BFF, no
translation step, no chart JSON smuggled inside message text.

`default_catalog_id` is explained under [Failure modes](#failure-modes).

## Frontend side

### `app/api/copilotkit/route.ts` — the runtime

```ts
const runtime = new CopilotRuntime({
  agents: { default: new HttpAgent({ url: ADK_AGUI_URL }) },
  a2ui: { injectA2UITool: true },
});
```

`HttpAgent` talks to `POST /chat` directly. `injectA2UITool` travels to the
Python side in the request's `forwarded_props`, and that is what triggers the
tool injection there.

### `components/Providers.tsx` — one line, two effects

```tsx
<CopilotKitProvider runtimeUrl="/api/copilotkit" a2ui={{ catalog: footballCatalog }}>
```

1. It registers the catalog with the built-in A2UI renderer, so incoming
   operations can be turned into React components.
2. It sends the catalog's **component schemas to the agent** as context
   (`includeSchema` defaults to true).

Both ends must opt in: the runtime injects the tool, the provider supplies the
catalog. Miss either one and nothing renders.

### `components/A2uiCatalog.tsx` — the contract, written for the model

One `Chart` component, five chart types. The zod `.describe()` strings are
**LLM-facing** — they are the schema shipped to the agent:

```ts
export const CATALOG_ID = "football_catalog";

const definitions = {
  Chart: {
    description: "A data visualization backed by ECharts. Pick the chartType …",
    props: z.object({
      chartType: z.enum(["bar", "line", "pie", "radar", "heatmap"])
        .describe("bar|line: rankings/trends. pie: parts of a whole. " +
                  "radar: one entity across several metrics. …"),
      data: z.array(z.record(z.union([z.string(), z.number()])))
        .describe("bar/line/pie: [{\"name\":\"Mbappé\",\"value\":8}, …]. " +
                  "radar: each item is ONE axis …"),
      // xKey, yKeys, title …
    }),
  },
};

export const footballCatalog = createCatalog(definitions, renderers, {
  catalogId: CATALOG_ID,
  includeBasicCatalog: true,
});
```

This is the part people underestimate: **you do not program the choice of chart,
you document it**. The model picks a radar for a head-to-head comparison because
the description says so. Prop descriptions are prompt engineering.

`includeBasicCatalog: true` adds A2UI's primitives (Column, Heading, Text, …) so
the model can compose a real surface around the chart, not just a bare chart.

`renderers` maps each component name to React — here `Chart` → `<EChart>`, which
initialises ECharts on a ref in `useEffect` with a `ResizeObserver`
(`echarts-for-react` lags on React 19, so we use `echarts` directly).

## What actually travels

The agent does not emit our `Chart` props directly. `ag-ui-adk` runs a nested
generation step, then **the host assembles the A2UI operations** and streams them
as nested tool-call events:

```jsonc
{ "createSurface":    { "surfaceId": "…", "catalogId": "football_catalog" } }
{ "updateComponents": { "components": [
    { "id": "root",  "component": { "Column": { "children": ["title", "chart"] } } },
    { "id": "title", "component": { "Heading": { "text": "Top 5 buteurs" } } },
    { "id": "chart", "component": { "Chart": { "chartType": "bar", "data": [ … ] } } }
  ] } }
```

Two rules the processor enforces: every component needs both an `id` and a
`component`, and the root must be a layout component with `id: "root"`.

## Failure modes

Dynamic A2UI is non-deterministic by construction — the model builds the surface.
Two failures showed up repeatedly, and they have different causes.

### `Catalog not found: …/basic_catalog.json`

**Not the model's fault.** The `catalogId` of a new surface is chosen by the
*host*: `ag-ui-adk` infers it from the catalog context, and falls back to the
A2UI **basic catalog URL** when that inference misses. Our frontend only
registers `football_catalog`, so any other id fails to resolve.

Fix: pin it explicitly in `server.py` —
`a2ui={"default_catalog_id": "football_catalog"}`. Prompt instructions cannot fix
this one, since the model never writes that field on this path.

Observed at roughly 1 render in 4 before the fix.

### `Component 'Chart' is missing an 'id'`

The generated component array is malformed. This one *is* on the model, and the
mitigation is the examples in `prompts/a2ui.md`: give a complete, valid component
array per chart type. The model anchors hard on examples — it will reliably
produce only the chart types it has seen written out.

Observed with `gemini-3.8-flash` (2 runs in 5); `gemini-2.5-flash` instead hits
the catalog error. Neither model is clean, which is why the talk demo opens with
the radar question, the most reliable one.

## Dynamic vs static — the trade-off

This repo is **dynamic** A2UI: the LLM decides *when* to render and *what* to
render. That is what makes it impressive on stage (it picks a radar for a
profile, a heatmap for a matrix) and what makes it fragile: every failure above
comes from that freedom.

The counterpart is **static agent-native** A2UI (`a2ui.create_surface()` /
`a2ui.render()` in Python): operations built by deterministic code. No
hallucination, no malformed components — at the cost of the model's autonomy in
choosing the UI.

Rule of thumb: dynamic for exploration and demos, static for anything a user
depends on.

## File map

| File | Role |
|---|---|
| `agent/football_a2ui_agent/agent.py` | `ENABLE_A2UI`, `AGUIToolset()`, prompt order |
| `agent/football_a2ui_agent/prompts/a2ui.md` | how to build a surface, one example per chart type |
| `agent/server.py` | `ADKAgent` + `/chat`, `default_catalog_id` |
| `webapp/app/api/copilotkit/route.ts` | `CopilotRuntime`, `HttpAgent`, `injectA2UITool` |
| `webapp/components/Providers.tsx` | `CopilotKitProvider a2ui={{ catalog }}` |
| `webapp/components/A2uiCatalog.tsx` | catalog id, component definitions, renderers |
| `webapp/components/EChart.tsx` | ECharts rendering, one `buildOption` branch per type |

Adding a chart type means touching three places: the `chartType` enum and its
data-shape description in `A2uiCatalog.tsx`, a `buildOption` branch in
`EChart.tsx`, and an example in `prompts/a2ui.md` — without the example, the
model will not use it.
