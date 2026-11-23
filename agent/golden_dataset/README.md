# Golden dataset (World Cup 2026)

Reference questions with the facts their answer must contain, replayed against
the running agent to catch regressions after a change of prompt, model, ADK
version or data. Counterpart of the lite repo's golden dataset (Qatar 2022).

| What | Covered by |
|---|---|
| Facts in the text answer (numbers, names, order) | **this dataset** — `dataset.yaml`, 13 cases |
| The agent refuses to invent (xG, shots) | **this dataset** — `trap_*` cases |
| A2UI charts (type, shape, key values) | `tests/a2ui_bench.py` |

Every case also fails if the agent answered **without running SQL** in the turn
(`requires_sql`, default true): a right number from memory is still a bug.

## Run

The agent must be up on `http://localhost:8080` (`adk web` API, text answers):

```bash
docker compose up -d adk-web
cd agent
uv run python -m golden_dataset.runner              # all cases, one pass
uv run python -m golden_dataset.runner trap_xg      # some cases
uv run pytest tests/test_golden.py -v               # pytest, 2 retries per case
```

Or `make golden` from the repo root. `ADK_URL` targets another agent.

## Updating it

Expected values come from BigQuery `fifa_world_cup_2026`, cross-checked with
the FIFA goalscorer list (`data/README.md`). If the data or the prompts change
on purpose, recompute the values and update `dataset.yaml` deliberately — the
dataset is a contract, not a snapshot of the last run.
