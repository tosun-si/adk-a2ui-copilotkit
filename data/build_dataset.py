"""Build the FIFA World Cup 2026 BigQuery tables from openfootball (CC0).

Source: https://github.com/openfootball/worldcup.json (2026/), pinned in data/raw/.
Stdlib only:  python3 data/build_dataset.py   →  data/out/*.ndjson

Tables (one NDJSON file each, schema in data/schemas/):
  teams           48 rows   — team-level aggregates + stage reached
  matches         104 rows  — one row per match
  players         1248 rows — one row per squad player, tournament aggregates
  player_matches  one row per player per match actually played
  team_matches    208 rows  — one row per team per match (both sides of each match)

Derived, not in the source: minutes (lineups + subs + red cards), appearances,
starts, goals/penalties/own goals per player, cards, stage reached.
No assists: no CC0 source has them reliably (checked against FIFA/ESPN).
"""

import collections
import difflib
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
RAW = ROOT / "raw"
OUT = ROOT / "out"

TOURNAMENT_START = date(2026, 6, 11)

# Match files use FIFA-ish names, squads/teams use common English names.
TEAM_ALIASES = {
    "USA": "United States",
    "Cabo Verde": "Cape Verde",
    "Côte d'Ivoire": "Ivory Coast",
    "Congo DR": "DR Congo",
    "Bosnia & Herzegovina": "Bosnia and Herzegovina",
    "Bosnia–Herz": "Bosnia and Herzegovina",  # FBref (en dash, truncated)
}

STAGES = {
    "First Stage": ("Group stage", 1),
    "Round of 32": ("Round of 32", 2),
    "Round of 16": ("Round of 16", 3),
    "Quarter-final": ("Quarter-final", 4),
    "Semi-final": ("Semi-final", 5),
    "Bronze final": ("Third place", 6),
    "Final": ("Final", 7),
}

POSITIONS = {"GK": "Goalkeeper", "DF": "Defender", "MF": "Midfielder", "FW": "Forward"}

# Lineup spellings that the generic matcher cannot resolve: (team, lineup name) → squad name.
NAME_OVERRIDES = {
    ("Brazil", "DANILO"): "Danilo Luiz",  # "DANILO SANTOS" is the other one
    ("Paraguay", "Alejandro ROMERO GAMARRA"): "Kaku",
    ("Cape Verde", "PICO LOPES"): "Roberto Lopes",
    ("Uruguay", "Maxi ARAUJO"): "Maximiliano Araújo",
    ("Jordan", "MOHAMMAD ABUALNADI"): "Mo Abualnadi",
    # FBref nicknames, each checked against club + birth year
    ("Brazil", "Danilo"): "Danilo Luiz",
    ("Uruguay", "Maxi Araújo"): "Maximiliano Araújo",
    ("Cape Verde", "Pico"): "Roberto Lopes",
    ("Argentina", "Flaco López"): "José Manuel López",
    ("Qatar", "Ró-Ró"): "Pedro Miguel",
    ("Jordan", "Sharara"): "Mohammad Abu Zrayq",
    ("Australia", "Mo Touré"): "Mohamed Touré",
}

# Goals where FBref disagrees with openfootball AND the FIFA goalscorer list
# (Wikipedia). We keep FIFA's version; FBref's assists for the player are kept.
# Qatar–Switzerland 90+4: FIFA = own goal Miro Muheim, FBref = Boualem Khoukhi.
FBREF_GOAL_DIVERGENCES = {("Qatar", "Boualem Khoukhi")}

# openfootball squads predate the late injury replacements. Final squads from
# Wikipedia "2026 FIFA World Cup squads" (same shirt number as the replaced player).
SQUAD_REPLACEMENTS = {
    ("Bosnia and Herzegovina", 24): ("Arjan Malić", "DF", "SK Sturm Graz", "AUT", "2005-08-28"),
    ("Haiti", 14): ("Garven Metusala", "DF", "Colorado Springs Switchbacks FC", "USA", "1999-12-31"),
    ("Morocco", 5): ("Marwane Saâdane", "DF", "Al-Fateh SC", "KSA", "1992-01-17"),
    ("Morocco", 17): ("Amine Sbaï", "FW", "Angers SCO", "FRA", "2000-11-05"),
    ("Japan", 6): ("Shūto Machino", "FW", "Borussia Mönchengladbach", "GER", "1999-09-30"),
    ("New Zealand", 7): ("Logan Rogerson", "FW", "Auckland FC", "NZL", "1998-05-28"),
    ("Jordan", 18): ("Mohammad Abu Ghoush", "MF", "Al-Hussein SC", "JOR", "2005-07-13"),
    ("Uzbekistan", 10): ("Ruslanbek Jiyanov", "MF", "Navbahor Namangan", "UZB", "2001-06-05"),
    ("England", 12): ("Trevoh Chalobah", "DF", "Chelsea FC", "ENG", "1999-07-05"),
}


