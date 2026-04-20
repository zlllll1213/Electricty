import { NAV_ITEMS } from "../lib/nationalUtils";

export default function Sidebar({ currentView, onNavigate, runResult, savedLlmConfig }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <p className="eyebrow">National Power</p>
        <h1>国家预测模块</h1>
        <p className="sidebar-copy">按照 `PowerModel` 的壳层与导航语义组织，便于后续直接并入仓库。</p>
      </div>

      <div className="sidebar-status">
        <div className="status-card">
          <span className="status-label">当前数据源</span>
          <strong>{runResult.source_label || "默认国家数据"}</strong>
        </div>
        <div className="status-card">
          <span className="status-label">最近报告</span>
          <strong>{runResult.report?.draft ? "已生成" : "未生成"}</strong>
        </div>
        <div className="status-card">
          <span className="status-label">模型配置</span>
          <strong>{savedLlmConfig?.enabled ? savedLlmConfig.model : "未配置"}</strong>
        </div>
      </div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.key}
            type="button"
            className={`sidebar-link ${currentView === item.key ? "is-active" : ""}`.trim()}
            onClick={() => onNavigate(item.key)}
          >
            <span className="sidebar-link-icon">{item.icon}</span>
            <span className="sidebar-link-main">
              <span className="sidebar-link-title">{item.title}</span>
              <span className="sidebar-link-note">{item.note}</span>
            </span>
            <span className="sidebar-link-indicator" />
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <p className="subtle-note">当前模块已对齐成“组件壳层 + views + requestJson + Panel”的并仓形态。</p>
      </div>
    </aside>
  );
}
