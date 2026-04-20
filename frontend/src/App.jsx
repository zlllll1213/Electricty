import { Suspense, lazy, startTransition, useEffect, useMemo, useState } from "react";

import Sidebar from "./components/Sidebar";
import Toast from "./components/Toast";
import Topbar from "./components/Topbar";
import { requestJson } from "./lib/api";
import { VIEW_META } from "./lib/nationalUtils";

const ModelConfigView = lazy(() => import("./views/ModelConfigView"));
const OverviewView = lazy(() => import("./views/OverviewView"));
const ReportView = lazy(() => import("./views/ReportView"));
const SourcesView = lazy(() => import("./views/SourcesView"));

const STORAGE_KEYS = {
  activeView: "national_power_active_view"
};

const DEFAULT_LLM_FORM = {
  enabled: false,
  provider: "OpenAI-Compatible",
  base_url: "",
  model: "",
  api_key: ""
};

const EMPTY_RUN = {
  history: [],
  forecast: [],
  stats: null,
  diagnostics: {},
  report: { draft: "", status: "local", status_message: "" },
  charts: { history: [], forecast: [], seasonality: [] },
  raw_records: [],
  source_label: ""
};

export default function App() {
  const [currentView, setCurrentView] = useState(localStorage.getItem(STORAGE_KEYS.activeView) || "overview");
  const [meta, setMeta] = useState(null);
  const [defaultDataset, setDefaultDataset] = useState(null);
  const [runResult, setRunResult] = useState(EMPTY_RUN);
  const [datasetSource, setDatasetSource] = useState("default");
  const [forecastPeriods, setForecastPeriods] = useState(12);
  const [uploadState, setUploadState] = useState({ filename: "", csvContent: "", validation: null });
  const [llmForm, setLlmForm] = useState(DEFAULT_LLM_FORM);
  const [savedLlmConfig, setSavedLlmConfig] = useState(null);
  const [loading, setLoading] = useState({ boot: true, run: false });
  const [toast, setToast] = useState({ visible: false, tone: "info", message: "" });

  const currentMeta = VIEW_META[currentView] || VIEW_META.overview;

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.activeView, currentView);
  }, [currentView]);

  useEffect(() => {
    async function boot() {
      try {
        const [metaPayload, datasetPayload] = await Promise.all([
          requestJson("/api/national/meta"),
          requestJson("/api/national/datasets/default")
        ]);

        setMeta(metaPayload.data);
        setDefaultDataset(datasetPayload.data);
        setForecastPeriods(metaPayload.data.defaults.forecast_periods);

        try {
          const llmPayload = await requestJson("/api/national/llm/config");
          setSavedLlmConfig(llmPayload.data.config);
          setLlmForm((current) => ({
            ...current,
            enabled: llmPayload.data.config.enabled,
            provider: llmPayload.data.config.provider,
            base_url: llmPayload.data.config.base_url,
            model: llmPayload.data.config.model,
            api_key: ""
          }));
        } catch {
          setSavedLlmConfig(null);
        }
      } catch (error) {
        showToast(error.message, "error");
      } finally {
        setLoading((current) => ({ ...current, boot: false }));
      }
    }

    boot();
  }, []);

  const overviewCards = useMemo(() => {
    const stats = runResult.stats;
    return [
      { label: "历史样本数", value: stats ? String(stats.record_count) : "--" },
      { label: "最新月份", value: stats ? stats.latest_month : "--" },
      { label: "最新用电量", value: stats ? `${stats.latest_value.toFixed(1)} 亿千瓦时` : "--" },
      { label: "历史均值", value: stats ? `${stats.average_value.toFixed(1)} 亿千瓦时` : "--" }
    ];
  }, [runResult.stats]);

  function showToast(message, tone = "info") {
    setToast({ visible: true, tone, message });
    window.setTimeout(() => {
      setToast((current) => ({ ...current, visible: false }));
    }, 2600);
  }

  function navigate(view) {
    startTransition(() => {
      setCurrentView(view);
    });
  }

  async function handleRunForecast() {
    setLoading((current) => ({ ...current, run: true }));
    try {
      const response = await requestJson("/api/national/forecast/run", {
        method: "POST",
        body: JSON.stringify({
          dataset_source: datasetSource,
          forecast_periods: Number(forecastPeriods),
          csv_content: datasetSource === "uploaded" ? uploadState.csvContent : null
        })
      });
      setRunResult(response.data);
      navigate("overview");
      showToast(`已完成 ${response.data.source_label} 的预测运行`, "success");
    } catch (error) {
      showToast(error.message, "error");
    } finally {
      setLoading((current) => ({ ...current, run: false }));
    }
  }

  async function handleTestLlm() {
    const response = await requestJson("/api/national/llm/test", {
      method: "POST",
      body: JSON.stringify({
        llm_config: llmForm
      })
    });
    showToast(response.data.message, "success");
  }

  async function handleSaveLlm() {
    const response = await requestJson("/api/national/llm/config", {
      method: "POST",
      body: JSON.stringify(llmForm)
    });
    setSavedLlmConfig(response.data.config);
    setLlmForm((current) => ({ ...current, api_key: "" }));
    showToast("模型配置已保存", "success");
  }

  async function handleClearLlm() {
    await requestJson("/api/national/llm/config", { method: "DELETE" });
    setSavedLlmConfig(null);
    setLlmForm(DEFAULT_LLM_FORM);
    showToast("模型配置已清除", "success");
  }

  return (
    <div className="app-shell repo-shell">
      <Sidebar
        currentView={currentView}
        onNavigate={navigate}
        runResult={runResult}
        savedLlmConfig={savedLlmConfig}
      />

      <main className="content-shell repo-content">
        <Topbar
          title={currentMeta.title || currentMeta.name}
          note={currentMeta.note}
          sourceLabel={runResult.source_label || "国家能源局真实公开数据"}
          loading={loading.run}
          savedLlmConfig={savedLlmConfig}
          reportStatus={runResult.report?.status}
        />

        <Suspense fallback={<ViewSkeleton viewName={currentMeta.name} />}>
          <div className="view-stack">
            {currentView === "overview" ? (
              <OverviewView
                overviewCards={overviewCards}
                datasetSource={datasetSource}
                setDatasetSource={setDatasetSource}
                forecastPeriods={forecastPeriods}
                setForecastPeriods={setForecastPeriods}
                defaults={meta?.defaults}
                uploadState={uploadState}
                setUploadState={setUploadState}
                onRunForecast={handleRunForecast}
                runResult={runResult}
                loading={loading}
              />
            ) : null}

            {currentView === "model" ? (
              <ModelConfigView
                llmForm={llmForm}
                setLlmForm={setLlmForm}
                savedLlmConfig={savedLlmConfig}
                onTest={() => handleTestLlm().catch((error) => showToast(error.message, "error"))}
                onSave={() => handleSaveLlm().catch((error) => showToast(error.message, "error"))}
                onClear={() => handleClearLlm().catch((error) => showToast(error.message, "error"))}
              />
            ) : null}

            {currentView === "report" ? (
              <ReportView
                llmForm={llmForm}
                runResult={runResult}
                setRunResult={setRunResult}
                showToast={showToast}
              />
            ) : null}

            {currentView === "sources" ? (
              <SourcesView
                defaultDataset={defaultDataset}
                meta={meta}
                uploadState={uploadState}
                runResult={runResult}
              />
            ) : null}
          </div>
        </Suspense>
      </main>

      <Toast toast={toast} />
    </div>
  );
}

function ViewSkeleton({ viewName }) {
  return (
    <div className="view-stack">
      <section className="section-card skeleton-card">
        <p className="eyebrow">Loading View</p>
        <h3>{viewName}</h3>
        <div className="skeleton-row wide" />
        <div className="skeleton-row" />
        <div className="skeleton-grid">
          <div className="skeleton-tile" />
          <div className="skeleton-tile" />
          <div className="skeleton-tile" />
        </div>
      </section>
    </div>
  );
}
