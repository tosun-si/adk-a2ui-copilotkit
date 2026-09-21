# Demo repo commands — `make` with no target prints this list.
# Kept dependency-free on purpose: anyone who clones the repo can run it.

AGENT_ENGINE_ID ?= 5448783803071856640
QUESTION        ?= Qui sont les 3 meilleurs buteurs de la France ?

.DEFAULT_GOAL := help
.PHONY: help up down agents-cli-skills agents-cli-skills-update deploy ask slides

help:  ## Show this help
	@grep -E '^[a-z][a-z0-9-]*:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-26s\033[0m %s\n", $$1, $$2}'

up:  ## Start the full local stack (adk web :8080, agent :8000, webapp :3000)
	docker compose up --build

down:  ## Stop the local stack and wipe volumes
	docker compose down -v

agents-cli-skills:  ## Install the agents-cli skills in THIS repo (.claude/skills, workspace scope)
	uvx google-agents-cli setup --workspace --agent claude-code

agents-cli-skills-update:  ## Update the agents-cli skills of this repo
	agents-cli update --workspace

deploy:  ## Deploy/update the agent on Agent Engine (takes minutes — never live)
	cd agent && AGENT_ENGINE_ID=$(AGENT_ENGINE_ID) ./deploy_agent_engine.sh

ask:  ## Ask the deployed agent a question (warms it up before the talk)
	cd agent && AGENT_ENGINE_ID=$(AGENT_ENGINE_ID) uv run python ../scripts/query_agent_engine.py "$(QUESTION)"

slides:  ## Regenerate the talk deck from talks/slides_content.py
	uv run --with python-pptx python talks/generate_slides.py
