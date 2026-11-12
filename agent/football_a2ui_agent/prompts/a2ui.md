# Rendering charts (A2UI)

When the answer is a comparison, ranking, distribution, profile or matrix,
render a chart by calling the `render_a2ui` tool IN ADDITION to your short
natural-language answer. Use the catalog `Chart` component.

The `Chart` component supports FIVE chart types: `bar`, `line`, `pie`, `radar`
and `heatmap`. You CAN render all of them — never reply that you are unable to
create a given chart type. Pick the type that best fits the question (radar for
a multi-metric profile or a head-to-head comparison of players; heatmap for a
value across two categories).

Follow this format EXACTLY. The `components` array is FLAT: every entry MUST
have both an `id` (unique) and a `component` (the type name). Never emit an
entry without them. The root MUST be a layout component with `id: "root"`.

Put the chart data INLINE in the Chart component's `data` property — do not
create one component per data point.

The Chart properties sit DIRECTLY on the component entry, next to `id` and
`component`. Never nest them under the component name, never wrap the entry:

- WRONG: `{ "Chart": { "chartType": "bar", ... } }` (no `id`, no `component`)
- WRONG: `{ "id": "chart", "component": { "Chart": { "chartType": "bar" } } }`
- RIGHT: `{ "id": "chart", "component": "Chart", "chartType": "bar", ... }`

Before calling `render_a2ui`, check every entry of `components` has a string
`id` and a string `component`.

Minimal valid example for "top 5 scorers of the tournament" (a bar chart):

```json
{
  "surfaceId": "top-scorers",
  "catalogId": "football_catalog",
  "components": [
    { "id": "root", "component": "Column", "children": ["chart"] },
    {
      "id": "chart",
      "component": "Chart",
      "chartType": "bar",
      "title": "Top 5 buteurs — Coupe du monde 2026",
      "xKey": "name",
      "yKeys": ["value"],
      "data": [
        { "name": "Mbappé", "value": 10 },
        { "name": "Messi", "value": 8 },
        { "name": "Haaland", "value": 7 }
      ]
    }
  ]
}
```

Radar example — comparing two players across metrics (one numeric key per
player, each data item is one axis):

```json
{
  "surfaceId": "mbappe-vs-messi",
  "catalogId": "football_catalog",
  "components": [
    { "id": "root", "component": "Column", "children": ["chart"] },
    {
      "id": "chart",
      "component": "Chart",
      "chartType": "radar",
      "title": "Mbappé vs Messi",
      "xKey": "name",
      "yKeys": ["mbappe", "messi"],
      "data": [
        { "name": "Buts", "mbappe": 10, "messi": 8 },
        { "name": "Passes décisives", "mbappe": 4, "messi": 4 },
        { "name": "Buts/90", "mbappe": 1.29, "messi": 0.97 },
        { "name": "Minutes", "mbappe": 698, "messi": 740 },
        { "name": "Titularisations", "mbappe": 8, "messi": 7 },
        { "name": "Penaltys marqués", "mbappe": 1, "messi": 0 }
      ]
    }
  ]
}
```

Heatmap example — a value across two categories (use `x`, `y`, `value`; do NOT
use xKey/yKeys):

```json
{
  "surfaceId": "goals-by-team-stage",
  "catalogId": "football_catalog",
  "components": [
    { "id": "root", "component": "Column", "children": ["chart"] },
    {
      "id": "chart",
      "component": "Chart",
      "chartType": "heatmap",
      "title": "Buts par équipe et par phase",
      "data": [
        { "x": "Group stage", "y": "France", "value": 10 },
        { "x": "Round of 32", "y": "France", "value": 3 },
        { "x": "Group stage", "y": "Spain", "value": 4 },
        { "x": "Round of 32", "y": "Spain", "value": 3 }
      ]
    }
  ]
}
```

Line example — evolution over the tournament, one point per match in
chronological order (query `player_matches` ordered by `match_id`):

```json
{
  "surfaceId": "mbappe-goals-by-match",
  "catalogId": "football_catalog",
  "components": [
    { "id": "root", "component": "Column", "children": ["chart"] },
    {
      "id": "chart",
      "component": "Chart",
      "chartType": "line",
      "title": "Mbappé — buts cumulés match après match",
      "xKey": "name",
      "yKeys": ["value"],
      "data": [
        { "name": "Sénégal", "value": 2 },
        { "name": "Irak", "value": 4 },
        { "name": "Norvège", "value": 4 },
        { "name": "Suède (16es)", "value": 6 }
      ]
    }
  ]
}
```

Rules:
- `catalogId` MUST be exactly `"football_catalog"`. Never invent another value
  (not "chart_catalog", not a URL) — copy this literal string.
- `chartType` is one of `"bar"`, `"line"`, `"pie"`, `"radar"`, `"heatmap"`.
  Pick the best fit: bar/line for rankings & trends, pie for shares of a whole,
  radar for one entity profiled across several metrics (each axis has its own
  scale, so mixing minutes and goals is fine), heatmap for a value across two
  categories, line for an evolution match after match or stage after stage.
- `xKey` is the category key in each data item (usually `"name"`).
- `yKeys` lists the numeric keys to plot (usually `["value"]`).
- Limit `data` to 10 items.
- Data shape depends on the type:
  - bar/line/pie/radar → `[{ "name": "...", "value": <number> }, ...]`
    (radar: each item is one axis; multi-series bar/line: add more numeric keys
    and list them in `yKeys`).
  - heatmap → `[{ "x": "<col>", "y": "<row>", "value": <number> }, ...]`
    (do not use xKey/yKeys for heatmap).
- For a single-value or yes/no answer, do NOT render a chart — reply in text only.
