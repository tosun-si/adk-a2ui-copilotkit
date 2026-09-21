"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";

export type EChartType = "bar" | "line" | "pie" | "radar" | "heatmap";

export interface EChartSpec {
  chartType: EChartType;
  title?: string;
  // Category / x-axis key in each data item (bar/line/pie/radar). Default "name".
  xKey?: string;
  // Numeric keys to plot (bar/line: one or more; pie/radar: first is used).
  yKeys?: string[];
  // Data points. Shape depends on chartType:
  //  - bar/line/pie/radar: { [xKey]: string, [yKey]: number }
  //  - heatmap: { x: string, y: string, value: number }
  data: Array<Record<string, string | number>>;
}

const PALETTE = [
  "#10b981", "#0ea5e9", "#7c3aed", "#e11d48", "#f59e0b",
  "#84cc16", "#06b6d4", "#a855f7", "#065f46", "#f43f5e",
];

function num(v: unknown): number {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

function buildOption(spec: EChartSpec): echarts.EChartsOption {
  const xKey = spec.xKey ?? "name";
  const yKeys = spec.yKeys && spec.yKeys.length > 0 ? spec.yKeys : ["value"];
  const data = spec.data ?? [];
  const title: echarts.EChartsOption["title"] = spec.title
    ? { text: spec.title, left: "center", textStyle: { fontSize: 14 } }
    : undefined;

  switch (spec.chartType) {
    case "bar":
    case "line": {
      const categories = data.map((d) => d[xKey]);
      return {
        color: PALETTE,
        title,
        tooltip: { trigger: "axis" },
        legend: yKeys.length > 1 ? { top: title ? 28 : 4 } : undefined,
        grid: { left: 8, right: 16, bottom: 8, top: 48, containLabel: true },
        xAxis: { type: "category", data: categories as string[] },
        yAxis: { type: "value" },
        series: yKeys.map((k) => ({
          name: k,
          type: spec.chartType as "bar" | "line",
          smooth: spec.chartType === "line",
          data: data.map((d) => num(d[k])),
        })),
      };
    }
    case "pie": {
      const key = yKeys[0];
      return {
        color: PALETTE,
        title,
        tooltip: { trigger: "item" },
        legend: { bottom: 0 },
        series: [
          {
            type: "pie",
            radius: "62%",
            center: ["50%", "52%"],
            data: data.map((d) => ({ name: String(d[xKey]), value: num(d[key]) })),
          },
        ],
      };
    }
    case "radar": {
      // Each data item is one axis; each yKey is one series (entity). This
      // supports both a single profile (yKeys=["value"]) and a comparison of
      // several entities overlaid (e.g. yKeys=["mbappe","messi"]).
      const axes = data.map((d) => String(d[xKey]));
      const maxVal =
        Math.max(1, ...data.flatMap((d) => yKeys.map((k) => num(d[k])))) * 1.15;
      return {
        color: PALETTE,
        title,
        tooltip: {},
        legend: yKeys.length > 1 ? { bottom: 0 } : undefined,
        radar: {
          indicator: axes.map((name) => ({ name, max: maxVal })),
          radius: "60%",
        },
        series: [
          {
            type: "radar",
            data: yKeys.map((k) => ({
              name: k,
              value: data.map((d) => num(d[k])),
              areaStyle: { opacity: 0.12 },
            })),
          },
        ],
      };
    }
    case "heatmap": {
      const xs = [...new Set(data.map((d) => String(d.x)))];
      const ys = [...new Set(data.map((d) => String(d.y)))];
      const points = data.map((d) => [
        xs.indexOf(String(d.x)),
        ys.indexOf(String(d.y)),
        num(d.value),
      ]);
      const maxVal = Math.max(1, ...data.map((d) => num(d.value)));
      return {
        title,
        tooltip: { position: "top" },
        grid: { height: "58%", top: 48, left: 8, right: 16, containLabel: true },
        xAxis: { type: "category", data: xs, splitArea: { show: true } },
        yAxis: { type: "category", data: ys, splitArea: { show: true } },
        visualMap: {
          min: 0,
          max: maxVal,
          calculable: true,
          orient: "horizontal",
          left: "center",
          bottom: 0,
        },
        series: [
          {
            type: "heatmap",
            data: points,
            label: { show: true },
            emphasis: { itemStyle: { shadowBlur: 8, shadowColor: "rgba(0,0,0,0.3)" } },
          },
        ],
      };
    }
  }
}

export function EChart({ spec }: { spec: EChartSpec }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    chart.setOption(buildOption(spec), true);
    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(ref.current);
    return () => {
      ro.disconnect();
      chart.dispose();
    };
  }, [spec]);

  if (!spec.data || spec.data.length === 0) {
    return (
      <div className="my-3 rounded-md border border-dashed border-gray-300 p-4 text-sm text-gray-500">
        Empty chart data.
      </div>
    );
  }

  return (
    <div className="my-4 rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
      <div ref={ref} className="h-72 w-full" />
    </div>
  );
}
