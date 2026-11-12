"""A2UI reliability bench: replay the real CopilotKit → agent request with each
demo question, N times, and validate every render_a2ui surface the way the
frontend renderer would (ids, component names, root, children, Chart data shape,
expected chart type, expected first value) — plus "no SQL ran" detection.

The fixture is a RunAgentInput captured between the CopilotKit runtime and the
agent (render_a2ui tool + the 5 A2UI context blocks: catalog, schemas,
guidelines). Re-capture it if the catalog or the CopilotKit version changes.

Needs the agent running (docker compose up agent, or uvicorn server:app):

    python3 -I tests/a2ui_bench.py                       # 7 questions × 10, 5 in parallel
    python3 -I tests/a2ui_bench.py -n 15 -q heatmap -p 1 # one question, sequential
"""
import argparse
import concurrent.futures as cf
import os
from pathlib import Path
import json
import sys
import time
import urllib.request
import uuid

URL = os.environ.get("AGUI_URL", "http://127.0.0.1:8000/chat")
FIXTURE = Path(__file__).parent / "fixtures" / "copilotkit_a2ui_request.json"
COMPONENTS = {'AudioPlayer', 'Button', 'Card', 'Chart', 'CheckBox', 'ChoicePicker', 'Column',
              'DateTimeInput', 'Divider', 'Icon', 'Image', 'List', 'Modal', 'Row', 'Slider',
              'Tabs', 'Text', 'TextField', 'Video'}

# (id, question, expected chartType, check on the Chart data → None if OK else reason)
def first_value(expected):
    def chk(c):
        d = c.get("data") or []
        yk = (c.get("yKeys") or ["value"])[0]
        v = d[0].get(yk) if d else None
        return None if v == expected else f"first {yk}={v!r}, expected {expected}"
    return chk

def radar_mbappe(c):
    flat = json.dumps(c.get("data"), ensure_ascii=False)
    return None if "10" in flat and "698" in flat else "radar data lacks Mbappé 10 goals / 698 min"

QUESTIONS = [
    ("radar", "Compare Mbappé et Dembélé : buts, passes décisives, buts par 90, minutes, titularisations", "radar", radar_mbappe),
    ("top5_goals", "Top 5 des buteurs du tournoi", "bar", first_value(10)),
    ("clubs", "Quels clubs ont fourni le plus de buts ? Montre-moi un graphique.", "bar", first_value(22)),
    ("psg_pie", "Les joueurs du PSG au Mondial, par sélection, en camembert", "pie", first_value(5)),
    ("top5_assists", "Top 5 des passeurs décisifs du tournoi", "bar", first_value(7)),
    ("mbappe_line", "Buts de Mbappé match après match", "line", None),
    ("heatmap", "Heatmap des buts par phase pour la France, l'Espagne, l'Argentine et l'Angleterre", "heatmap", None),
]


def validate(args_raw, expected_type, check):
    """Returns (status, detail). status: ok | wrong_type | bad_data | invalid."""
    try:
        a = json.loads(args_raw)
    except Exception as e:
        return "invalid", f"args not JSON: {e}"
    if a.get("catalogId") not in (None, "football_catalog"):
        return "invalid", f"catalogId={a.get('catalogId')!r}"
    comps = a.get("components")
    if not isinstance(comps, list) or not comps:
        return "invalid", "no components"
    ids = set()
    for c in comps:
        if not isinstance(c, dict) or not isinstance(c.get("id"), str):
            return "invalid", f"component missing id: keys={list(c)[:6] if isinstance(c, dict) else c}"
        if c.get("component") not in COMPONENTS:
            return "invalid", f"unknown component {c.get('component')!r} keys={list(c)[:6]}"
        ids.add(c["id"])
    if "root" not in ids:
        return "invalid", "no root"
    for c in comps:
        for ch in c.get("children") or []:
            if isinstance(ch, str) and ch not in ids:
                return "invalid", f"dangling child {ch!r}"
    charts = [c for c in comps if c["component"] == "Chart"]
    if not charts:
        return "invalid", "no Chart component"
    ch = charts[0]
    data = ch.get("data")
    if not isinstance(data, list) or not data:
        return "invalid", "Chart without data"
    t = ch.get("chartType")
    if t == "heatmap":
        if not all(isinstance(d.get("value"), (int, float)) and "x" in d and "y" in d for d in data):
            return "invalid", "heatmap items need x, y, numeric value"
    else:
        xk, yks = ch.get("xKey", "name"), ch.get("yKeys") or ["value"]
        if not all(xk in d and all(isinstance(d.get(k), (int, float)) for k in yks) for d in data):
            return "invalid", f"items lack {xk}/{yks}: {data[0]}"
    if t != expected_type:
        return "wrong_type", f"{t} instead of {expected_type}"
    if check:
        reason = check(ch)
        if reason:
            return "bad_data", reason
    return "ok", ""


