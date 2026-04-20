import { SourceTable } from "../components/SourceTable";

export default function SourcesView({ defaultDataset, meta, uploadState, runResult }) {
  const activeRawRows = runResult.raw_records?.length ? runResult.raw_records : defaultDataset?.raw_records ?? [];
  const activeCleanRows =
    runResult.history?.length
      ? runResult.history.map((item) => ({
          date: item.date,
          consumption_billion_kwh: item.value,
          is_imputed: item.is_imputed,
          source: item.source,
          source_url: item.source_url,
          note: item.note
        }))
      : defaultDataset?.cleaned_records?.map((item) => ({
          date: item.date,
          consumption_billion_kwh: item.value,
          is_imputed: item.is_imputed,
          source: item.source,
          source_url: item.source_url,
          note: item.note
        })) ?? [];

  return (
    <div className="page-grid">
      <section className="section-card markdown-card">
        <h3>字段说明</h3>
        <pre>{meta?.documents?.data_schema_markdown ?? "加载中..."}</pre>
      </section>
      <section className="section-card markdown-card">
        <h3>官方数据来源说明</h3>
        <pre>{meta?.documents?.official_sources_markdown ?? "加载中..."}</pre>
      </section>
      <SourceTable rows={activeCleanRows} title="清洗后数据" />
      <SourceTable rows={activeRawRows} title="原始来源数据" />
      {uploadState.validation?.result ? (
        <section className="section-card compact">
          <h3>上传校验摘要</h3>
          <p className="muted-text">
            {uploadState.validation.result.filename || uploadState.filename} 已通过校验，历史区间为{" "}
            {uploadState.validation.result.summary.history_start} 至{" "}
            {uploadState.validation.result.summary.history_end}。
          </p>
        </section>
      ) : null}
    </div>
  );
}
