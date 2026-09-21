#!/bin/bash
# One-shot, idempotent GCP setup for the Agent Engine deploy + observability.
#
# Run once before the first deploy, and again if the Traces tab stays empty.
# Needs: roles/serviceusage.serviceUsageAdmin + roles/resourcemanager.projectIamAdmin.
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-gb-poc-373711}"
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')

# Agent Engine runtime identity (Reasoning Engine service agent). It only exists
# once Agent Engine has been used once in the project — if the IAM binding
# fails with "does not exist", deploy once, then re-run this script.
AE_SA="service-${PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"

echo "--- Enabling APIs on ${PROJECT_ID} ---"
gcloud services enable \
  aiplatform.googleapis.com \
  agentregistry.googleapis.com \
  bigquery.googleapis.com \
  telemetry.googleapis.com \
  cloudtrace.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  cloudresourcemanager.googleapis.com \
  --project "${PROJECT_ID}"
# telemetry.googleapis.com is the one that matters for traces: `--otel_to_cloud`
# exports spans over OTLP to the Telemetry API, not the legacy Cloud Trace API.
# Disabled → spans are dropped, the Traces tab stays empty, no error surfaced.

ROLES=(
  roles/aiplatform.user            # Gemini + Agent Engine sessions/memory
  roles/agentregistry.viewer       # discover the BigQuery MCP server
  roles/mcp.toolUser               # call the MCP tools
  roles/bigquery.dataViewer        # read the dataset
  roles/bigquery.jobUser           # run query jobs
  roles/telemetry.tracesWriter     # OTLP spans → Telemetry API
  roles/cloudtrace.agent           # legacy Cloud Trace path (belt and braces)
  roles/logging.logWriter          # OTel logs → Cloud Logging
  roles/monitoring.metricWriter    # OTel metrics → Cloud Monitoring
  roles/browser                    # project number → project id (trace ↔ log link)
)

echo "--- Granting roles to ${AE_SA} ---"
for ROLE in "${ROLES[@]}"; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member "serviceAccount:${AE_SA}" \
    --role "${ROLE}" \
    --condition=None \
    --quiet >/dev/null
  echo "  ✓ ${ROLE}"
done

echo "--- Done ---"
