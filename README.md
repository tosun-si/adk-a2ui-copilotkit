# adk-a2ui-copilotkit

Native **A2UI** (agent-driven generative UI) with **Google ADK** + **CopilotKit**.

Same use case as the previous article — a Qatar 2022 FIFA World Cup stats agent
that queries BigQuery through MCP (via Agent Registry) — but here the agent
**drives the UI itself** through Google's A2UI protocol, instead of tunneling a
chart JSON blob through a BFF.

> Companion to `football-agent-adk-copilotkit` (the "CopilotKit lite" variant).
> Previous article: _<link to the MCP/ADK/Cloud Run article>_.

## What's different from the lite repo

| | lite repo | this repo |
|---|---|---|
| Transport | `adk api_server` `/run` HTTP + BFF | **native AG-UI endpoint** (`ag-ui-adk`) |
| Who builds the UI | BFF translates a `chart` fence | **the LLM** (dynamic A2UI, `render_a2ui`) |
| Chart spec | proprietary JSON in the message text | A2UI declarative surface (catalog components) |
| Frontend | CopilotKit chat + `chartTagRenderers` | CopilotKit v2 + A2UI catalog renderer |

The agent code is the **same BigQuery MCP agent**, minus `visualization.md`: in
dynamic A2UI you don't prompt the model to emit chart JSON — the runtime injects
a `render_a2ui` tool and the frontend catalog's component descriptions guide it.

## Architecture

```
ADK agent (BigQuery MCP via Agent Registry)
  └─ wrapped by ag-ui-adk → native AG-UI endpoint  POST /chat   (agent/server.py)
        ▼ AG-UI event stream
CopilotRuntime { agents: { default: HttpAgent(/chat) }, a2ui: { injectA2UITool: true } }
        ▼
<CopilotKitProvider a2ui={{ catalog }}> + <CopilotChat/>   (catalog = basic + Recharts Chart)
```

## Docs

- [`docs/a2ui.md`](docs/a2ui.md) — how A2UI works here: the Python side
  (`AGUIToolset`, `ADKAgent`), the frontend side (catalog, renderers), what
  travels between them, and the two failure modes with their causes.
- [`talks/DEMO_KIT.md`](talks/DEMO_KIT.md) — talk demo flow and recovery.

## Commands

`make` lists everything (no dependency beyond make itself):

| Target | What it does |
|---|---|
| `make up` / `make down` | the local stack (adk web :8080, agent :8000, webapp :3000) |
| `make agents-cli-skills` | install the agents-cli skills in this repo (workspace scope) |
| `make agents-cli-skills-update` | update them |
| `make deploy` | deploy/update the agent on Agent Engine |
| `make ask` | ask the deployed agent a question (warm-up before a demo) |
| `make slides` | regenerate the talk deck |

`.envrc.example` → copy to `.envrc` (gitignored) + `direnv allow`. It exports the
GCP variables and prints a hint when the agents-cli skills are missing — it never
installs anything by itself.

## Run locally

Needs GCP credentials (Agent Registry + BigQuery), same project as the lite repo.
Run `gcloud auth application-default login` once if you haven't.

### Docker Compose (canonical — one command)

```bash
docker compose up --build
```

Starts `adk-web` (native ADK dev UI on :8080), `agent` (AG-UI endpoint on
:8000) + `webapp` (:3000). Your local Application Default Credentials are
mounted read-only into the agent containers. Open http://localhost:3000 (A2UI)
or http://localhost:8080 (ADK web, plain text — A2UI is only wired for the
AG-UI runtime, see `ENABLE_A2UI` in `agent.py`).

### Outside Docker (per-component iteration)

**1. Agent (AG-UI endpoint on :8000)**

```bash
cd agent
uv sync
uv run uvicorn server:app --host 0.0.0.0 --port 8000
# → POST /chat streams AG-UI events
```

**2. Webapp (Next.js on :3000)**

```bash
cd webapp
npm install
ADK_AGUI_URL=http://localhost:8000/chat npm run dev
```

Open http://localhost:3000 and ask e.g. _"Qui sont les 5 meilleurs buteurs ?"_ —
the LLM should call `render_a2ui` and an A2UI chart renders inline.