FBREF_CSV = RAW / "fbref_wc2026_standard.csv"


def load_fbref_assists(idx, teams_raw):
    """Assists from FBref "Standard Stats" (Share & Export → Get table as CSV),
    exported by hand to data/raw/fbref_wc2026_standard.csv (gitignored: not CC0).

    Returns ({(team, squad name): (assists, fbref goals)}, unmatched rows), or
    (None, []) when the file is absent (assists stay NULL)."""
    import csv
    if not FBREF_CSV.exists():
        return None, []
    lines = FBREF_CSV.read_text(encoding="utf-8-sig").splitlines()
    # the export starts with a group-header row ("Playing Time", "Performance"…)
    start = next(i for i, l in enumerate(lines) if "Player" in l.split(",") and "Ast" in l.split(","))
    reader = csv.reader(lines[start:])
    header = next(reader)
    col = {h: header.index(h) for h in ("Player", "Squad", "Gls", "Ast")}
    # FBref squads look like "fr France", "ci Côte d'Ivoire", "kr Korea Republic"
    team_by_key = {}
    for name, meta in teams_raw.items():
        for alias in (name, meta["name"], meta.get("name_normalised") or name):
            team_by_key[compact(alias)] = name
    out, unmatched = {}, []
    for row in reader:
        if len(row) < len(header) or row[col["Player"]] in ("", "Player"):
            continue  # repeated header rows inside the table
        squad = re.sub(r"^[a-z]{2,3} ", "", row[col["Squad"]])
        team = team_by_key.get(compact(TEAM_ALIASES.get(squad, squad)))
        p = idx.resolve(team, row[col["Player"]]) if team else None
        if not p:
            unmatched.append((row[col["Squad"]], row[col["Player"]]))
            continue
        out[(team, p["name"])] = (int(row[col["Ast"]] or 0), int(row[col["Gls"]] or 0))
    return out, unmatched


def apply_replacements(squads):
    for t in squads:
        for p in t["players"]:
            r = SQUAD_REPLACEMENTS.get((t["name"], p["number"]))
            if r:
                p.update(name=r[0], pos=r[1], club={"name": r[2], "country": r[3]},
                         date_of_birth=r[4])


TRANSLIT = str.maketrans({"ø": "o", "Ø": "o", "æ": "ae", "Æ": "ae", "ß": "ss", "ı": "i",
                          "đ": "d", "Đ": "d", "ł": "l", "Ł": "l", "ð": "d", "þ": "th"})


def norm(s: str) -> str:
    """'Zaïre-Emery' → 'zaire emery': ascii, lower-case, punctuation → space."""
    s = unicodedata.normalize("NFKD", s.translate(TRANSLIT)).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s.lower().replace("'", "")).split())


def compact(s: str) -> str:
    """Spacing/transliteration-insensitive key: 'Kim Seung-gyu' == 'KIM Seunggyu',
    'Rüdiger' == 'RUEDIGER', 'Al-Haydos' == 'ALHAYDOS'."""
    s = norm(s).replace(" ", "")
    return re.sub(r"([aou])e", r"\1", s)


def minute(m: str) -> int:
    """'90+3' → 90, '45+1' → 45, '106' → 106.

    openfootball writes a substitution made at the break before extra time as
    '121' (5 cases, all in extra-time matches): it is minute 90, not 120+1 —
    confirmed against FBref minutes (Mabil 30', Heggem / Almirón -30')."""
    if str(m) == "121":
        return 90
    return int(str(m).split("+")[0])


