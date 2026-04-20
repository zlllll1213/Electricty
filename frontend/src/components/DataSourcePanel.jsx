import { requestJson } from "../lib/api";

export function DataSourcePanel({
  datasetSource,
  setDatasetSource,
  forecastPeriods,
  setForecastPeriods,
  uploadState,
  setUploadState,
  defaults
}) {
  async function handleFileChange(event) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    const csvContent = await file.text();
    setUploadState({ filename: file.name, csvContent, validation: { loading: true } });

    try {
      const response = await requestJson("/api/national/datasets/validate", {
        method: "POST",
        body: JSON.stringify({ csv_content: csvContent, filename: file.name })
      });
      setUploadState({
        filename: file.name,
        csvContent,
        validation: { loading: false, result: response.data, error: "" }
      });
    } catch (error) {
      setUploadState({
        filename: file.name,
        csvContent,
        validation: { loading: false, result: null, error: error.message }
      });
    }
  }

  const validation = uploadState.validation;

  return (
    <section className="section-card">
      <h3>数据与参数</h3>
      <label className="field-block">
        <span>数据源</span>
        <select value={datasetSource} onChange={(event) => setDatasetSource(event.target.value)}>
          <option value="default">国家能源局真实公开数据</option>
          <option value="uploaded">上传我整理的新 CSV</option>
        </select>
      </label>

      <label className="field-block">
        <span>预测月数</span>
        <input
          type="range"
          min={defaults?.forecast_min ?? 6}
          max={defaults?.forecast_max ?? 12}
          step="1"
          value={forecastPeriods}
          onChange={(event) => setForecastPeriods(event.target.value)}
        />
        <small>{forecastPeriods} 个月</small>
      </label>

      {datasetSource === "uploaded" ? (
        <div className="upload-block">
          <label className="secondary-button">
            选择 CSV 文件
            <input type="file" accept=".csv,text/csv" onChange={handleFileChange} hidden />
          </label>
          <p className="upload-filename">{uploadState.filename || "尚未选择文件"}</p>
          {validation?.loading ? <small>正在校验上传数据...</small> : null}
          {validation?.error ? <small className="text-error">{validation.error}</small> : null}
          {validation?.result ? (
            <small>
              校验通过：{validation.result.summary.clean_record_count} 条清洗后记录，
              插值补齐 {validation.result.summary.imputed_count} 条。
            </small>
          ) : null}
        </div>
      ) : (
        <p className="muted-text">默认加载仓库内的国家能源局月度真实公开数据。</p>
      )}
    </section>
  );
}
