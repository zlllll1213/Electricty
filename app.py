from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from src.analysis.qa_engine import RuleBasedQAEngine
from src.analysis.report_generator import generate_report
from src.config import APP_CONFIG, LLM_PROVIDER_PRESET_MAP, LLM_PROVIDER_PRESETS
from src.data_loader import DataValidationError, load_dataset
from src.forecast.sarima_model import ForecastingError, SarimaForecaster
from src.llm.client import LLMClient, LLMConfig
from src.preprocess import DataProcessingError, clean_monthly_data, compute_basic_statistics
from src.visualization import (
    build_forecast_chart,
    build_history_chart,
    build_seasonality_chart,
)


def save_report(report_text: str) -> Path:
    APP_CONFIG.report_output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = APP_CONFIG.report_output_dir / f"electricity_report_{timestamp}.txt"
    output_path.write_text(report_text, encoding="utf-8")
    return output_path


def inject_page_style() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(227, 244, 234, 0.9), transparent 28%),
                radial-gradient(circle at top right, rgba(255, 236, 210, 0.9), transparent 25%),
                linear-gradient(180deg, #f7fbf8 0%, #fcfaf5 100%);
        }
        .hero-card {
            padding: 1.2rem 1.4rem;
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.82);
            border: 1px solid rgba(15, 76, 92, 0.08);
            box-shadow: 0 16px 40px rgba(15, 23, 42, 0.06);
            margin-bottom: 1rem;
        }
        .hero-title {
            font-size: 1.9rem;
            font-weight: 700;
            color: #12343b;
            margin-bottom: 0.45rem;
        }
        .hero-subtitle {
            color: #486169;
            line-height: 1.7;
            font-size: 0.98rem;
        }
        div[data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.84);
            border: 1px solid rgba(15, 76, 92, 0.08);
            border-radius: 18px;
            padding: 0.7rem 0.9rem;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.04);
        }
        div[data-testid="stExpander"] {
            border-radius: 16px;
            border: 1px solid rgba(15, 76, 92, 0.08);
            background: rgba(255, 255, 255, 0.82);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_session_state() -> None:
    defaults = {
        "llm_enabled": False,
        "llm_provider_preset": LLM_PROVIDER_PRESETS[0].key,
        "llm_provider": LLM_PROVIDER_PRESETS[0].display_name,
        "llm_base_url": LLM_PROVIDER_PRESETS[0].endpoint,
        "llm_model": LLM_PROVIDER_PRESETS[0].default_model,
        "llm_api_key": "",
        "llm_test_status": "",
        "llm_test_message": "",
        "report_text": "",
        "report_signature": "",
        "report_origin": "local",
        "report_status_message": "",
        "qa_answer": "",
        "qa_origin": "",
        "qa_status_message": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def apply_provider_preset() -> None:
    preset_key = st.session_state.get("llm_provider_preset")
    preset = LLM_PROVIDER_PRESET_MAP.get(preset_key)
    if preset is None:
        return
    st.session_state["llm_provider"] = preset.display_name
    st.session_state["llm_base_url"] = preset.endpoint
    if not st.session_state.get("llm_model", "").strip() or st.session_state.get("llm_model") in {
        existing.default_model for existing in LLM_PROVIDER_PRESETS
    }:
        st.session_state["llm_model"] = preset.default_model


def clear_api_key() -> None:
    st.session_state["llm_api_key"] = ""


def test_llm_connection() -> None:
    client = build_llm_client()
    success, message = client.test_connection()
    st.session_state["llm_test_status"] = "success" if success else "error"
    st.session_state["llm_test_message"] = message


def build_report_signature(clean_df: pd.DataFrame, forecast_df: pd.DataFrame, forecast_periods: int) -> str:
    history_end = clean_df[APP_CONFIG.date_col].max().strftime("%Y-%m")
    forecast_end = forecast_df[APP_CONFIG.date_col].max().strftime("%Y-%m")
    return f"{history_end}|{forecast_end}|{forecast_periods}|{len(clean_df)}"


def reset_report_state(report_text: str, report_signature: str) -> None:
    st.session_state["report_text"] = report_text
    st.session_state["report_signature"] = report_signature
    st.session_state["report_origin"] = "local"
    st.session_state["report_status_message"] = "当前显示的是本地规则报告。"


def apply_cloud_report(report_draft: str, llm_client: LLMClient, context: dict[str, float | int]) -> None:
    polished = llm_client.polish_report(report_draft, context=context)
    st.session_state["report_text"] = polished
    if llm_client.last_report_used_cloud:
        st.session_state["report_origin"] = "cloud"
        st.session_state["report_status_message"] = "本次报告已由云端大模型润色。"
    elif llm_client.last_report_error:
        st.session_state["report_origin"] = "local"
        st.session_state["report_status_message"] = f"云端润色失败，已回退到本地规则报告：{llm_client.last_report_error}"
    else:
        st.session_state["report_origin"] = "local"
        st.session_state["report_status_message"] = "当前显示的是本地规则报告。"


def build_llm_client() -> LLMClient:
    config = LLMConfig(
        api_key=st.session_state.get("llm_api_key", "").strip() or os.getenv("LLM_API_KEY", ""),
        base_url=st.session_state.get("llm_base_url", "").strip() or os.getenv("LLM_BASE_URL", ""),
        model=st.session_state.get("llm_model", "").strip() or os.getenv("LLM_MODEL", ""),
        provider=st.session_state.get("llm_provider", "OpenAI-Compatible").strip()
        or os.getenv("LLM_PROVIDER", "OpenAI-Compatible"),
    )
    return LLMClient(enabled=bool(st.session_state.get("llm_enabled", False)), config=config)


def select_data_source(data_choice: str, uploaded_file):
    if data_choice == "上传我整理的新 CSV":
        return uploaded_file, "上传 CSV", uploaded_file is None
    return APP_CONFIG.official_data_path, "国家能源局真实公开数据", False


def format_source_table(data_frame: pd.DataFrame) -> pd.DataFrame:
    formatted = data_frame.copy()
    if APP_CONFIG.date_col in formatted.columns:
        formatted[APP_CONFIG.date_col] = pd.to_datetime(
            formatted[APP_CONFIG.date_col],
            errors="coerce",
        ).dt.strftime("%Y-%m")
    return formatted


st.set_page_config(
    page_title="电力用电量预测与分析 Demo",
    page_icon="⚡",
    layout="wide",
)

init_session_state()
inject_page_style()

st.markdown(
    """
    <div class="hero-card">
        <div class="hero-title">电力行业公开数据预测与大模型分析 Demo</div>
        <div class="hero-subtitle">
            默认使用国家能源局真实公开月度数据，完成用电量趋势预测、报告生成与问答增强。
            页面内置 OpenAI、Google Gemini、DeepSeek、智谱 AI、通义千问的官方接口预设，
            你只需要输入自己的 API Key，就能直接切换云端模型。
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("实验配置")
    data_choice = st.radio(
        "数据源",
        ["国家能源局真实公开数据", "上传我整理的新 CSV"],
        index=0,
    )
    forecast_periods = st.slider(
        "预测月数",
        min_value=APP_CONFIG.min_forecast_periods,
        max_value=APP_CONFIG.max_forecast_periods,
        value=APP_CONFIG.default_forecast_periods,
    )
    uploaded_file = st.file_uploader("上传 CSV 数据", type=["csv"])
    st.caption("当前版本聚焦课程实验演示，默认使用 SARIMA。")

with st.expander("云端大模型配置（官方预设 + 安全输入）", expanded=True):
    preset_col, info_col = st.columns([1.2, 1.6])
    with preset_col:
        st.selectbox(
            "厂商预设",
            options=[preset.key for preset in LLM_PROVIDER_PRESETS],
            key="llm_provider_preset",
            on_change=apply_provider_preset,
        )
        st.checkbox("启用云端大模型增强", key="llm_enabled")
        st.text_input("Provider Label", key="llm_provider")
        st.text_input("API Endpoint", key="llm_base_url")
        st.text_input("Model Name", key="llm_model")
        st.text_input(
            "API Key",
            key="llm_api_key",
            type="password",
            autocomplete="off",
            placeholder="仅保存在当前会话内存中",
        )
        action_col1, action_col2 = st.columns(2)
        with action_col1:
            st.button("测试 API 连接", on_click=test_llm_connection, width="stretch")
        with action_col2:
            st.button("清空 API Key", on_click=clear_api_key, width="stretch")

    with info_col:
        current_preset = LLM_PROVIDER_PRESET_MAP[st.session_state["llm_provider_preset"]]
        st.markdown(f"**当前官方预设：{current_preset.display_name}**")
        st.markdown(f"`{current_preset.endpoint}`")
        st.markdown(f"建议模型：`{current_preset.default_model}`")
        st.markdown(current_preset.note)
        st.markdown(f"[查看官方文档]({current_preset.doc_url})")
        st.caption(
            "API Key 使用密码框输入，不会写入本地文件。更正式的部署建议改用环境变量或 `st.secrets`。"
        )

if st.session_state.get("llm_test_status") == "success":
    st.success(st.session_state.get("llm_test_message", "连接成功。"))
elif st.session_state.get("llm_test_status") == "error":
    st.error(st.session_state.get("llm_test_message", "连接失败。"))

llm_client = build_llm_client()

if st.session_state.get("llm_enabled", False):
    if llm_client.is_ready:
        st.success(
            f"云端模型已启用：{llm_client.config.provider} / {llm_client.config.model} / {llm_client.masked_api_key()}"
        )
    else:
        st.warning("已启用云端增强，但 Endpoint、Model 或 API Key 还不完整，当前会自动回退到本地规则分析。")

st.markdown(
    """
    当前页面只围绕真实公开数据工作：
    默认读取 `国家能源局真实公开数据`，也支持上传你后续整理更新过的同结构 CSV。
    """
)

data_source, source_label, missing_upload = select_data_source(data_choice, uploaded_file)

if missing_upload:
    st.warning("你已选择上传新 CSV，但当前还没有上传文件。请先上传符合标准的 CSV。")
    st.stop()

try:
    raw_df = load_dataset(data_source)
    clean_df = clean_monthly_data(raw_df)
    stats = compute_basic_statistics(clean_df)

    forecaster = SarimaForecaster(
        date_col=APP_CONFIG.date_col,
        target_col=APP_CONFIG.target_col,
    )
    forecast_result = forecaster.fit_predict(clean_df, periods=forecast_periods)
    forecast_df = forecast_result.forecast

    report_text = generate_report(
        history_df=clean_df,
        forecast_df=forecast_df,
        stats=stats,
        llm_client=None,
    )

    qa_engine = RuleBasedQAEngine()

except (DataValidationError, DataProcessingError, ForecastingError) as exc:
    st.error(f"处理失败：{exc}")
    st.stop()

st.info("当前默认使用基于国家能源局官网公告整理的真实公开月度数据，来源说明见 `docs/official_data_sources.md`。")
st.write(f"当前数据源：`{source_label}`")

report_signature = build_report_signature(clean_df, forecast_df, forecast_periods)
if st.session_state.get("report_signature") != report_signature:
    reset_report_state(report_text, report_signature)

summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
summary_col1.metric("历史样本数", int(stats["record_count"]))
summary_col2.metric("最新月份", stats["latest_month"])
summary_col3.metric("最新用电量", f'{stats["latest_value"]:.1f} 亿千瓦时')
summary_col4.metric("历史均值", f'{stats["average_value"]:.1f} 亿千瓦时')

st.subheader("趋势图与预测图")
st.caption("左侧看历史走势与移动均值，右侧看未来预测区间和可能的高峰月份。")
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.plotly_chart(build_history_chart(clean_df), width="stretch")

with chart_col2:
    st.plotly_chart(build_forecast_chart(clean_df, forecast_df), width="stretch")

st.subheader("季节性结构")
st.caption("用柱形和折线共同展示历史月度平均分布，便于快速识别高峰季和低谷季。")
st.plotly_chart(build_seasonality_chart(clean_df), width="stretch")

tab_names = ["清洗后数据", "预测结果"]
if "source_url" in raw_df.columns:
    tab_names.append("来源数据")

tabs = st.tabs(tab_names)

with tabs[0]:
    show_history_df = clean_df.copy()
    show_history_df[APP_CONFIG.date_col] = show_history_df[APP_CONFIG.date_col].dt.strftime("%Y-%m")
    st.dataframe(show_history_df, width="stretch")

with tabs[1]:
    show_forecast_df = forecast_df.copy()
    show_forecast_df[APP_CONFIG.date_col] = show_forecast_df[APP_CONFIG.date_col].dt.strftime("%Y-%m")
    st.dataframe(show_forecast_df, width="stretch")

if len(tabs) > 2:
    with tabs[2]:
        st.dataframe(format_source_table(raw_df), width="stretch")
        st.caption("`note` 中标记为“推导”的月份来自国家能源局累计值计算，未修改原始统计口径。")

report_col, qa_col = st.columns([1.2, 0.8])

with report_col:
    st.subheader("自动分析报告")
    report_action_col1, report_action_col2 = st.columns(2)
    with report_action_col1:
        if st.button("恢复本地规则报告", width="stretch"):
            reset_report_state(report_text, report_signature)
    with report_action_col2:
        if st.button("使用云端大模型润色", width="stretch"):
            if not llm_client.is_ready:
                st.session_state["report_origin"] = "local"
                st.session_state["report_status_message"] = "云端模型未就绪，请先完成 Endpoint、Model 和 API Key 配置。"
            else:
                with st.spinner("正在请求云端大模型润色报告..."):
                    apply_cloud_report(
                        report_draft=report_text,
                        llm_client=llm_client,
                        context={
                            "latest_value": stats["latest_value"],
                            "forecast_average": float(forecast_df["forecast"].mean()),
                            "forecast_periods": len(forecast_df),
                        },
                    )

    if st.session_state.get("report_origin") == "cloud":
        st.success(st.session_state.get("report_status_message", "本次报告已由云端大模型润色。"))
    else:
        status_message = st.session_state.get("report_status_message", "")
        if status_message.startswith("云端润色失败") or "未就绪" in status_message:
            st.warning(status_message)
        else:
            st.caption(status_message)

    st.text_area("报告内容", value=st.session_state.get("report_text", report_text), height=320)
    if st.button("保存报告到 outputs/reports"):
        output_path = save_report(st.session_state.get("report_text", report_text))
        st.success(f"报告已保存：{output_path}")

with qa_col:
    st.subheader("简单问答")
    with st.form("qa_form", clear_on_submit=False):
        user_question = st.text_input(
            "请输入问题",
            placeholder="例如：未来一年用电量趋势如何？",
        )
        ask_button = st.form_submit_button("提交问题", width="stretch")

    if ask_button and user_question:
        with st.spinner("正在生成回答..."):
            answer = qa_engine.answer(
                question=user_question,
                history_df=clean_df,
                forecast_df=forecast_df,
                stats=stats,
                llm_client=llm_client,
            )
        st.session_state["qa_answer"] = answer
        if llm_client.last_answer_used_cloud:
            st.session_state["qa_origin"] = "cloud"
            st.session_state["qa_status_message"] = "本次问答由云端大模型生成。"
        elif llm_client.last_answer_error:
            st.session_state["qa_origin"] = "local"
            st.session_state["qa_status_message"] = f"云端问答失败，已回退到本地规则回答：{llm_client.last_answer_error}"
        elif llm_client.is_ready:
            st.session_state["qa_origin"] = "local"
            st.session_state["qa_status_message"] = "当前使用的是本地规则回答。"
        else:
            st.session_state["qa_origin"] = "local"
            st.session_state["qa_status_message"] = "云端模型未启用或未配置完整，当前使用的是本地规则回答。"

    if st.session_state.get("qa_status_message"):
        if st.session_state.get("qa_origin") == "cloud":
            st.success(st.session_state["qa_status_message"])
        elif "失败" in st.session_state.get("qa_status_message", ""):
            st.warning(st.session_state["qa_status_message"])
        else:
            st.caption(st.session_state["qa_status_message"])

    if st.session_state.get("qa_answer"):
        st.write(st.session_state["qa_answer"])

st.subheader("使用说明")
st.markdown(
    """
    - 页面默认只使用真实公开数据，不再提供演示示例数据。
    - 内置了 OpenAI、Google Gemini、DeepSeek、智谱 AI、通义千问的官方接口预设。
    - API Key 只保存在当前会话内存，不写入本地文件。
    - 如果你后续补充了新的国家能源局月度数据，可以直接上传同结构 CSV 继续使用。
    """
)
