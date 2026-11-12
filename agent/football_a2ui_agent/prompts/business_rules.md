## Business Rules
1. Efficiency rankings (goals per 90, minutes per goal) only include players with
   at least 180 minutes played — otherwise a 1-goal cameo tops the list. Say so.
2. Team style: OFFENSIVE (goals_for / matches_played >= 2.0), SOLID DEFENCE
   (goals_against / matches_played < 1.0), else BALANCED.
3. Knockout stage = `stage_order >= 2` (Round of 32 onwards).
4. Penalty shoot-out kicks are not goals. A match won on penalties counts as a win.
5. Goal contributions = goals + assists (players table only).
6. Discipline points: yellow card = 1, red card = 3. Lower is cleaner.
7. Ties in a ranking: break them with fewer minutes played, and mention the tie.
