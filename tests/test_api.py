from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def build_csv_content(length: int = 24) -> str:
    rows = ["date,consumption_billion_kwh,source,note"]
    for index in range(length):
        year = 2023 + (index // 12)
        month = (index % 12) + 1
        rows.append(f"{year:04d}-{month:02d},{7000 + index * 15},测试来源,样本")
    return "\n".join(rows)


def test_get_default_dataset() -> None:
    response = client.get("/api/national/datasets/default")
    payload = response.json()

    assert response.status_code == 200
    assert payload["code"] == 0
    assert payload["data"]["source"] == "default"
    assert payload["data"]["summary"]["clean_record_count"] >= 18


def test_validate_dataset_rejects_invalid_csv() -> None:
    response = client.post("/api/national/datasets/validate", json={"csv_content": "date\n2024-01"})

    assert response.status_code == 400
    assert response.json()["code"] == 1


def test_run_forecast_returns_full_payload_for_uploaded_csv() -> None:
    response = client.post(
        "/api/national/forecast/run",
        json={
            "dataset_source": "uploaded",
            "forecast_periods": 6,
            "csv_content": build_csv_content(),
            "llm_config": {
                "enabled": False,
                "provider": "OpenAI-Compatible",
                "base_url": "",
                "model": "",
                "api_key": ""
            }
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["data"]["forecast"]
    assert payload["data"]["history"]
    assert payload["data"]["stats"]["record_count"] >= 18
    assert payload["data"]["report"]["status"] == "local"


def test_polish_report_falls_back_when_llm_is_not_ready() -> None:
    response = client.post(
        "/api/national/report/polish",
        json={
            "draft_report": "示例报告",
            "context": {"latest_value": 100},
            "llm_config": {
                "enabled": True,
                "provider": "OpenAI-Compatible",
                "base_url": "",
                "model": "",
                "api_key": ""
            }
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["data"]["report_text"] == "示例报告"
    assert payload["data"]["status"] == "fallback_local"


def test_qa_uses_rule_answer_when_llm_is_disabled() -> None:
    forecast_run = client.post(
        "/api/national/forecast/run",
        json={
            "dataset_source": "uploaded",
            "forecast_periods": 6,
            "csv_content": build_csv_content(),
            "llm_config": {
                "enabled": False,
                "provider": "OpenAI-Compatible",
                "base_url": "",
                "model": "",
                "api_key": ""
            }
        },
    ).json()["data"]

    response = client.post(
        "/api/national/qa",
        json={
            "question": "未来一年用电量趋势如何",
            "history": forecast_run["history"],
            "forecast": forecast_run["forecast"],
            "stats": forecast_run["stats"],
            "llm_config": {
                "enabled": False,
                "provider": "OpenAI-Compatible",
                "base_url": "",
                "model": "",
                "api_key": ""
            }
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["data"]["status"] == "local"
    assert "未来" in payload["data"]["answer"]
