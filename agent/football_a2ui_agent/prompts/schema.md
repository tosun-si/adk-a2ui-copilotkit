## Tables (dataset fifa_world_cup_2026)

Pick the table from the question; most questions need ONE table, no join.

| Question about… | Table |
|---|---|
| a player's tournament totals, rankings of players, squads, clubs, ages | `players` |
| per match / per stage / evolution over the tournament, "against whom" | `player_matches` |
| a team match by match / per stage: goals for/against, results, path | `team_matches` |
| results, scores, penalty shoot-outs, venues, attendance, referees | `matches` |
| team totals, stage reached, goals for/against, cards per team | `teams` |

All numeric columns are real INT64/FLOAT64 (no CAST needed). Snake_case names.

### players — one row per squad player (48 × 26 = 1248)
| Column | Type | Notes |
|---|---|---|
| player_name | STRING | with accents, e.g. 'Kylian Mbappé' — display this |
| player_search_name | STRING | lower-case ASCII, e.g. 'kylian mbappe' — filter on this |
| team | STRING | national team, English name ('France', 'United States', 'Ivory Coast') |
| fifa_code | STRING | FRA, ARG, … |
| confederation | STRING | UEFA, CONMEBOL, CONCACAF, CAF, AFC, OFC |
| team_stage_reached | STRING | Champion, Runner-up, Third place, Fourth place, Quarter-final, Round of 16, Round of 32, Group stage |
| jersey_number | INT64 | |
| position | STRING | GK, DF, MF, FW |
| position_label | STRING | Goalkeeper, Defender, Midfielder, Forward |
| club | STRING | e.g. 'Paris Saint-Germain', 'Real Madrid C. F.', 'FC Bayern München' |
| club_country | STRING | league country code: FRA (Ligue 1), ENG, ESP, GER, ITA, … |
| date_of_birth | DATE | |
| age_at_tournament | INT64 | age on 2026-06-11 |
| matches_played, matches_started, minutes_played | INT64 | |
| goals, penalty_goals, own_goals | INT64 | goals exclude own goals and shoot-outs |
| assists | INT64 | assists (FBref count), tournament total only — not per match |
| yellow_cards, red_cards | INT64 | |
| goals_per_90 | FLOAT64 | NULL if never played |
| minutes_per_goal | FLOAT64 | NULL if no goal |

### player_matches — one row per player per match played (3288 rows)
match_id, match_date (DATE), stage, stage_order (1 = Group stage … 6 = Third
place, 7 = Final), player_name, player_search_name, team, opponent, position,
started (BOOL), minutes_played, goals, penalty_goals, own_goals, yellow_cards,
red_cards, team_goals, opponent_goals, result ('W'/'D'/'L', shoot-outs decide W/L).

### matches — one row per match (104)
match_id, match_date, kickoff_local, stage, stage_order, group_letter (A–L or
NULL), home_team, away_team, home_score, away_score (after extra time),
home_score_90, away_score_90, extra_time (BOOL), home_penalties,
away_penalties (NULL without shoot-out), winner (NULL for a draw), venue,
attendance, referee, referee_country.

### team_matches — one row per team per match (208 = 2 × 104)
match_id, match_date, stage, stage_order, group_letter, team, opponent,
goals_for, goals_against (after extra time, opponent own goals included),
goals_for_90, goals_against_90, extra_time, penalties_for, penalties_against,
result ('W'/'D'/'L'), venue, attendance.
Team goals per stage = `SELECT team, stage, stage_order, SUM(goals_for) …
GROUP BY team, stage, stage_order` — never UNION home/away on `matches`.

### teams — one row per national team (48)
team, fifa_code, group_letter, confederation, stage_reached, final_rank_bucket
(1, 2, 3, 4, then 5 / 9 / 17 / 33 — sort ascending), matches_played, wins,
draws, losses, goals_for, goals_against, clean_sheets, yellow_cards, red_cards.

### Not in the data
No shots, xG, passes completed, possession, dribbles or tackles, and no
assists per match (assists exist only as a tournament total in `players`). If
asked, say the dataset does not track it and offer the closest available metric
(goals, assists, goals per 90, minutes, starts). Never invent these numbers.
