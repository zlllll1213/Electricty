import Panel from "../components/Panel";

export default function ModelConfigView({ llmForm, setLlmForm, savedLlmConfig, onTest, onSave, onClear }) {
  function updateField(key, value) {
    setLlmForm((current) => ({ ...current, [key]: value }));
  }

  return (
    <div className="module-view is-active" data-view="model">
      <div className="page-grid">
        <Panel kicker="LLM" title="模型设置" note="将国家模块的模型配置组织成与目标仓库一致的设置页形态。">
          <div className="panel-heading">
            <label className="toggle-field">
              <input
                type="checkbox"
                checked={llmForm.enabled}
                onChange={(event) => updateField("enabled", event.target.checked)}
              />
              <span>启用增强</span>
            </label>
          </div>

          <div className="two-col-grid">
            <label className="field-block">
              <span>Provider</span>
              <input value={llmForm.provider} onChange={(event) => updateField("provider", event.target.value)} />
            </label>
            <label className="field-block">
              <span>Model</span>
              <input value={llmForm.model} onChange={(event) => updateField("model", event.target.value)} />
            </label>
          </div>

          <label className="field-block">
            <span>Base URL</span>
            <input value={llmForm.base_url} onChange={(event) => updateField("base_url", event.target.value)} />
          </label>
          <label className="field-block">
            <span>API Key</span>
            <input
              type="password"
              value={llmForm.api_key}
              onChange={(event) => updateField("api_key", event.target.value)}
              placeholder={savedLlmConfig?.has_api_key ? "已保存密钥，可留空保持不变" : "输入你的 API Key"}
            />
          </label>

          <div className="action-row">
            <button className="secondary-button" type="button" onClick={onTest}>
              测试连接
            </button>
            <button className="primary-button" type="button" onClick={onSave}>
              保存配置
            </button>
            <button className="secondary-button" type="button" onClick={onClear}>
              清除配置
            </button>
          </div>
        </Panel>

        <Panel kicker="Runtime" title="当前接入状态" note="把运行时摘要和提示拆到侧栏信息卡，靠近目标仓库的模型设置页结构。">
          <div className="info-panel">
            <span>当前已保存配置</span>
            <strong>{savedLlmConfig?.enabled ? `${savedLlmConfig.model} @ ${savedLlmConfig.base_url}` : "暂无"}</strong>
            <small>{savedLlmConfig?.masked_api_key || "尚未保存 API Key"}</small>
          </div>
        </Panel>
      </div>
    </div>
  );
}
