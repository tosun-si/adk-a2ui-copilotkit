# Demo Kit — GDG Paris : « ADK en action : du développement au déploiement d'un agent IA »

20 min. Même agent tout du long : ADK + BigQuery MCP (Agent Registry), Qatar 2022.

- Engine déployé : `football-stats-agent-adk` — `AGENT_ENGINE_ID=5448783803071856640` (europe-west1)
- Console (Playground) : https://console.cloud.google.com/vertex-ai/agents/agent-engines/locations/europe-west1/agent-engines/5448783803071856640/playground?project=gb-poc-373711
- Slides : `uv run --with python-pptx python talks/generate_slides.py` → `talks/slides/talk_gdg_paris_adk.pptx`
- Schéma : `diagrams/adk_agent_platform_archi.excalidraw` (+ `.png` utilisé par la slide)

## J-1 / le matin

```bash
gcloud auth login && gcloud auth application-default login   # ADC expiré = agent muet
./scripts/setup_gcp.sh                                        # APIs + IAM (idempotent)
cd agent && AGENT_ENGINE_ID=5448783803071856640 ./deploy_agent_engine.sh   # update in place, même URL console
```

- Pré-déployer : un déploiement prend plusieurs minutes, **ne jamais le faire en live**, montrer seulement la commande.
- Nettoyer les vieux engines pour une console lisible : `./scripts/cleanup_old_engines.sh` (`--apply`).

## 5 min avant

```bash
docker compose down -v && docker compose up --build
cd agent && AGENT_ENGINE_ID=5448783803071856640 uv run python ../scripts/query_agent_engine.py   # réveille l'engine + crée une trace fraîche
```

Onglets navigateur ouverts dans l'ordre :

1. `http://localhost:8080` — ADK web
2. `http://localhost:3000` — webapp A2UI
3. Console Agent Platform → Agent Engine → l'engine → **Playground** (events + traces)
4. Même engine → **Sessions**
5. Agent Registry → **MCP servers**

> Libérer le port 8080 avant de lancer la stack : `docker stop football-agent-docker-agent-gemma-dmr-football-agent-1`

## Déroulé démo

| # | Où | Quoi montrer | Question type |
|---|---|---|---|
| 1 | ADK web `:8080` | Chat + panneau **Events** : le LLM appelle `execute_sql_readonly` (et parfois `get_table_info`) via MCP. Cliquer un event → la requête SQL générée. | « Qui a marqué le plus de buts ? » |
| 2 | Éditeur | `agent.py` : `LlmAgent` + `AgentRegistry` → toolset MCP (15 lignes utiles). Prompts en `.md`, `tool_filter` read-only. | — |
| 3 | Webapp `:3000` | Même agent en AG-UI : le LLM choisit et construit le graphique (A2UI). Voir les questions ci-dessous. | « Compare Mbappé et Messi » |
| 4 | Terminal | `deploy_agent_engine.sh` : `uv export` → `adk deploy agent_engine --otel_to_cloud`. **Ne pas exécuter**, l'engine est déjà là. | — |
| 5 | Playground | **Même code, même réponse**, mais managé : scale-to-zero, sessions managées, IAM. Events **et** traces sont dans cet onglet. | « Top 5 passeurs de la France » |
| 6 | Traces | Arbre de spans `invoke_agent → call_llm → execute_tool`, SQL dans les attributs, tokens, latence LLM vs BigQuery. Repli : Cloud Trace. | — |
| 7 | Agent Registry | Catalogue des MCP servers managés Google (BigQuery, …) : l'agent les découvre par `displayName`, sans URL en dur. | — |
| 8 | Terminal + éditeur | `agents-cli` : le scaffolding d'un projet ADK par l'assistant de code (voir la rubrique dédiée). | — |
| 9 | IDE | Le même agent en **Java** (builder `LlmAgent.builder()`), et un mot sur Kotlin. | — |

## Questions pour la webapp A2UI (`:3000`)

Ordre conseillé : du plus fiable au plus spectaculaire. Le LLM choisit lui-même le type de graphique ; les ajouts entre parenthèses (« en radar », « en camembert ») servent à l'orienter si besoin.

| # | Question | Graphique attendu | Statut |
|---|---|---|---|
| 1 | « Compare Mbappé et Messi sur buts, passes décisives et dribbles par match » | radar, 2 joueurs superposés | ✅ testé, a marché à chaque essai → **ouvrir avec celle-ci** |
| 2 | « Qui sont les 5 meilleurs buteurs du tournoi ? Montre-moi un graphique. » | bar | ⚠️ testé, 7/9 (le reste : `Catalog not found`) |
| 3 | « Répartition des buts de la France par poste, en camembert » | pie (FW / MF / DF) | non testé |
| 4 | « Buts et passes décisives des 5 meilleurs joueurs de la France » | bar multi-séries (`yKeys` = buts, passes) | non testé |
| 5 | « Heatmap des buts par poste pour l'Argentine, la France, le Maroc et la Croatie » | heatmap (x = poste, y = équipe) | non testé |

