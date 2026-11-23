"""Replay the golden dataset against the running agent (`adk web` API).

The agent must be reachable at $ADK_URL (default http://localhost:8080, the
`adk-web` service of docker-compose.yaml). Text answers only: A2UI is off on
`adk web`; the charts are checked by tests/a2ui_bench.py.

    cd agent && uv run python -m golden_dataset.runner            # all cases
    cd agent && uv run python -m golden_dataset.runner trap_xg    # some cases

Exit code 0 if every case passes, 1 otherwise.
"""
from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

import yaml

ADK_URL = os.environ.get("ADK_URL", "http://localhost:8080")
APP_NAME = "football_a2ui_agent"
USER_ID = "golden-runner"
DATASET_PATH = Path(__file__).parent / "dataset.yaml"
_NUMBER = re.compile(r"(?<![\d.,])\d+(?:[.,]\d+)?(?![\d])")


@dataclass
class Answer:
    text: str        # full answer, as returned
    norm: str        # lower-case, accents stripped
    numbers: list[float]
    sql_ran: bool    # did the agent call execute_sql_readonly in this turn?


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    no_accents = "".join(c for c in decomposed if not unicodedata.combining(c)).lower()
    return no_accents.replace("’", "'")


def _post(url: str, payload: dict[str, Any]) -> Any:
    req = Request(url, data=json.dumps(payload).encode(), method="POST",
                  headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())


def ask(question: str) -> Answer:
    """One fresh session per question: no context leaks between cases."""
    session = f"golden-{uuid.uuid4().hex[:8]}"
    _post(f"{ADK_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions/{session}", {})
    events = _post(f"{ADK_URL}/run", {
        "appName": APP_NAME, "userId": USER_ID, "sessionId": session,
        "newMessage": {"role": "user", "parts": [{"text": question}]},
    })
    text, sql_ran = "", False
    for event in events:
        for part in (event.get("content") or {}).get("parts") or []:
            if part.get("text") and not part.get("thought"):
                text += part["text"]
            call = part.get("functionCall") or part.get("function_call")
            if call and call.get("name") == "execute_sql_readonly":
                sql_ran = True
    numbers = [float(n.replace(",", ".")) for n in _NUMBER.findall(text)]
    return Answer(text=text, norm=normalize(text), numbers=numbers, sql_ran=sql_ran)


def _alternatives(item: str | list[str]) -> list[str]:
    return [normalize(a) for a in (item if isinstance(item, list) else [item])]


def check(answer: Answer, expect: dict[str, Any]) -> list[str]:
    """Return the list of broken expectations (empty = pass)."""
    errors = []
    # Every number must come from BigQuery: a right answer from memory is a fail.
    if expect.get("requires_sql", True) and not answer.sql_ran:
        errors.append("answered WITHOUT querying BigQuery")
    for needle in expect.get("contains_all", []):
        if normalize(needle) not in answer.norm:
            errors.append(f"missing {needle!r}")
    if "contains_any" in expect and not any(normalize(n) in answer.norm for n in expect["contains_any"]):
        errors.append(f"none of {expect['contains_any'][:4]}… found")
    if "matching_any" in expect and not any(re.search(rx, answer.norm) for rx in expect["matching_any"]):
        errors.append("no refusal / negation found")
    cursor = -1
    for item in expect.get("ordered", []):
        positions = [p for p in (answer.norm.find(a, cursor + 1) for a in _alternatives(item)) if p != -1]
        if not positions:
            errors.append(f"order broken at {item!r}")
            break
        cursor = min(positions)
    for n in expect.get("numbers", []):
        if float(n) not in answer.numbers:
            errors.append(f"number {n} missing")
    for pattern in expect.get("not_matching", []):
        if re.search(pattern, answer.norm):
            errors.append(f"matches forbidden /{pattern}/")
    return errors


def load_cases(ids: list[str] | None = None) -> list[dict[str, Any]]:
    cases = yaml.safe_load(DATASET_PATH.read_text())
    return [c for c in cases if not ids or c["id"] in ids]


def main(ids: list[str]) -> int:
    cases = load_cases(ids)
    failed = 0
    for case in cases:
        print(f"→ {case['id']:<28}", end=" ", flush=True)
        try:
            answer = ask(case["question"])
        except (URLError, OSError, ValueError) as exc:  # network / 5xx (HTTPError ⊂ URLError) / timeout / bad JSON
            failed += 1
            print(f"ERROR  {exc}")
            continue
        errors = check(answer, case["expect"])
        sql = "sql" if answer.sql_ran else "NO SQL"
        if errors:
            failed += 1
            print(f"FAIL   [{sql}] {'; '.join(errors)}")
            print(f"       answer: {answer.text[:300]!r}")
        else:
            print(f"ok     [{sql}]")
    print(f"\n=== {len(cases) - failed}/{len(cases)} passed ===")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
