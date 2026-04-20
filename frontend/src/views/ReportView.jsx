import { useState } from "react";

import { requestJson } from "../lib/api";

export default function ReportView({ llmForm, runResult, setRunResult, showToast }) {
  const [question, setQuestion] = useState("");
  const [answerState, setAnswerState] = useState({ answer: "", message: "" });

  async function handlePolish() {
    const response = await requestJson("/api/national/report/polish", {
      method: "POST",
      body: JSON.stringify({
        draft_report: runResult.report.draft,
        context: {
          latest_value: runResult.stats?.latest_value,
          forecast_average: averageForecast(runResult.forecast),
          forecast_periods: runResult.forecast.length
        },
        llm_config: llmForm
      })
    });

    setRunResult((current) => ({
      ...current,
      report: {
        draft: response.data.report_text,
        status: response.data.status,
        status_message: response.data.status_message
      }
    }));
    showToast("已更新报告内容", "success");
  }

  async function handleAsk() {
    const response = await requestJson("/api/national/qa", {
      method: "POST",
      body: JSON.stringify({
        question,
        history: runResult.history,
        forecast: runResult.forecast,
        stats: runResult.stats
      })
    });
    setAnswerState({ answer: response.data.answer, message: response.data.status_message });
  }

  if (!runResult.report.draft) {
    return <div className="status-banner">先在总览页运行一次预测，这里才会生成报告和问答上下文。</div>;
  }

  return (
    <div className="report-grid">
      <section className="section-card report-card">
        <div className="panel-heading">
          <h3>自动分析报告</h3>
          <button className="secondary-button" type="button" onClick={() => handlePolish().catch((error) => showToast(error.message, "error"))}>
            重新润色
          </button>
        </div>
        <p className="muted-text">{runResult.report.status_message}</p>
        <textarea value={runResult.report.draft} readOnly rows={20} />
      </section>

      <section className="section-card report-card">
        <h3>问答工作台</h3>
        <label className="field-block">
          <span>问题</span>
          <input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="例如：未来一年用电量趋势如何？" />
        </label>
        <button className="primary-button" type="button" onClick={() => handleAsk().catch((error) => showToast(error.message, "error"))} disabled={!question.trim()}>
          发送问题
        </button>
        <p className="muted-text">{answerState.message}</p>
        <div className="qa-answer">{answerState.answer || "提交问题后，这里会显示回答。"}</div>
      </section>
    </div>
  );
}

function averageForecast(forecast) {
  if (!forecast?.length) {
    return 0;
  }
  return forecast.reduce((sum, point) => sum + point.forecast, 0) / forecast.length;
}
