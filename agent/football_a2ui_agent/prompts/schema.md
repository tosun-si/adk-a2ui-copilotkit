## Table Schema (team_players_stat_raw)
The columns use camelCase naming. Here is the full schema:
| Column | Type | Description |
|--------|------|-------------|
| nationality | STRING | Country/team name (e.g., "France", "Argentina") |
| fifaRanking | INTEGER | FIFA ranking of the team |
| nationalTeamKitSponsor | STRING | Kit sponsor |
| position | STRING | Player position (GK, DF, MF, FW) |
| nationalTeamJerseyNumber | INTEGER | Jersey number |
| playerDob | STRING | Date of birth |
| club | STRING | Club team |
| playerName | STRING | Player full name |
| appearances | STRING | Number of appearances |
| goalsScored | STRING | Goals scored |
| assistsProvided | STRING | Assists provided |
| dribblesPerNinety | STRING | Dribbles per 90 minutes |
| interceptionsPerNinety | STRING | Interceptions per 90 minutes |
| tacklesPerNinety | STRING | Tackles per 90 minutes |
| totalDuelsWonPerNinety | STRING | Total duels won per 90 minutes |
| savePercentage | STRING | Goalkeeper save percentage |
| cleanSheets | STRING | Clean sheets percentage |
| brandSponsorAndUsed | STRING | Player's brand sponsor |

IMPORTANT: Many numeric columns are stored as STRING type. Use CAST() or SAFE_CAST() to convert them for sorting/aggregation.
Example: SAFE_CAST(goalsScored AS INT64) to sort by goals.