class SquadIndex:
    def __init__(self, squads):
        self.by_team = {t["name"]: t["players"] for t in squads}
        self.unresolved: collections.Counter = collections.Counter()
        self.fuzzy: set = set()

    def resolve(self, team: str, name: str):
        players = self.by_team[team]
        if (team, name) in NAME_OVERRIDES:
            target = NAME_OVERRIDES[(team, name)]
            return next(p for p in players if p["name"] == target)
        n = norm(name)
        exact = [p for p in players if norm(p["name"]) == n]
        if len(exact) == 1:
            return exact[0]
        toks = n.split()
        # lineup uses "First LAST": every token must appear in the squad name
        cands = [p for p in players if set(toks) <= set(norm(p["name"]).split())]
        if len(cands) == 1:
            return cands[0]
        # surname (upper-case part of the lineup name) only
        surname = [t for t in name.split() if t.isupper() and len(t) > 1]
        if surname:
            s = norm(" ".join(surname)).split()
            cands = [p for p in players if set(s) <= set(norm(p["name"]).split())]
            if len(cands) == 1:
                return cands[0]
        # substring fallback (compound names, "Vinicius Junior" vs "Vinícius Júnior")
        cands = [p for p in players if n in norm(p["name"]) or norm(p["name"]) in n]
        if len(cands) == 1:
            return cands[0]
        # spacing / transliteration-insensitive: full name, then surname
        c = compact(name)
        cands = [p for p in players if compact(p["name"]) == c]
        if len(cands) == 1:
            return cands[0]
        if surname:
            cs = compact(" ".join(surname))
            cands = [p for p in players if cs in compact(p["name"])]
            if len(cands) == 1:
                return cands[0]
        # last resort: closest spelling, only if clearly ahead of the runner-up
        scored = sorted(((difflib.SequenceMatcher(None, c, compact(p["name"])).ratio(), p)
                         for p in players), key=lambda x: -x[0])
        if scored[0][0] >= 0.75 and scored[0][0] - scored[1][0] >= 0.1:
            self.fuzzy.add((team, name, scored[0][1]["name"], round(scored[0][0], 2)))
            return scored[0][1]
        self.unresolved[(team, name)] += 1
        return None


