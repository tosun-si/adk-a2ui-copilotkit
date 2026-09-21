"""Slide-by-slide content for the GDG Paris talk (20 min).

« ADK en action : du développement au déploiement d'un agent IA »

Déroulé : ADK → tools/MCP → code → démo locale (adk web) → démo A2UI →
déploiement → Playground + traces → agents-cli → Java/Kotlin → conclusion.
"""

FOOTER_TEXT = "ADK en action · GDG Paris"

SLIDES = [
    {
        "type": "title",
        "title": "ADK en action",
        "subtitle": "Du développement au déploiement d'un agent IA sur Google Cloud",
        "footer": "Mazlum Tosun · GroupBees · GDG Paris 2026",
        "notes": (
            "Bonjour à tous. 20 minutes pour passer d'une idée d'agent à un agent "
            "qui tourne vraiment sur Google Cloud : on code avec ADK, on le lance "
            "en local, on le déploie, et on regarde ce qui se passe en production."
        ),
    },
    {
        "type": "bullets",
        "title": "Créer un agent ≠ l'exploiter",
        "bullets": [
            "Un prototype d'agent : quelques lignes, ça marche sur le laptop",
            "En prod : qui l'héberge ? où sont les conversations ?",
            "Que fait-il exactement quand il se trompe ?",
            "Et qu'a-t-il le droit de faire sur mes données ?",
        ],
        "kicker": "ADK répond au « créer ». Agent Platform répond au « exploiter ».",
        "notes": (
            "Tout le monde a déjà bricolé un agent qui marche sur son poste. Les "
            "vraies questions arrivent après : hébergement, sessions, debug, "
            "sécurité. C'est le fil rouge des 20 minutes."
        ),
    },
    {
        "type": "bullets",
        "title": "ADK — Agent Development Kit",
        "image": "bee.png",
        "bullets": [
            "Le framework d'agents de Google, open source",
            "Code-first : un agent = du code versionné et testable",
            "Python, Java, Go, TypeScript",
            "Outillage inclus : adk web, adk eval, adk deploy",
            "Optimisé Gemini, mais model-agnostic",
        ],
        "notes": (
            "ADK, c'est le framework que Google utilise pour ses propres agents. "
            "Point important : c'est du code, pas du no-code. Donc Git, revue, "
            "tests, CI/CD. Et la CLI couvre tout le cycle de vie."
        ),
    },
    {
        "type": "bullets",
        "title": "Tools & MCP : le découplage",
        "image": "usbc.png",
        "bullets": [
            "Un agent seul ne sait rien faire : ses tools font le travail",
            "MCP = l'USB-C des agents : un protocole, tous les outils",
            "Serveurs MCP managés par Google, découverts via Agent Registry",
            "Zéro client BigQuery à coder, zéro URL en dur",
            "Découplé aussi du modèle et du runtime",
        ],
        "kicker": "Le même agent tourne en local, sur Agent Platform ou sur Cloud Run.",
        "notes": (
            "MCP, c'est l'USB-C des agents : avant, un connecteur par outil ; "
            "maintenant un protocole unique. Google héberge le serveur MCP "
            "BigQuery, je ne code aucun connecteur. Et l'agent le découvre par "
            "son nom dans Agent Registry, sans URL en dur."
        ),
    },
    {
        "type": "image",
        "title": "L'architecture",
        "image_path": "../diagrams/adk_agent_platform_archi.png",
        "image_placeholder": "diagrams/adk_agent_platform_archi.png",
        "notes": (
            "À gauche le local : uv et Docker Compose, l'agent dans adk web et la "
            "webapp. À droite le même code sur Agent Runtime, l'ex-Agent Engine. "
            "Gemini pour le modèle, Agent Registry pour le serveur MCP BigQuery, "
            "et la télémétrie qui part en OpenTelemetry vers Cloud Observability."
        ),
    },
    {
        "type": "code",
        "title": "L'agent : une vingtaine de lignes",
        "code": (
            "from google.adk.agents import LlmAgent\n"
            "from google.adk.integrations.agent_registry import AgentRegistry\n"
            "\n"
            "registry = AgentRegistry(project_id=PROJECT_ID, location=\"global\")\n"
            "\n"
            "# Découverte du serveur MCP BigQuery managé par Google\n"
            "server = find_by_display_name(registry, \"bigquery.googleapis.com\")\n"
            "toolset = registry.get_mcp_toolset(server)\n"
            "\n"
            "# Moindre privilège : le LLM ne voit que les outils en lecture\n"
            "toolset.tool_filter = [\"get_table_info\", \"execute_sql_readonly\", ...]\n"
            "\n"
            "root_agent = LlmAgent(\n"
            "    model=\"gemini-2.5-flash\",\n"
            "    name=\"football_stats_agent\",\n"
            "    instruction=load_prompts(\"prompts/*.md\"),\n"
            "    tools=[toolset],\n"
            ")"
        ),
        "kicker": "La vraie barrière reste l'IAM : bigquery.dataViewer, bigquery.jobUser.",
        "notes": (
            "Voilà tout l'agent. Un modèle, des instructions, des tools. Les "
            "instructions sont dans des fichiers Markdown, relisibles par des "
            "non-développeurs. Le filtre d'outils, c'est du confort : la vraie "
            "barrière, c'est l'IAM."
        ),
    },
    {
        "type": "demo",
        "title": "Le dev local : uv, Docker, adk web",
        "steps": [
            "docker compose up  →  adk web sur :8080",
            "« Qui sont les 3 meilleurs buteurs de la France ? »",
            "Panneau Events : l'appel MCP et le SQL généré",
            "Trace locale : temps LLM vs temps BigQuery",
        ],
        "notes": (
            "Je montre uv et le Dockerfile en 10 secondes, puis adk web. Je pose "
            "la question, et surtout j'ouvre le panneau Events : le choix de "
            "l'outil, le SQL écrit par le modèle, le résultat BigQuery. C'est "
            "l'outil de debug du quotidien."
        ),
    },
    {
        "type": "demo",
        "title": "Le même agent pilote l'interface (A2UI)",
        "steps": [
            "Webapp Next.js + CopilotKit  →  :3000",
            "« Compare Mbappé et Messi sur buts, passes et dribbles »",
            "Le LLM choisit le type de graphique et le construit",
            "Même agent, même code : seul le runtime change",
        ],
        "notes": (
            "Le même agent, exposé cette fois en AG-UI. Le modèle ne renvoie pas "
            "du texte mais des composants d'interface : il choisit un radar pour "
            "une comparaison. C'est puissant, et non déterministe : si ça rate, "
            "je repose la question et j'en fais un point du talk."
        ),
    },
    {
        "type": "code",
        "title": "Déployer : une commande",
        "code": (
            "# Dépendances : pyproject.toml reste la source de vérité\n"
            "uv export --no-default-groups --no-hashes \\\n"
            "  -o football_agent/requirements.txt\n"
            "\n"
            "# Déploiement sur Agent Runtime (ex-Agent Engine)\n"
            "adk deploy agent_engine \\\n"
            "  --project gb-poc-373711 --region europe-west1 \\\n"
            "  --display_name football-stats-agent-adk \\\n"
            "  --otel_to_cloud \\\n"
            "  --agent_engine_id $AGENT_ENGINE_ID \\\n"
            "  \"$(pwd)/football_agent\"        # chemin ABSOLU"
        ),
        "kicker": "--otel_to_cloud : les traces. --agent_engine_id : mise à jour sur place.",
        "notes": (
            "Une commande. Trois détails qui comptent : le requirements généré "
            "par uv pour garder les extras ADK, --otel_to_cloud pour la "
            "télémétrie, et --agent_engine_id pour redéployer sur la même "
            "ressource sans perdre les sessions. Je ne le lance pas en live."
        ),
    },
    {
        "type": "demo",
        "title": "Agent Platform : Playground, traces, sessions",
        "steps": [
            "Playground : même agent, même réponse, en managé",
            "Traces : invoke_agent → LLM → tool MCP, avec le SQL",
            "Tokens et latence par étape (OpenTelemetry → Cloud Trace)",
            "Sessions persistées, sans une ligne de code",
        ],
        "notes": (
            "Je pose la question dans le Playground, puis j'ouvre la trace de "
            "cette question précise : l'arbre de spans, la latence de chaque "
            "étape, le SQL dans les attributs, les tokens. Puis l'onglet "
            "Sessions : l'historique est géré par la plateforme."
        ),
    },
    {
        "type": "bullets",
        "title": "agents-cli : l'agent qui construit l'agent",
        "bullets": [
            "uvx google-agents-cli setup — des skills pour Claude Code & co.",
            "agents-cli create : scaffolding d'un projet ADK complet",
            "agents-cli run / eval run : exécution et évaluation notée",
            "agents-cli deploy : déploiement sur Google Cloud",
            "CI/CD et observabilité générés avec le projet",
        ],
        "kicker": "ADK reste le framework ; agents-cli donne les mains à votre assistant de code.",
        "notes": (
            "Dernière brique : agents-cli. Ce n'est pas un concurrent d'ADK, "
            "c'est un jeu de skills qui permet à un assistant de code de créer, "
            "évaluer et déployer des agents ADK de bout en bout, avec le CI/CD "
            "et l'observabilité. Si je suis court en temps, je le dis sans le "
            "faire en live."
        ),
    },
    {
        "type": "demo",
        "title": "agents-cli en action",
        "steps": [
            "agents-cli create  →  un projet ADK prêt à déployer",
            "Le code généré : même structure que le nôtre",
            "agents-cli deploy  →  Agent Platform",
            "(l'agent est déjà déployé : on regarde le résultat)",
        ],
        "notes": (
            "Démo courte et sans risque : le scaffolding en live, le déploiement "
            "seulement montré. Si le temps manque, je saute cette démo et je dis "
            "simplement que tout ce qu'on vient de coder peut être généré."
        ),
    },
    {
        "type": "code",
        "title": "Et en Java (et en Kotlin)",
        "code": (
            "import com.google.adk.agents.LlmAgent;\n"
            "\n"
            "LlmAgent rootAgent = LlmAgent.builder()\n"
            "    .name(\"football_stats_agent\")\n"
            "    .description(\"Stats de la Coupe du monde 2022\")\n"
            "    .model(\"gemini-2.5-flash\")\n"
            "    .instruction(systemInstruction)\n"
            "    .tools(bigQueryMcpToolset)   // même serveur MCP managé\n"
            "    .build();"
        ),
        "kicker": "Mêmes concepts, API fluent. Et ça s'utilise tel quel depuis Kotlin.",
        "notes": (
            "Les mêmes concepts existent en Java : un builder au lieu du "
            "constructeur Python. Je montre le vrai code dans l'IDE quelques "
            "secondes. Et comme c'est de la JVM, ça s'utilise directement "
            "depuis Kotlin."
        ),
    },
    {
        "type": "takeaways",
        "title": "À retenir",
        "items": [
            ("Un agent, c'est du code",
             "ADK : versionné, testé, débuggé dans adk web"),
            ("Les outils, on les découvre",
             "MCP managé + Agent Registry, bornés par IAM"),
            ("La plateforme fait l'exploitation",
             "runtime, sessions, traces : une commande adk deploy"),
        ],
        "notes": (
            "Trois choses à retenir. Un agent c'est du code. Les outils se "
            "découvrent au lieu de se coder. Et la plateforme apporte tout ce "
            "qui rend l'agent exploitable."
        ),
    },
    {
        "type": "end",
        "title": "Merci !",
        "lines": [
            "Questions ?",
            "Mazlum Tosun — GroupBees",
            "Le code de la démo : agent ADK + BigQuery MCP + Agent Platform",
        ],
        "notes": "Merci, place aux questions.",
    },
]
