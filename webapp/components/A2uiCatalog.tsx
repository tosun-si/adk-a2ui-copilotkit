"use client";

import { z } from "zod";
import { createCatalog } from "@copilotkit/a2ui-renderer";
import { EChart, type EChartSpec } from "./EChart";

// Fixed, short, unambiguous catalog id. In dynamic mode the LLM fills the
// surface's `catalogId` itself and will hallucinate arbitrary values
// (e.g. "chart_catalog") if not told a literal one. We register under this
// exact id AND instruct the agent (prompts/a2ui.md) to always use it verbatim.
// A short token is copied far more reliably by the model than a long URL id.
export const CATALOG_ID = "football_catalog";

// Dynamic-A2UI best practice: component props are LLM-facing. Their `.describe()`
// text is injected into the agent as the catalog schema, so the model knows how
// to fill them. We expose ONE Chart component backed by ECharts, with five
// chart types the LLM can pick from at runtime — this is what makes the
// "agent drives the UI" story rich (it chooses radar for profiles, heatmap for
// matrices, etc.).
//
// `includeBasicCatalog: true` also exposes A2UI's built-in primitives (Column,
// Heading, Text, …) so the LLM can compose a real declarative surface.
const definitions = {
  Chart: {
    description:
      "A data visualization backed by ECharts. Pick the chartType that best " +
      "fits the question: 'bar'/'line' for rankings & trends, 'pie' for shares, " +
      "'radar' for a multi-metric profile of one entity, 'heatmap' for a matrix " +
      "of two categories vs a value.",
    props: z.object({
      chartType: z
        .enum(["bar", "line", "pie", "radar", "heatmap"])
        .describe(
          "bar|line: rankings/trends. pie: parts of a whole. radar: one " +
            "entity across several metrics. heatmap: value across two categories."
        ),
      title: z.string().optional().describe("Short chart title."),
      xKey: z
        .string()
        .optional()
        .describe(
          "For bar/line/pie/radar: the key holding the category/axis label in " +
            "each data item (usually 'name'). Ignored for heatmap."
        ),
      yKeys: z
        .array(z.string())
        .optional()
        .describe(
          "Numeric keys to plot. bar/line: one or more series (e.g. ['value'] " +
            "or ['goals','assists']). pie: the first key. radar: ONE key per " +
            "entity — use several to compare entities (e.g. ['mbappe','messi']). " +
            "Ignored for heatmap."
        ),
      data: z
        .array(z.record(z.union([z.string(), z.number()])))
        .describe(
          "The data points (max 10). Shape depends on chartType:\n" +
            "- bar/line/pie: [{\"name\":\"Mbappé\",\"value\":8}, ...].\n" +
            "- radar: each item is ONE axis/metric; add one numeric key per " +
            "entity, e.g. [{\"name\":\"Buts\",\"mbappe\":8,\"messi\":7}, " +
            "{\"name\":\"Passes\",\"mbappe\":2,\"messi\":3}] with " +
            "yKeys=['mbappe','messi'].\n" +
            "- heatmap: [{\"x\":\"1st half\",\"y\":\"France\",\"value\":5}, ...] " +
            "with x, y (categories) and value (number)."
        ),
    }),
  },
};

interface ChartProps {
  chartType?: EChartSpec["chartType"];
  title?: string;
  xKey?: string;
  yKeys?: string[];
  data?: EChartSpec["data"];
}

const renderers = {
  Chart: ({ props }: { props: ChartProps }) => {
    if (!props.data || props.data.length === 0) return null;
    const spec: EChartSpec = {
      chartType: props.chartType ?? "bar",
      title: props.title,
      xKey: props.xKey,
      yKeys: props.yKeys,
      data: props.data,
    };
    return <EChart spec={spec} />;
  },
};

// includeBasicCatalog: true → our catalog is a superset (all basic components
// + Chart), so the LLM can compose surfaces (Column/Text/…) and the processor
// resolves everything under CATALOG_ID.
export const footballCatalog = createCatalog(definitions, renderers, {
  catalogId: CATALOG_ID,
  includeBasicCatalog: true,
});
