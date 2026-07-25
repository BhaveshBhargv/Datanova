import type { ChartData } from "./eda";
import type { EChartsOption } from "echarts";

const INDIGO = "#4f46e5";

export function buildOption(cd: ChartData): EChartsOption {
  const title: EChartsOption["title"] = {
    text: cd.title,
    left: "center",
    textStyle: { fontSize: 14, fontWeight: 600, color: "#334155" },
  };
  const data0 = cd.series[0]?.data as unknown;

  switch (cd.type) {
    case "histogram":
    case "bar":
      return {
        title,
        tooltip: { trigger: "axis" },
        grid: { left: 56, right: 20, top: 48, bottom: 90 },
        xAxis: {
          type: "category",
          data: cd.categories as string[],
          name: cd.x_label ?? undefined,
          nameLocation: "middle",
          nameGap: 70,
          axisLabel: {
            rotate: (cd.categories?.length ?? 0) > 6 ? 45 : 0,
            fontSize: 10,
          },
        },
        yAxis: { type: "value", name: cd.y_label ?? undefined },
        series: [
          {
            type: "bar",
            data: data0 as number[],
            itemStyle: { color: INDIGO },
            barCategoryGap: cd.type === "histogram" ? "2%" : "20%",
          },
        ],
      };

    case "pie":
      return {
        title,
        tooltip: { trigger: "item" },
        legend: { bottom: 0, type: "scroll" },
        series: [
          {
            type: "pie",
            radius: ["35%", "62%"],
            center: ["50%", "48%"],
            data: data0 as { name: string; value: number }[],
          },
        ],
      };

    case "box":
      return {
        title,
        tooltip: { trigger: "item" },
        grid: { left: 56, right: 20, top: 48, bottom: 60 },
        xAxis: { type: "category", data: cd.categories as string[] },
        yAxis: { type: "value", name: cd.y_label ?? undefined },
        series: [
          { type: "boxplot", data: data0 as number[][], itemStyle: { color: "#e0e7ff", borderColor: INDIGO } },
          {
            type: "scatter",
            data: (cd.extra.outliers as number[][]) ?? [],
            symbolSize: 6,
            itemStyle: { color: "#ef4444" },
          },
        ],
      };

    case "scatter":
      return {
        title,
        tooltip: { trigger: "item" },
        grid: { left: 56, right: 24, top: 48, bottom: 56 },
        xAxis: { type: "value", name: cd.x_label ?? undefined, scale: true },
        yAxis: { type: "value", name: cd.y_label ?? undefined, scale: true },
        series: [
          {
            type: "scatter",
            data: data0 as number[][],
            symbolSize: 7,
            itemStyle: { color: INDIGO, opacity: 0.7 },
          },
        ],
      };

    case "correlation_heatmap":
      return {
        title,
        tooltip: { position: "top" },
        grid: { left: 90, right: 20, top: 48, bottom: 90 },
        xAxis: {
          type: "category",
          data: cd.extra.x as string[],
          axisLabel: { rotate: 45, fontSize: 10 },
        },
        yAxis: { type: "category", data: cd.extra.y as string[] },
        visualMap: {
          min: -1,
          max: 1,
          calculable: true,
          orient: "horizontal",
          left: "center",
          bottom: 8,
          inRange: { color: ["#2166ac", "#f7f7f7", "#b2182b"] },
        },
        series: [
          {
            type: "heatmap",
            data: data0 as number[][],
            label: {
              show: true,
              fontSize: 10,
              formatter: (p: any) =>
                p.data[2] === null ? "" : Number(p.data[2]).toFixed(2),
            },
          },
        ],
      };

    case "line":
      return {
        title,
        tooltip: { trigger: "axis" },
        grid: { left: 56, right: 24, top: 48, bottom: 70 },
        xAxis: {
          type: "category",
          data: cd.categories as string[],
          name: cd.x_label ?? undefined,
          axisLabel: { rotate: (cd.categories?.length ?? 0) > 8 ? 45 : 0, fontSize: 10 },
        },
        yAxis: { type: "value", name: cd.y_label ?? undefined },
        series: [
          { type: "line", data: data0 as number[], smooth: true, itemStyle: { color: INDIGO } },
        ],
      };

    default:
      return { title };
  }
}
