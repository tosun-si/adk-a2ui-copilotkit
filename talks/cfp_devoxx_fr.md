# Soumission CFP — Devoxx France

Talk NL to SQL (même talk que DevLille 2026 et DevFest Paris 2026, déroulé de
la démo : [`demo_nl_to_sql.md`](demo_nl_to_sql.md)).

Track : AI & Agentic Systems. Tous les champs sont en **texte brut** : pas de
gras, pas de backticks, pas de tirets longs, pas d'emoji.

Choix de positionnement : l'abstract reste centré sur le NL to SQL, BigQuery et
Google Cloud ne sont que le cadre de la démo. Conversational Analytics n'est
pas dans l'abstract (trop « produit GCP » pour Devoxx) ; il peut rester une
slide de comparaison dans le talk.

À faire avant le talk : l'abstract promet des golden datasets **en CI**. Le
golden dataset existe (`agent/golden_dataset/`, `make golden`) mais ne tourne
pas encore en CI.

## Titre

```
Qui a marqué le plus de buts ? Construire un agent IA pour parler à vos données
```

## Abstract (1 200 caractères max)

1 092 caractères.

```
Permettre aux équipes métier d'interroger leurs données en langage naturel, c'est une belle promesse. On pourrait croire qu'un LLM qui écrit du SQL suffit. En vrai, il se trompe de colonne, ignore les règles métier et invente des chiffres quand la donnée n'existe pas.

Dans ce talk, je construis un agent de statistiques sur la Coupe du monde 2026 : il répond en langage naturel, génère et exécute le SQL, puis affiche le bon graphique à la demande.

On verra comment le construire avec Agent Development Kit (ADK) et MCP : décrire le schéma, encoder les règles métier dans des instructions modulaires, et empêcher l'agent de répondre de mémoire. L'agent pilote aussi ses graphiques lui-même, avec les protocoles ouverts AG-UI et A2UI.

Puis on attaquera les défis de la production : mesurer la fiabilité avec des golden datasets en CI, observer l'agent, détecter les hallucinations et suivre les coûts.

La démo tourne sur BigQuery et Google Cloud, mais ce n'est qu'un exemple : les patterns s'appliquent à n'importe quel projet "talk to my data", quelle que soit votre base ou votre cloud.
```

## Elevator pitch (« Why should this talk be selected? », 1 000 caractères max)

860 caractères.

```
Je travaille sur des projets data pour plusieurs clients, et le "talk to my data" y est très demandé : leurs utilisateurs métier veulent accéder plus facilement à la donnée. Ce talk partage ce que j'ai appris en le construisant, sans prétendre avoir LA solution.

Je l'ai donné à DevLille 2026 dans le grand amphi, avec de très bons retours et beaucoup d'échanges avec le public après le talk. Les retours sont sur OpenFeedback : https://openfeedback.io/devlille-2026/2026-06-11/d73fa080-f6de-4171-9099-178f27e9f082

La démo est en live. On pose des questions à l'agent, on regarde le SQL qu'il génère, il dessine ses graphiques, et on le piège sur une stat qui n'existe pas pour voir s'il invente. Je montre aussi ce qui casse, et comment on le mesure avec des golden datasets.

Tout le code est open source sur https://github.com/tosun-si/adk-a2ui-copilotkit
```

## Notes (« Any additional requirements, alternative session formats… »)

```
Je présente seul. Un micro casque serait idéal, car j'alterne entre les slides et la démo.

La démo est en live depuis mon laptop : sortie HDMI ou USB-C, et un accès internet stable. Je l'ai déjà jouée sur scène à DevLille, je suis serein là-dessus. Si le Wi-Fi de la salle lâche, je basculerai sur un partage de connexion 5G.

Format visé : conférence de 45 minutes. Le talk peut aussi tenir en 30 minutes, en gardant la démo et en resserrant la partie production.

Le talk est aussi au programme du DevFest Paris 2026 : la version Devoxx intégrera ce que j'y aurai appris.

Proposé en AI & Agentic Systems, mais le talk parle aussi d'accès à la donnée pour les métiers : il pourrait aussi aller dans un track Data si ça vous arrange pour le programme.
```
