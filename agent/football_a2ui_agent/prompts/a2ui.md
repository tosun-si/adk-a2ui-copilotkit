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

Minimal valid example for "top 5 scorers of France" (a bar chart):

```json
{
  "surfaceId": "top-scorers-france",
  "catalogId": "football_catalog",
  "components": [
    { "id": "root", "component": "Column", "children": ["chart"] },
    {
      "id": "chart",
      "component": "Chart",
      "chartType": "bar",
      "title": "Top 5 buteurs — France",
      "xKey": "name",
      "yKeys": ["value"],
      "data": [
        { "name": "Mbappé", "value": 8 },
        { "name": "Giroud", "value": 4 }
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
        { "name": "Buts", "mbappe": 8, "messi": 7 },
        { "name": "Passes décisives", "mbappe": 2, "messi": 3 },
        { "name": "Dribbles/90", "mbappe": 3.1, "messi": 2.6 },
        { "name": "Tirs/90", "mbappe": 4.2, "messi": 3.8 }
      ]
    }
  ]
}
```

Heatmap example — a value across two categories (use `x`, `y`, `value`; do NOT
use xKey/yKeys):

```json
{
  "surfaceId": "goals-by-team-phase",
  "catalogId": "football_catalog",
  "components": [
    { "id": "root", "component": "Column", "children": ["chart"] },
    {
      "id": "chart",
      "component": "Chart",
      "chartType": "heatmap",
      "title": "Buts par équipe et par mi-temps",
      "data": [
        { "x": "1re mi-temps", "y": "France", "value": 5 },
        { "x": "2e mi-temps", "y": "France", "value": 3 },
        { "x": "1re mi-temps", "y": "Argentine", "value": 4 },
        { "x": "2e mi-temps", "y": "Argentine", "value": 6 }
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
  radar for one entity profiled across several metrics, heatmap for a value
  across two categories.
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