def run_once(base, q):
    qid, question, expected, check = q
    body = dict(base, threadId=str(uuid.uuid4()), runId=str(uuid.uuid4()),
                messages=[{"id": str(uuid.uuid4()), "role": "user", "content": question}])
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Accept": "text/event-stream"})
    t0 = time.time()
    calls, args, errors, text = {}, {}, [], []
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            for line in r:
                line = line.decode().strip()
                if not line.startswith("data:"):
                    continue
                e = json.loads(line[5:])
                if e["type"] == "TOOL_CALL_START":
                    calls[e["toolCallId"]] = e["toolCallName"]
                elif e["type"] == "TOOL_CALL_ARGS":
                    args[e["toolCallId"]] = args.get(e["toolCallId"], "") + e["delta"]
                elif e["type"] == "TEXT_MESSAGE_CONTENT":
                    text.append(e["delta"])
                elif e["type"] == "RUN_ERROR":
                    errors.append(e.get("message"))
    except Exception as ex:
        errors.append(repr(ex))
    renders = [args.get(i, "") for i, n in calls.items() if n == "render_a2ui"]
    if errors:
        status, detail = "error", "; ".join(map(str, errors))[:300]
    elif not renders:
        status, detail = "no_render", ""
    else:
        status, detail = validate(renders[-1], expected, check)
    sql = [args.get(i, "") for i, n in calls.items() if n == "execute_sql_readonly"]
    if status == "ok" and not sql:
        status, detail = "no_sql", "chart rendered without any BigQuery query"
    return {"q": qid, "status": status, "detail": detail, "secs": round(time.time() - t0),
            "args": renders[-1] if renders else None, "sql": sql,
            "text": "".join(text)[:600]}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("-n", type=int, default=10, help="runs per question")
    ap.add_argument("-p", type=int, default=5, help="parallel runs")
    ap.add_argument("-q", help="comma-separated question ids (default: all)")
    ap.add_argument("-o", default="a2ui_bench_results.json", help="per-run results")
    ap.add_argument("--fixture", default=str(FIXTURE))
    a = ap.parse_args()
    base = json.load(open(a.fixture))
    only = a.q.split(",") if a.q else None
    jobs = [q for q in QUESTIONS if not only or q[0] in only for _ in range(a.n)]
    with cf.ThreadPoolExecutor(a.p) as ex:
        results = list(ex.map(lambda q: run_once(base, q), jobs))
    json.dump(results, open(a.o, "w"), ensure_ascii=False, indent=1)
    print(f"{'question':14s} {'ok':>3s}  failures")
    for q in QUESTIONS:
        rs = [r for r in results if r["q"] == q[0]]
        if not rs:
            continue
        ok = sum(r["status"] == "ok" for r in rs)
        fails = [f"{r['status']}: {r['detail'][:110]}" for r in rs if r["status"] != "ok"]
        print(f"{q[0]:14s} {ok:>2d}/{len(rs)}  " + (" | ".join(fails) if fails else ""))
    tot = sum(r["status"] == "ok" for r in results)
    print(f"TOTAL {tot}/{len(results)}  median {sorted(r['secs'] for r in results)[len(results)//2]}s")


if __name__ == "__main__":
    main()
