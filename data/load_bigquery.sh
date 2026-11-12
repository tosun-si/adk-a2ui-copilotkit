#!/usr/bin/env bash
# Build the 2026 World Cup tables from data/raw/ and (re)load them into BigQuery.
# Idempotent: --replace overwrites each table; the dataset is created once.
#
#   PROJECT_ID=gb-poc-373711 ./data/load_bigquery.sh
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-gb-poc-373711}"
LOCATION="${LOCATION:-europe-west1}"
DATASET="${DATASET:-fifa_world_cup_2026}"
HERE="$(cd "$(dirname "$0")" && pwd)"

python3 "$HERE/build_dataset.py"

if ! bq --project_id="$PROJECT_ID" show --dataset "$PROJECT_ID:$DATASET" >/dev/null 2>&1; then
  bq --project_id="$PROJECT_ID" mk --dataset --location="$LOCATION" \
    --description="FIFA World Cup 2026 (Canada/Mexico/USA) — players, matches, teams. Source: openfootball/worldcup.json (CC0)." \
    "$PROJECT_ID:$DATASET"
fi

description() {
  case "$1" in
    players) echo "One row per squad player (48 x 26 = 1248): profile + tournament totals (goals, minutes, cards)." ;;
    player_matches) echo "One row per player per match played: minutes, goals, cards, result. Use for per-match / per-stage questions." ;;
    matches) echo "One row per match (104): stage, teams, score, extra time, penalties, venue, attendance, referee." ;;
    teams) echo "One row per national team (48): stage reached, wins/draws/losses, goals for/against, cards." ;;
    team_matches) echo "One row per team per match (208): goals for/against, result, stage. Use for team-level per-match / per-stage questions." ;;
  esac
}

for table in players player_matches matches teams team_matches; do
  echo "→ $DATASET.$table"
  bq --project_id="$PROJECT_ID" load --location="$LOCATION" --replace \
    --source_format=NEWLINE_DELIMITED_JSON \
    "$PROJECT_ID:$DATASET.$table" "$HERE/out/$table.ndjson" "$HERE/schemas/$table.json"
  bq --project_id="$PROJECT_ID" update --description "$(description "$table")" "$PROJECT_ID:$DATASET.$table" >/dev/null
done

bq --project_id="$PROJECT_ID" query --location="$LOCATION" --use_legacy_sql=false --format=pretty \
  "SELECT player_name, team, goals FROM \`$PROJECT_ID.$DATASET.players\` ORDER BY goals DESC LIMIT 5"
