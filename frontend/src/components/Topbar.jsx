export default function Topbar({ title, note, sourceLabel, loading, savedLlmConfig, reportStatus }) {
  return (
    <header className="topbar">
      <div>
        <p className="eyebrow">当前模块</p>
        <h2 className="topbar-title">{title}</h2>
        <p className="topbar-copy">{note}</p>
      </div>
      <div className="topbar-actions">
        <div className="topbar-meta">
          <span className="topbar-chip">Source</span>
          <strong>{sourceLabel}</strong>
        </div>
        <div className="topbar-meta">
          <span className="topbar-chip">LLM</span>
          <strong>{savedLlmConfig?.enabled ? savedLlmConfig.model : "未配置"}</strong>
        </div>
        <div className="topbar-meta">
          <span className="topbar-chip">Status</span>
          <strong>{loading ? "运行中" : reportStatus || "待命"}</strong>
        </div>
        <div className="topbar-meta">
          <span className="topbar-chip">Report</span>
          <strong>{reportStatus || "--"}</strong>
        </div>
        <div className="topbar-meta">
          <span className="topbar-chip">Runtime</span>
          <strong>{loading ? "运行中" : "待命"}</strong>
        </div>
      </div>
    </header>
  );
}