## Deploy to Agent Engine (Agent Platform)

The same agent (A2UI off) deploys to Agent Engine with telemetry on:

```bash
./scripts/setup_gcp.sh                                   # once: APIs + IAM for the AE service agent
cd agent
./deploy_agent_engine.sh                                 # create
AGENT_ENGINE_ID=<id> ./deploy_agent_engine.sh            # update in place
AGENT_ENGINE_ID=<id> uv run python ../scripts/query_agent_engine.py "Top 5 buteurs ?"
```

Then use the Playground / Traces / Sessions tabs of the engine in the console.
Empty Traces tab → see the checklist in `talks/DEMO_KIT.md`.

## agents-cli (skills Google, installées dans le repo)

[`google/agents-cli`](https://github.com/google/agents-cli) donne à un assistant
de code (Claude Code, Codex, …) les skills pour créer, évaluer et déployer des
agents ADK de bout en bout. Ce n'est pas un concurrent d'ADK : c'est la couche
qui pilote ADK depuis l'assistant.

Installé ici en **scope workspace**, pour ne rien poser dans le HOME :

```bash
uvx google-agents-cli setup --workspace --agent claude-code
```

Ce que ça fait :

- `uv tool install google-agents-cli` → la CLI `agents-cli` (globale, dans
  `~/.local/bin`) ;
- `npx -y skills@1.5.9 add https://github.com/google/agents-cli -y --agent claude-code`
  → les 7 skills copiées dans **`.claude/skills/`** du repo (pas de lien
  symbolique, pas de `~/.claude/skills` touché).

Les skills : `google-agents-cli-scaffold`, `-adk-code`, `-deploy`, `-eval`,
`-observability`, `-publish`, `-workflow`. Claude Code les charge
automatiquement dans une session ouverte **sur ce repo** — elles n'existent pas
ailleurs.

`.claude/skills/` est gitignoré (copies vendorées) : pour les réinstaller,
relance la commande ci-dessus. Les commandes principales de la CLI :

```bash
agents-cli create <name>      # scaffolding d'un projet ADK
agents-cli playground         # playground local
agents-cli run "<prompt>"     # exécution non interactive
agents-cli eval run           # évaluation notée
agents-cli scaffold enhance . # ajoute CI/CD + déploiement à un projet existant
agents-cli deploy             # déploiement sur Google Cloud
agents-cli publish            # publication (Gemini Enterprise)
```

Version installée : **1.6.1** (21/09/2026). Les skills viennent de la branche
`main` du repo Google, donc non figées : `uv tool install google-agents-cli==1.6.1`
pour épingler la CLI.

Pour désinstaller du repo : `rm -rf .claude/skills` (et
`uv tool uninstall google-agents-cli` pour la CLI).

## Status

- [x] Agent ported + exposed as native AG-UI endpoint (`ag-ui-adk`)
- [x] Webapp: CopilotKit v2 + dynamic A2UI + declarative Recharts catalog
- [x] Both build clean
- [x] Live end-to-end run — bar, line and pie charts render via the LLM-driven `render_a2ui`
- [ ] (later) static agent-native variant (`a2ui.create_surface()`/`render()`) for the reliability comparison

## Gotchas hit (article material)

1. **zod v3 vs v4** — CopilotKit 1.57.3 needs zod v3; a fresh install drifts to v4 and breaks `createCatalog`. Pin `zod@^3.25`.
2. **`@ag-ui/client` version** — `HttpAgent` must match the version `@copilotkit/runtime` expects (0.0.53 for 1.57.3), else `AbstractAgent` type mismatch (`pendingInterrupts`).
3. **Catalog id must match what the LLM emits** — the A2UI message processor resolves surfaces by exact id. The LLM emits the basic-catalog id, so registering a custom `"football"` id fails with `Catalog not found`. Alias the (superset) catalog to `basicCatalog.id`.
4. **Malformed flat components** — in dynamic mode the LLM hand-builds the flat A2UI component array and gets it wrong (`Component 'undefined' is missing an 'id'`) unless given a concrete example in the system prompt. This is the core dynamic-vs-static trade-off.