Si ça plante :

- `A2UI render error: Catalog not found: …basic_catalog.json` → **reposer la même question**. Punchline : « le LLM construit l'UI lui-même : puissant, mais pas déterministe ». C'est l'argument dynamique vs statique de l'article.
- Le LLM répond « je ne peux pas faire ce graphique » → ajouter le type explicitement (« en radar », « en heatmap »).
- Pas de réponse du tout → ADC expiré (`gcloud auth application-default login`), pas un bug A2UI.

Questions à éviter : les cartons ou les stats par phase ou par match (la table n'a pas ces colonnes), et les courbes « dans le temps » (pas de dimension temporelle, le line chart sera artificiel).

Pont narratif avec ADK web : « même agent, même code, autre runtime ». `server.py` active A2UI (`ENABLE_A2UI`), `adk web` non.

## agents-cli : montrer la commande (étape 8)

[`google/agents-cli`](https://github.com/google/agents-cli) donne à un assistant de code (Claude Code, Codex, …) les skills pour **créer, évaluer, déployer et observer** des agents ADK. Ce n'est pas un concurrent d'ADK : ADK reste le framework, `agents-cli` donne les mains à l'assistant.

### Installé dans ce repo, en scope workspace

```bash
make agents-cli-skills          # = uvx google-agents-cli setup --workspace --agent claude-code
make agents-cli-skills-update   # = agents-cli update --workspace
```

Les 7 skills (`scaffold`, `adk-code`, `deploy`, `eval`, `observability`, `publish`, `workflow`) sont copiées dans **`.claude/skills/`** du repo. La CLI elle-même est un outil isolé (`uv tool`, binaire dans `~/.local/bin`) — **pas** une dépendance du `pyproject.toml` de l'agent : l'y ajouter ajoute 39 paquets au lock et change jusqu'aux versions de production (testé : `opentelemetry-exporter-gcp-trace` disparaissait de l'export).

### Workspace ou global : l'argument du talk

| | `--workspace` | `-g` (global) |
|---|---|---|
| Où | `.claude/skills/` du repo | `~/.claude/skills/` + `~/.agents/skills/` |
| Portée | ce projet uniquement | toutes tes sessions |
| Cohabitation | les skills Google restent dans le contexte du repo ADK | elles se mélangent à ton catalogue perso/équipe |

Le message : quand on a **déjà son propre catalogue de skills** (conventions maison, standards d'équipe), on ne veut pas que chaque outil déverse les siennes dans le HOME. Le scope workspace garde les skills Google là où elles servent — le repo ADK — et laisse le global aux conventions qu'on assume pour tous ses projets. Les noms sont préfixés `google-agents-cli-*`, donc aucun conflit ; c'est un choix de périmètre, pas de collision.

### À montrer en live (2 min max)

```bash
cd ~/my-projects/blogarticles/agents-cli-demos      # dossier dédié aux générations
agents-cli --help                                   # create · playground · run · eval · deploy · publish
agents-cli create demo-agent --adk --skip-checks --auto-approve
```

Les flags comptent sur scène : `--adk` = quickstart (ADK + Agent Runtime + prototype, aucune question), `--skip-checks` = pas d'appel GCP de vérification, `--auto-approve` = zéro prompt. **Testé : 2,7 s, sans auth ni réseau bloquant.**

Ce qui est généré :

```
demo-agent/
├── app/agent.py              un agent ADK + un tool d'exemple (météo)
├── app/fast_api_app.py       le serveur FastAPI
├── app/app_utils/            adaptateur Agent Runtime, A2A, services
├── deployment/terraform/     IAM, APIs, service, storage, telemetry.tf
├── Dockerfile
├── pyproject.toml
├── GEMINI.md                 les instructions pour l'assistant de code
├── agents-cli-manifest.yaml
└── README.md
```

Deux points à dire : le Terraform inclut l'**observabilité** (`telemetry.tf` + schéma BigQuery des logs GenAI), et le modèle par défaut du template est **`gemini-3.8-flash`**. L'agent d'exemple est un agent météo : la structure est générée, le métier reste le tien.

```bash
agents-cli info                      # config du projet, chemins, version de la CLI
# agents-cli deploy                  # NE PAS lancer : plusieurs minutes
```

Vérifié avec la CLI **1.6.1** installée ici. Autres verbes utiles à citer :
`playground` (playground local), `eval run` (évaluation notée), `scaffold enhance .`
(ajoute CI/CD et déploiement à un projet existant), `publish` (Gemini Enterprise).

Puis ouvrir le projet généré dans l'éditeur : même structure que celle qu'on vient de coder à la main (agent, prompts, tests, CI/CD, observabilité). Punchline : « tout ce qu'on a écrit ensemble, l'assistant sait le générer — reste à savoir ce qu'on veut, et à le relire ».

Si tu es court en temps : ne rien lancer, montrer juste la slide et la commande.

## Modèle : pourquoi on reste en 2.5-flash

`gemini-3.8-flash` marche (testé le 21/09), mais **uniquement via l'endpoint
`global`** — 404 en `europe-west1`. Et sur A2UI il est moins fiable : 2 échecs
sur 5 (`Component 'Chart' is missing an 'id'`) contre 2 sur 9 en 2.5
(`Catalog not found`). Le radar passe dans les deux cas.

Donc : **2.5-flash pour le talk**. À dire à l'oral : « le template d'agents-cli
génère déjà du 3.8, qui n'est servi que sur l'endpoint global ». Pour basculer
malgré tout :

```bash
MODEL=gemini-3.8-flash MODEL_LOCATION=global docker compose up --build
```

## Autres idées à montrer sur Agent Platform (si le temps le permet)

- **Observability / Dashboard** de l'engine : requêtes, latence, erreurs, tokens. C'est le « rendre exploitable » de l'abstract.
- **Logs corrélés** : depuis un span, sauter aux logs Cloud Logging de la même requête.
- **Update in place** (`--agent_engine_id`) : même resource, même URL, les sessions survivent. C'est le cycle de vie d'un agent en prod.
- **Identité / IAM** : l'agent tourne avec son propre service agent, et les rôles (`mcp.toolUser`, `bigquery.jobUser`…) bornent ce qu'il peut faire. Message sécurité simple et fort.
- **Memory Bank** (à mentionner, pas en démo) : `async_add_session_to_memory` / `async_search_memory` sont déjà exposés par l'engine ; ajouter `PreloadMemoryTool` suffit pour une mémoire long terme.
- Vérifier avant le talk si l'engine déployé apparaît aussi dans **Agent Registry** (agents), ce qui ferait une belle boucle avec l'écran des MCP servers.

## Traces vides sur Agent Engine : checklist

Le problème des talks précédents. Dans l'ordre :

1. **API `telemetry.googleapis.com` activée ?** ADK 2.6 exporte les spans en OTLP vers la Telemetry API, pas vers l'API Cloud Trace historique. Désactivée → spans perdus sans erreur. (`setup_gcp.sh` l'active.)
2. **Rôle `roles/telemetry.tracesWriter`** sur `service-<PROJECT_NUMBER>@gcp-sa-aiplatform-re.iam.gserviceaccount.com`.
3. **`--otel_to_cloud`** passé au deploy (fait par le script) → l'engine tourne `adk api_server --otel_to_cloud`.
4. **`opentelemetry-exporter-otlp-proto-http`** dans `requirements.txt` (vient de `pyproject.toml`) ; sinon l'export no-op silencieusement.
5. **Chemin ABSOLU** de l'agent au deploy : sinon le `.env` est ignoré.
6. Spans présents mais vides (pas de SQL, pas de prompt) → `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=true` dans `.env` (`adk deploy --otel_to_cloud` le force à `false` s'il est absent).
7. Vérifier les env vars réellement appliquées à l'engine : console → engine → Deployment details, ou le log de `adk deploy` (`env_vars`).
8. Laisser 1–2 min de latence d'ingestion avant de conclure que c'est vide.

## Questions testées sur l'engine (18/09)

- « Qui sont les 3 meilleurs buteurs de la France ? » → Mbappe 8, Giroud 4, Tchouaméni 1
- « Combien de buts pour Mbappé ? » → 8 (règle accents dans `query_workflow.md`)
- « Top 5 passeurs du tournoi » → Perisic, B. Fernandes, Kane, Messi, Griezmann (3 chacun)

## Recovery

```bash
docker compose down -v && docker compose up --build      # stack locale propre
lsof -ti :8080 -ti :8000 -ti :3000 | xargs kill -9        # ports occupés
gcloud auth application-default login                    # agent qui ne répond rien
```

Plan B si le réseau ou l'engine lâche : vidéo pré-enregistrée des étapes 4 à 6 et de la webapp A2UI.