def main() -> int:
    matches_raw = json.loads((RAW / "worldcup-full.json").read_text())["matches"]
    squads = json.loads((RAW / "worldcup.squads.json").read_text())
    teams_raw = {TEAM_ALIASES.get(t["name"], t["name"]): t
                 for t in json.loads((RAW / "worldcup.teams.json").read_text())}
    apply_replacements(squads)
    idx = SquadIndex(squads)

    def team_name(t: str) -> str:
        return TEAM_ALIASES.get(t, t)

    # player key = (team, squad name)
    stats = collections.defaultdict(collections.Counter)
    player_matches = []
    matches = []
    team_stats = collections.defaultdict(collections.Counter)
    team_last_stage = {}
    unresolved_events = []

    for match_id, m in enumerate(matches_raw, start=1):
        t1, t2 = team_name(m["team1"]), team_name(m["team2"])
        stage_key = m["round"].split(",")[0]
        stage, stage_order = STAGES[stage_key]
        group = m["round"].split("Group ")[1] if "Group " in m["round"] else None
        sc = m["score"]
        ft = sc.get("et") or sc["ft"]  # score after extra time when played
        pens = sc.get("p")
        length = 120 if "et" in sc else 90
        if pens:
            winner = t1 if pens[0] > pens[1] else t2
        elif ft[0] != ft[1]:
            winner = t1 if ft[0] > ft[1] else t2
        else:
            winner = None
        matches.append({
            "match_id": match_id,
            "match_date": m["date"],
            "kickoff_local": m["time"],
            "stage": stage,
            "stage_order": stage_order,
            "group_letter": group,
            "home_team": t1,
            "away_team": t2,
            "home_score": ft[0],
            "away_score": ft[1],
            "home_score_90": sc["ft"][0],
            "away_score_90": sc["ft"][1],
            "extra_time": "et" in sc,
            "home_penalties": pens[0] if pens else None,
            "away_penalties": pens[1] if pens else None,
            "winner": winner,
            "venue": m["ground"],
            "attendance": m.get("attendance"),
            "referee": " ".join(w if not w.isupper() else w.title()
                                for w in m["referees"][0]["name"].split())
            if m.get("referees") else None,
            "referee_country": m["referees"][0].get("country") if m.get("referees") else None,
        })

        sides = [(t1, t2, 0), (t2, t1, 1)]
        # per-match per-player accumulator
        pm = {}

        def slot(team, p):
            key = (team, p["name"])
            if key not in pm:
                pm[key] = {"team": team, "player": p, "on": None, "off": None, "started": False,
                           "goals": 0, "penalty_goals": 0, "own_goals": 0,
                           "yellow_cards": 0, "red_cards": 0}
            return pm[key]

        for team, opp, i in sides:
            lineup = m["lineup"][i]
            for e in lineup["starter"]:
                p = idx.resolve(team, e["name"])
                if p:
                    s = slot(team, p)
                    s["on"], s["started"] = 0, True
            for sub in lineup.get("subs", []):
                p_on, p_off = idx.resolve(team, sub["on"]), idx.resolve(team, sub["off"])
                if p_on:
                    slot(team, p_on)["on"] = minute(sub["minute"])
                if p_off:
                    slot(team, p_off)["off"] = minute(sub["minute"])
            for b in (m.get("bookings") or [[], []])[i]:
                p = idx.resolve(team, b["name"])
                if not p:
                    unresolved_events.append((match_id, team, "booking", b["name"]))
                    continue
                s = slot(team, p)
                if b["type"] == "Y":
                    s["yellow_cards"] += 1
                else:  # "R" straight red, "Y/R" second yellow
                    s["red_cards"] += 1
                    s["off"] = minute(b["minute"]) if s["off"] is None else s["off"]

        for team, opp, i in sides:
            for g in m.get(f"goals{i + 1}", []):
                # an own goal in goals1 was scored by a team2 player
                scorer_team = opp if g.get("owngoal") else team
                p = idx.resolve(scorer_team, g["name"])
                if not p:
                    unresolved_events.append((match_id, scorer_team, "goal", g["name"]))
                    continue
                s = slot(scorer_team, p)
                if g.get("owngoal"):
                    s["own_goals"] += 1
                else:
                    s["goals"] += 1
                    s["penalty_goals"] += 1 if g.get("penalty") else 0

        for team, opp, i in sides:
            gf, ga = (ft[0], ft[1]) if i == 0 else (ft[1], ft[0])
            if winner == team:
                result = "W"
            elif winner is None:
                result = "D"
            else:
                result = "L"
            ts = team_stats[team]
            ts["matches_played"] += 1
            ts["goals_for"] += gf
            ts["goals_against"] += ga
            ts["wins" if result == "W" else "draws" if result == "D" else "losses"] += 1
            ts["clean_sheets"] += 1 if ga == 0 else 0
            prev = team_last_stage.get(team)
            if prev is None or stage_order >= prev[1]:
                team_last_stage[team] = (stage, stage_order, result)
            for (pteam, _), s in pm.items():
                if pteam != team or s["on"] is None:
                    continue  # bench player who did not come on
                # clamp: the source writes some stoppage-time subs as "121"
                off = min(s["off"] if s["off"] is not None else length, length)
                mins = max(off - min(s["on"], length), 0)
                p = s["player"]
                row = {
                    "match_id": match_id,
                    "match_date": m["date"],
                    "stage": stage,
                    "stage_order": stage_order,
                    "player_name": p["name"],
                    "player_search_name": norm(p["name"]),
                    "team": team,
                    "opponent": opp,
                    "position": p["pos"],
                    "started": s["started"],
                    "minutes_played": mins,
                    "goals": s["goals"],
                    "penalty_goals": s["penalty_goals"],
                    "own_goals": s["own_goals"],
                    "yellow_cards": s["yellow_cards"],
                    "red_cards": s["red_cards"],
                    "team_goals": gf,
                    "opponent_goals": ga,
                    "result": result,
                }
                player_matches.append(row)
                a = stats[(team, p["name"])]
                a["matches_played"] += 1
                a["matches_started"] += 1 if s["started"] else 0
                for k in ("minutes_played", "goals", "penalty_goals", "own_goals",
                          "yellow_cards", "red_cards"):
                    a[k] += row[k]
                ts["yellow_cards"] += s["yellow_cards"]
                ts["red_cards"] += s["red_cards"]

    # stage reached: winners of Final / Third place are explicit, others = last stage played
    def stage_reached(team):
        stage, order, result = team_last_stage[team]
        if stage == "Final":
            return ("Champion", 1) if result == "W" else ("Runner-up", 2)
        if stage == "Third place":
            return ("Third place", 3) if result == "W" else ("Fourth place", 4)
        return {"Group stage": ("Group stage", 33), "Round of 32": ("Round of 32", 17),
                "Round of 16": ("Round of 16", 9), "Quarter-final": ("Quarter-final", 5)}[stage]

    teams = []
    for t in squads:
        name = t["name"]
        meta = teams_raw[name]
        ts = team_stats[name]
        reached, best_rank = stage_reached(name)
        teams.append({
            "team": name,
            "fifa_code": t["fifa_code"],
            "group_letter": t["group"],
            "confederation": meta["confed"],
            "stage_reached": reached,
            "final_rank_bucket": best_rank,
            "matches_played": ts["matches_played"],
            "wins": ts["wins"], "draws": ts["draws"], "losses": ts["losses"],
            "goals_for": ts["goals_for"], "goals_against": ts["goals_against"],
            "clean_sheets": ts["clean_sheets"],
            "yellow_cards": ts["yellow_cards"], "red_cards": ts["red_cards"],
        })
    team_meta = {t["team"]: t for t in teams}
    # separate index: FBref spellings must not pollute the lineup diagnostics
    fbref, fbref_unmatched = load_fbref_assists(SquadIndex(squads), teams_raw)

    players = []
    for t in squads:
        for p in t["players"]:
            a = stats.get((t["name"], p["name"]), collections.Counter())
            dob = date.fromisoformat(p["date_of_birth"])
            age = TOURNAMENT_START.year - dob.year - (
                (TOURNAMENT_START.month, TOURNAMENT_START.day) < (dob.month, dob.day))
            mins = a["minutes_played"]
            players.append({
                "player_name": p["name"],
                "player_search_name": norm(p["name"]),
                "team": t["name"],
                "fifa_code": t["fifa_code"],
                "confederation": team_meta[t["name"]]["confederation"],
                "team_stage_reached": team_meta[t["name"]]["stage_reached"],
                "jersey_number": p["number"],
                "position": p["pos"],
                "position_label": POSITIONS[p["pos"]],
                "club": p["club"]["name"],
                "club_country": p["club"]["country"],
                "date_of_birth": p["date_of_birth"],
                "age_at_tournament": age,
                "matches_played": a["matches_played"],
                "matches_started": a["matches_started"],
                "minutes_played": mins,
                "goals": a["goals"],
                "assists": (fbref.get((t["name"], p["name"]), (0, 0))[0]
                            if fbref is not None else None),
                "penalty_goals": a["penalty_goals"],
                "own_goals": a["own_goals"],
                "yellow_cards": a["yellow_cards"],
                "red_cards": a["red_cards"],
                "goals_per_90": round(a["goals"] * 90 / mins, 2) if mins else None,
                "minutes_per_goal": round(mins / a["goals"], 1) if a["goals"] else None,
            })

    # team_matches: one row per team per match (2 × 104). Saves the model a
    # home/away UNION on `matches` for every team-level per-match/per-stage
    # question (the heatmap took 40-90 s with 2-4 SQL attempts without it).
    team_matches = []
    for m in matches:
        for side, opp_side in (("home", "away"), ("away", "home")):
            team, opp = m[f"{side}_team"], m[f"{opp_side}_team"]
            gf, ga = m[f"{side}_score"], m[f"{opp_side}_score"]
            pf, pa = m[f"{side}_penalties"], m[f"{opp_side}_penalties"]
            result = "D" if m["winner"] is None else ("W" if m["winner"] == team else "L")
            team_matches.append({
                "match_id": m["match_id"],
                "match_date": m["match_date"],
                "stage": m["stage"],
                "stage_order": m["stage_order"],
                "group_letter": m["group_letter"],
                "team": team,
                "opponent": opp,
                "goals_for": gf,
                "goals_against": ga,
                "goals_for_90": m[f"{side}_score_90"],
                "goals_against_90": m[f"{opp_side}_score_90"],
                "extra_time": m["extra_time"],
                "penalties_for": pf,
                "penalties_against": pa,
                "result": result,
                "venue": m["venue"],
                "attendance": m["attendance"],
            })

    # ---- validation: fail loudly rather than load wrong numbers -------------
    errors = []
    raw_goals = sum(len(m.get("goals1", [])) + len(m.get("goals2", [])) for m in matches_raw)
    built_goals = sum(p["goals"] + p["own_goals"] for p in players)
    if raw_goals != built_goals:
        errors.append(f"goals: raw {raw_goals} != built {built_goals}")
    score_goals = sum(m["home_score"] + m["away_score"] for m in matches)
    if score_goals != raw_goals:
        errors.append(f"goals: scores {score_goals} != events {raw_goals}")
    if len(players) != 1248 or len(teams) != 48 or len(matches) != 104:
        errors.append(f"counts: {len(players)} players, {len(teams)} teams, {len(matches)} matches")
    starters = collections.Counter((r["match_id"], r["team"]) for r in player_matches if r["started"])
    bad = {k: v for k, v in starters.items() if v != 11}
    if bad:
        errors.append(f"starters != 11: {list(bad.items())[:5]}")
    team_minutes = collections.Counter()
    team_reds = collections.Counter()
    for r in player_matches:
        team_minutes[(r["match_id"], r["team"])] += r["minutes_played"]
        team_reds[(r["match_id"], r["team"])] += r["red_cards"]
    for (mid, team), mins in team_minutes.items():
        full_time = 11 * (120 if matches[mid - 1]["extra_time"] else 90)
        if mins > full_time or (mins < full_time and not team_reds[(mid, team)]):
            errors.append(f"minutes {mid}/{team}: {mins} vs {full_time} with no red card")
    if idx.unresolved:
        errors.append(f"unresolved lineup names: {dict(idx.unresolved)}")
    if unresolved_events:
        errors.append(f"unresolved events: {unresolved_events}")
    champions = [t["team"] for t in teams if t["stage_reached"] == "Champion"]
    if champions != ["Spain"]:
        errors.append(f"champion: {champions}")
    # Spot checks against FIFA official stats (Wikipedia goalscorers, ESPN)
    expected = {("France", "Kylian Mbappé"): 10, ("Argentina", "Lionel Messi"): 8,
                ("France", "Ousmane Dembélé"): 6, ("France", "Bradley Barcola"): 3,
                ("England", "Jude Bellingham"): 7, ("Norway", "Erling Haaland"): 7}
    got = {(p["team"], p["player_name"]): p["goals"] for p in players}
    for k, v in expected.items():
        if got.get(k) != v:
            errors.append(f"spot check {k}: expected {v}, got {got.get(k)}")
    if fbref is None:
        print(f"WARNING: {FBREF_CSV.name} absent → assists = NULL", file=sys.stderr)
    else:
        if fbref_unmatched:
            errors.append(f"FBref rows not matched to a squad player: {fbref_unmatched}")
        # same goals on both sides = the name matching picked the right player
        bad = [(k, g, got[k]) for k, (_, g) in fbref.items()
               if got.get(k) != g and k not in FBREF_GOAL_DIVERGENCES]
        if bad:
            errors.append(f"FBref goals differ from openfootball: {bad}")
        olise = fbref.get(("France", "Michael Olise"), (None,))[0]
        if olise != 7:
            errors.append(f"spot check Olise assists: expected 7, got {olise}")
        print(f"assists: {sum(a for a, _ in fbref.values())} from FBref, "
              f"{len(fbref)} players matched")
    if len(team_matches) != 208 or sum(t["goals_for"] for t in team_matches) != raw_goals:
        errors.append(f"team_matches: {len(team_matches)} rows, "
                      f"{sum(t['goals_for'] for t in team_matches)} goals")
    tm_totals = collections.Counter()
    for t in team_matches:
        tm_totals[t["team"]] += t["goals_for"]
    bad_tm = [(t["team"], t["goals_for"], tm_totals[t["team"]]) for t in teams
              if t["goals_for"] != tm_totals[t["team"]]]
    if bad_tm:
        errors.append(f"team_matches goals_for != teams.goals_for: {bad_tm}")
    if "-v" in sys.argv:
        for f in sorted(idx.fuzzy):
            print("fuzzy match:", f)
    if errors:
        print("VALIDATION FAILED:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 1

    OUT.mkdir(exist_ok=True)
    for name, rows in (("teams", teams), ("matches", matches), ("players", players),
                       ("player_matches", player_matches), ("team_matches", team_matches)):
        with (OUT / f"{name}.ndjson").open("w") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"{name:15s} {len(rows):5d} rows → data/out/{name}.ndjson")
    print(f"goals {built_goals} (own goals {sum(p['own_goals'] for p in players)}), "
          f"champion {champions[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
