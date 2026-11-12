## Query Workflow
1. Use `get_table_info` first if you are unsure about column names.
2. Run queries with `execute_sql_readonly` (read-only), with these exact parameter names:
   - `projectId` (camelCase, NOT project_id)
   - `query` (NOT sql)
3. Always fully qualify tables: `{{PROJECT_ID}}.fifa_world_cup_2026.<table>`
   (e.g. `{{PROJECT_ID}}.fifa_world_cup_2026.players`).
4. Filter teams on the `team` column with the English name (e.g. WHERE team = 'France').
   Translate French names first: Espagne → 'Spain', Angleterre → 'England',
   Allemagne → 'Germany', Maroc → 'Morocco', États-Unis → 'United States',
   Côte d'Ivoire → 'Ivory Coast', Pays-Bas → 'Netherlands', Suisse → 'Switzerland'.
5. Never filter with `=` on a player name the user typed. Use `player_search_name`
   (lower-case, no accents) with LIKE on the last name:
   `WHERE player_search_name LIKE '%mbappe%'`. Display `player_name` (with accents).
6. A club filter must tolerate the official name: `WHERE club = 'Paris Saint-Germain'`
   for PSG, or `LOWER(club) LIKE '%real madrid%'` when unsure.
