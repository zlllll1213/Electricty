import { DataSourcePanel } from "../components/DataSourcePanel";
import { ForecastChartPanel } from "../components/ForecastChartPanel";
import { MetricCard } from "../components/MetricCard";
import Panel from "../components/Panel";
import { SourceTable } from "../components/SourceTable";

export default function OverviewView({
  overviewCards,
  datasetSource,
  setDatasetSource,
  forecastPeriods,
  setForecastPeriods,
  defaults,
  uploadState,
  setUploadState,
  onRunForecast,
  runResult,
  loading
}) {
  return (
    <div className="module-view is-active" data-view="overview">
      <section className="hero-board">
        <div>
          <p className="eyebrow">National Module</p>
          <h2 className="hero-title">国家预测模块总览屏</h2>
          <p className="hero-copy">总览页负责参数、指标和图表，报告与来源页拆到独立视图中，靠近目标仓库的首页组织方式。</p>
        </div>
        <button className="primary-button" type="button" onClick={onRunForecast} disabled={loading.run}>
          {loading.run ? "正在运行..." : "运行预测"}
        </button>
      </section>

      <Panel kicker="Runbook" title="数据与参数" note="保留国家模块自己的数据语义，但布局和信息组织尽量贴近目标仓库。">
        <div className="content-grid">
          <DataSourcePanel
            datasetSource={datasetSource}
            setDatasetSource={setDatasetSource}
            forecastPeriods={forecastPeriods}
            setForecastPeriods={setForecastPeriods}
            uploadState={uploadState}
            setUploadState={setUploadState}
            defaults={defaults}
          />

          <section className="panel-card">
            <h3>运行摘要</h3>
            <div className="metric-grid">
              {overviewCards.map((item) => (
                <MetricCard key={item.label} label={item.label} value={item.value} />
              ))}
            </div>
          </section>
        </div>
      </Panel>

      <Panel kicker="Dashboard" title="图表与结果" note="图表和结果表仍然独立，但通过 Panel 组件和模块视图包装对齐未来并仓的结构。">
        <div className="page-grid">
          <ForecastChartPanel
            title="历史月度趋势"
            caption="与仓库里的预测页一致，图表被放进独立业务卡片里。"
            series={runResult.charts.history}
          />
          <ForecastChartPanel
            title="未来预测区间"
            caption="保留国家模块独立的数据含义，但界面组织向仓库对齐。"
            series={runResult.charts.forecast}
          />
          <ForecastChartPanel
            title="季节性分布"
            caption="用单独卡片展示月度结构，而不是堆进一个长页面。"
            series={runResult.charts.seasonality}
          />
          <SourceTable rows={runResult.forecast} title="预测结果表" />
        </div>
      </Panel>
    </div>
  );
}
