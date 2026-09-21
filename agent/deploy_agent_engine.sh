#!/bin/bash
# Deploy (or update in place) the football agent on Agent Engine (Agent Platform).
#
# Usage:
#   ./deploy_agent_engine.sh                        # create a new engine
#   AGENT_ENGINE_ID=1234567890 ./deploy_agent_engine.sh   # update in place (same id/URL)
#
# Prefer the in-place update once the engine exists: the console URL, sessions
# and traces stay on the same resource — handy for a live demo.
set -euo pipefail

cd "$(dirname "$0")"

PROJECT_ID="${GCP_PROJECT_ID:-gb-poc-373711}"
REGION="${LOCATION:-europe-west1}"
DISPLAY_NAME="${DISPLAY_NAME:-football-stats-agent-adk}"
DESCRIPTION="Qatar 2022 World Cup stats agent — ADK + BigQuery MCP (Agent Registry)"
AGENT_DIR="football_a2ui_agent"
REQUIREMENTS_FILE="${AGENT_DIR}/requirements.txt"

# requirements.txt MUST live in the agent folder (ADK 2.6 ignores
# --requirements_file). Generated from pyproject.toml (single source of truth),
# extras included. `--no-default-groups` drops the local-only groups (dev, agui:
# ag-ui-adk is not needed on Agent Engine). Without an explicit file, adk deploy
# writes a bare `google-adk[a2a]` and the engine fails at startup on the
# missing extras (mcp, agent-identity, otel exporters).
trap 'rm -f "${REQUIREMENTS_FILE}"' EXIT
echo "--- Generating ${REQUIREMENTS_FILE} ---"
uv export --no-default-groups --no-hashes --no-emit-project -o "${REQUIREMENTS_FILE}" >/dev/null

UPDATE_ARGS=()
if [[ -n "${AGENT_ENGINE_ID:-}" ]]; then
  echo "--- Updating engine ${AGENT_ENGINE_ID} in place ---"
  UPDATE_ARGS=(--agent_engine_id "${AGENT_ENGINE_ID}")
else
  echo "--- Creating a new engine ---"
fi

echo "Project: ${PROJECT_ID} | Region: ${REGION} | Display name: ${DISPLAY_NAME}"

# - ABSOLUTE agent path: adk deploy chdir()s to dirname(agent) — a relative
#   path gives dirname "" and the .env is silently skipped (no env vars → no
#   telemetry).
# - --otel_to_cloud: the engine runs `adk api_server --otel_to_cloud` → traces,
#   logs and metrics to Cloud Observability (Traces tab of the engine).
uv run adk deploy agent_engine \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --display_name "${DISPLAY_NAME}" \
  --description "${DESCRIPTION}" \
  --otel_to_cloud \
  ${UPDATE_ARGS[@]+"${UPDATE_ARGS[@]}"} \
  "$(pwd)/${AGENT_DIR}"

echo "--- Done. Export the engine id for the next runs: ---"
echo "    export AGENT_ENGINE_ID=<id printed above>"
