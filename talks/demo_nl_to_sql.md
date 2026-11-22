# Démo — talk « Qui a marqué le plus de buts ? Construire un agent IA qui interroge des données en langage naturel »

Talk NL to SQL, donné à DevLille (repo lite, Qatar 2022) puis à **DevFest Paris
(30/11/2026)** sur ce repo : Coupe du monde 2026, fil rouge PSG, graphiques A2UI.
L'autre talk de ce repo, « ADK en action », a son propre déroulé :
[`demo_adk_en_action.md`](demo_adk_en_action.md).

- Slides : `~/my-projects/conferences/devfest_paris/2026/talk_nl_to_sql/talk_adk_nl_sql_devfest_paris_30_11_2026_v2.pptx`
- Données : BigQuery `fifa_world_cup_2026` (5 tables, voir `data/README.md`)
- Prompts NL to SQL : `agent/football_a2ui_agent/prompts/` (`role`, `schema`, `query_workflow`, `business_rules`, `a2ui`)

**Tout tourne en local avec Docker Compose, comme à DevLille. Pendant le talk,
on ne touche à aucun terminal : on passe d'un onglet à l'autre.**

## J-1

```bash
gcloud auth application-default login            # ADC expiré = agent muet, sans erreur
docker compose build                             # images prêtes, le jour J le up est immédiat
docker compose up -d
cd agent && python3 -I tests/a2ui_bench.py -n 15   # banc A2UI : attendu 105/105 (7 questions × 15)
docker compose down
```

Le banc rejoue la vraie requête CopilotKit sur les 7 questions de la démo. À
relancer après tout changement de prompt, de modèle ou de version d'ADK.

## 5 min avant de monter sur scène

```bash
docker ps --format '{{.Names}} {{.Ports}}' | grep -E ':(8080|8000|3000)->'   # rien ne doit occuper ces ports
cd ~/my-projects/blogarticles/adk-a2ui-copilotkit
docker compose down -v       # repart de zéro (efface les volumes)
docker compose up            # lance les 3 services
```

Si un autre projet occupe le 8080 (ex. `adk-conversational-analytics-adk-web-1`) :
`docker stop <nom>`.

Attendre ~30 s, puis poser **une question test** sur `http://localhost:3000` :
« Top 5 des buteurs du tournoi ». Si le graphique s'affiche, c'est prêt.

Onglets ouverts dans l'ordre :

1. `http://localhost:8080` — ADK web (texte, panneau Events)
2. `http://localhost:3000` — webapp CopilotKit + A2UI
3. (option) Console Agent Platform → engine `3830629241939034112` → Playground

## Pendant le talk

| Slides | Ce qu'on montre | Où |
|---|---|---|
| 1-2 | Titre, présentation | slides |
| 3-7 | Le problème, la promesse, la valeur métier, les limites | slides |
| 8-9 | Architecture globale, CI/CD | slides |
| 10-12 | Pourquoi ADK, pourquoi MCP, architecture front | slides |
| **13 — Démo time** | **La démo ci-dessous** | onglets 1 puis 2 |
| 14 | Développer en local avec Gemma | slide seule (la démo Gemma vit dans `football-agent-adk-gemma-dmr`) |
| 15 | System instructions modulaires | (option) éditeur : `prompts/schema.md`, `prompts/business_rules.md` |
| 16-20 | RAG, validation technique et métier, production, à retenir | slides |
| 21-22 | Feedback, merci | slides |

### Démo (slide 13)

**1. ADK web `:8080` — voir le SQL**
« Qui a marqué le plus de buts ? » → réponse en texte. Ouvrir le panneau
**Events** : le LLM appelle `execute_sql_readonly` via MCP ; cliquer l'event
montre la requête SQL générée. Message : « l'agent n'invente pas, il interroge ».

**2. Webapp `:3000` — le même agent dessine sa réponse**
Même agent, servi en AG-UI : le LLM choisit le type de graphique et le construit
(A2UI). Poser les questions dans l'ordre ci-dessous, en s'arrêtant selon le temps.

**3. Le piège** — « Quels sont les xG de Mbappé ? » (voir plus bas).

**4. (option) Playground de l'engine** — même code, même réponse, mais managé.
Fait le lien avec la slide « En production ».

<a id="questions"></a>
## Questions — Coupe du monde 2026, fil rouge PSG

Réponses attendues calculées depuis les données (vérifiées contre la liste FIFA
des buteurs). Les 7 questions de la webapp passent le banc A2UI à 105/105
(12/11/2026).

### Webapp A2UI (`:3000`) — ordre conseillé

