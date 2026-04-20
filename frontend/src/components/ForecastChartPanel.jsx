import { Suspense, lazy } from "react";

const Plot = lazy(async () => {
  const [{ default: createPlotlyComponent }, plotlyModule] = await Promise.all([
    import("react-plotly.js/factory"),
    import("plotly.js-dist-min")
  ]);
  const Plotly = plotlyModule.default || plotlyModule;
  return { default: createPlotlyComponent(Plotly) };
});

function buildPlotTrace(series) {
  if (series.chart_type === "bar") {
    return {
      type: "bar",
      name: series.name,
      x: series.x,
      y: series.y,
      marker: { color: series.color }
    };
  }

  return {
    type: "scatter",
    mode: "lines",
    fill: series.chart_type === "area" ? "tozeroy" : undefined,
    name: series.name,
    x: series.x,
    y: series.y,
    line: { color: series.color, width: 3 }
  };
}

export function ForecastChartPanel({ title, caption, series }) {
  if (!series?.length) {
    return (
      <section className="section-card chart-card">
        <h3>{title}</h3>
        <p className="muted-text">{caption}</p>
        <div className="empty-state">运行一次预测后，这里会出现图表。</div>
      </section>
    );
  }

  return (
    <section className="section-card chart-card">
      <h3>{title}</h3>
      <p className="muted-text">{caption}</p>
      <Suspense fallback={<div className="chart-skeleton">图表模块正在加载...</div>}>
        <Plot
          data={series.map(buildPlotTrace)}
          layout={{
            autosize: true,
            height: 320,
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "#fdfdfb",
            margin: { l: 42, r: 16, t: 20, b: 42 },
            font: { family: "IBM Plex Sans, PingFang SC, sans-serif" },
            xaxis: { showgrid: false },
            yaxis: { gridcolor: "rgba(15, 23, 42, 0.08)" },
            legend: { orientation: "h", y: 1.15 }
          }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: "100%" }}
        />
      </Suspense>
    </section>
  );
}
