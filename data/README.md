# FIFA World Cup 2026 dataset

BigQuery dataset `fifa_world_cup_2026` (project `gb-poc-373711`, `europe-west1`),
the input of the agent.

```bash
python3 data/build_dataset.py        # raw/ → out/*.ndjson, fails on any inconsistency
./data/load_bigquery.sh              # build + bq load --replace (PROJECT_ID, LOCATION, DATASET overridable)
```

## Source

[openfootball/worldcup.json](https://github.com/openfootball/worldcup.json) —
**CC0 (public domain)** — files `2026/worldcup-full.json`, `worldcup.squads.json`,
`worldcup.teams.json`, pinned at commit `516d3825c3bd23fdc298c4014e84bde78f2d4965`
in `raw/`. It has every match with lineups, substitutions, goals (minute,
penalty, own goal) and bookings.

Corrections applied in `build_dataset.py`:

- 9 late injury replacements missing from the openfootball squads (Saâdane,
  Machino, Chalobah, …), taken from Wikipedia *2026 FIFA World Cup squads*.
- Lineup spellings matched to squad names (transliterations: `KIM Seunggyu` →
  Kim Seung-gyu, `ODEGAARD` → Ødegaard, plus 5 explicit overrides).

## Tables

| Table | Rows | Grain |
|---|---|---|
| `players` | 1248 | squad player: profile + tournament totals |
| `player_matches` | 3288 | player × match played |
| `matches` | 104 | match |
| `teams` | 48 | national team |
| `team_matches` | 208 | team × match (both sides of each match) |

Column descriptions live in `schemas/*.json` and are loaded into BigQuery, so the
agent sees them through `get_table_info`.

Derived columns: minutes (starters from 0, subs from their minute, until
substitution / red card / end of match; stoppage time not counted; a sub at
minute `121` is the break before extra time = 90), appearances,
starts, goals per 90, stage reached.

## Validation (the build fails otherwise)

- 308 goals = sum of scores = 294 player goals + 14 own goals.
- 178 / 178 goalscorers match the FIFA list (Wikipedia *Goalscorers*, sourced from
  FIFA player statistics), e.g. Mbappé 10, Messi 8, Haaland 7, Bellingham 7, Dembélé 6.
- 11 starters per team per match; team minutes = 11 × 90 (or 120) unless a red card.
- Every lineup, goal and booking name resolves to a squad player.
- Champion: Spain (1–0 a.e.t. v Argentina, Ferran Torres 106').

## Assists (FBref)

openfootball has no assists. They come from FBref *Player Standard Stats*,
exported by hand (FBref blocks automated access; *Share & Export → Get table as
CSV*) to `raw/fbref_wc2026_standard.csv` — **gitignored, not CC0**. Without the
file the build still runs and `assists` is NULL.

Checks: all 1039 FBref rows matched to a squad player, FBref goals = our goals
for every player (proves the name matching), Olise = 7, and the FBref top 20 is
identical to the API-Football leaderboard (two independent providers). Appearances
and starts match FBref for every player; minutes within 1' (median).

Known divergence kept on FIFA's side: Qatar–Switzerland 90+4' is an own goal by
Miro Muheim for FIFA / openfootball, a Boualem Khoukhi goal for FBref.

API-Football was tried first: its free plan does not cover the 2026 season.

## Why not the Kaggle datasets

`mominullptr/FIFA-World-Cup-2026-Dataset` (CC0, the most complete one, with
assists) disagrees with the FIFA list for 9 players (Dembélé 5 instead of 6,
Barcola 4 instead of 3, Yamal 2 instead of 1, …), has mangled names
(`MARQUINHOSMarcos`, `Mc` for McGinn) and gives Olise 8 assists where FIFA/ESPN
give 7. A wrong number on stage costs more than a missing column.