| # | Question | Graphique | Réponse attendue |
|---|---|---|---|
| 1 | « Top 5 des buteurs du tournoi » | bar | Mbappé 10, Messi 8, Haaland 7, Bellingham 7, Dembélé 6 (ex æquo avec Kane, départagé aux minutes). ~10 s : la plus sûre pour ouvrir |
| 2 | « Compare Mbappé et Dembélé : buts, passes décisives, buts par 90, minutes, titularisations » | radar | Mbappé 10 / 4 / 1,29 / 698 / 8 — Dembélé 6 / 2 / 0,91 / 596 / 7 |
| 3 | « Quels clubs ont fourni le plus de buts ? » | bar | Real Madrid 22, **PSG 16**, Arsenal 13 → « Paris, 2ᵉ club du Mondial » |
| 4 | « Les joueurs du PSG au Mondial, par sélection, en camembert » | pie | France 5, Portugal 4, puis 1 chacun (Brésil, Maroc, Espagne, Sénégal, Équateur, Corée du Sud, Tunisie) — 16 joueurs |
| 5 | « Top 5 des passeurs décisifs du tournoi » | bar | Olise 7, puis Mbappé, Messi, Brahim Díaz, Bruno Guimarães, Ødegaard à 4 (ex æquo) |
| 6 | « Buts de Mbappé match après match » | line | 2, 2, 0, 2, 1, 1, 0, 2 (Sénégal → Angleterre) |
| 7 | « Heatmap des buts par phase pour la France, l'Espagne, l'Argentine et l'Angleterre » | heatmap | France : 10 en poules, 0 en demie ; Espagne : 1 en finale (buts d'équipe, CSC adverses compris). **15–45 s** : la poser en dernier |

Si le temps est court : 1, 2, 3 puis le piège.

### Questions fun (texte, ADK web ou webapp) — pour interagir avec la salle

- « Quel joueur du PSG est champion du monde ? » → **Fabián Ruiz** (Espagne), le seul.
- « Qui est le plus jeune buteur du tournoi ? » → **Ibrahim Mbaye**, 18 ans, PSG (Sénégal).
- « Quel match a eu le plus de buts ? » → la petite finale **France 4–6 Angleterre** (10 buts).
- « Qui a le plus de buts + passes décisives ? » → Mbappé 14 (10 + 4), Messi 12, puis Dembélé et Bellingham 8.
- « Le joueur du PSG le plus décisif ? » → Dembélé 8 (6 buts + 2 passes), Barcola 4, Hakimi 3.
- « Top 3 des passeurs décisifs du PSG ? » → Hakimi 2, Dembélé 2 (départagés aux minutes), Lee Kang-in 1.
- « Combien de joueurs de Ligue 1 au Mondial ? » → 84 (PSG 16, Nice 8, Lille 8, Strasbourg 7).
- « Comment a fini la France ? » → 4ᵉ : défaite 0–2 contre l'Espagne en demie, puis 4–6 contre l'Angleterre.
- « Qui a gagné la finale ? » → Espagne 1–0 Argentine a.p., Ferran Torres (106ᵉ).

### Le piège à poser exprès

« Quels sont les xG de Mbappé ? » (ou « combien de tirs ? ») → l'agent doit
répondre que le dataset ne contient pas cette stat et proposer buts / passes /
buts par 90. Punchline : « pas de colonne, pas de chiffre inventé ».

### Anecdotes à raconter

- **La qualité de la donnée** : les passes décisives viennent de FBref et ont été
  recoupées avec API-Football (top 20 identique). Le dataset Kaggle le plus
  complet donnait Olise à 8 au lieu de 7 et Dembélé à 5 buts au lieu de 6 : la
  qualité de la donnée d'entrée, c'est la moitié d'un agent « talk to my data ».
- **Modéliser la donnée pour l'agent** : la heatmap « buts par équipe et par
  phase » demandait 2 à 4 requêtes SQL (union domicile/extérieur). Une table
  `team_matches` (une ligne par équipe et par match) la ramène à une requête.
- **Le modèle ne connaît pas 2026** : quand la session MCP tombe, un agent sans
  garde-fou répond de mémoire (un top 5 des passeurs avec De Bruyne dedans). Ici
  il répond « BigQuery indisponible » plutôt que d'inventer.

## Si ça plante

- `A2UI render error: Catalog not found` → reposer la même question.
- `Component 'Chart' is missing an 'id'` → reposer ; défaut connu du modèle,
  réparé par `repair_render_a2ui_args` dans `agent.py`.
- « Je n'arrive pas à interroger BigQuery… » → la session MCP est tombée, le
  garde-fou a joué : reposer la question (et en faire un moment du talk).
- L'agent cite Giroud, Lloris ou des chiffres 2022 → il a répondu de mémoire :
  « vérifie dans la base ».
- Pas de réponse du tout → ADC expiré (`gcloud auth application-default login`).
- Tout est cassé : `docker compose down -v && docker compose up`, de retour en une commande.

Plan B si le réseau lâche : vidéo pré-enregistrée de la démo (ADK web + 3 questions webapp).

## À la fin

```bash
Ctrl+C                 # dans le terminal de compose
docker compose down
```

## Pourquoi c'est sûr

- `adk web` (8080) et le serveur AG-UI (8000) tournent dans des conteneurs
  isolés : chacun a ses propres sessions, aucun conflit.
- La webapp (3000) parle à l'agent par le réseau Docker interne, pas par ton localhost.
- Aucune commande entre les phases : rien à oublier, rien à nettoyer.
- Garde-fous dans `agent.py` : retries MCP, pas de graphique sans requête SQL dans le tour.
