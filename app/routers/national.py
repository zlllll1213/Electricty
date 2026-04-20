from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas import (
    APIResponse,
    LLMConfigUpsertRequest,
    LLMTestRequest,
    NationalDatasetValidateRequest,
    NationalForecastRunRequest,
    NationalPolishReportRequest,
    NationalQARequest,
)
from app.services.national import NationalService


router = APIRouter(prefix="/api/national", tags=["national"])


def get_service(request: Request) -> NationalService:
    return NationalService(runtime=request.app.state.runtime)


@router.get("/datasets/default", response_model=APIResponse)
def get_default_dataset(request: Request) -> APIResponse:
    service = get_service(request)
    return APIResponse(data=service.get_default_dataset_payload())


@router.post("/datasets/validate", response_model=APIResponse)
def validate_dataset(payload: NationalDatasetValidateRequest, request: Request) -> APIResponse:
    service = get_service(request)
    return APIResponse(data=service.validate_dataset(payload))


@router.post("/forecast/run", response_model=APIResponse)
def run_forecast(payload: NationalForecastRunRequest, request: Request) -> APIResponse:
    service = get_service(request)
    return APIResponse(data=service.run_forecast(payload))


@router.post("/report/polish", response_model=APIResponse)
def polish_report(payload: NationalPolishReportRequest, request: Request) -> APIResponse:
    service = get_service(request)
    return APIResponse(data=service.polish_report(payload))


@router.post("/qa", response_model=APIResponse)
def answer_question(payload: NationalQARequest, request: Request) -> APIResponse:
    service = get_service(request)
    return APIResponse(data=service.answer_question(payload))


@router.post("/llm/test", response_model=APIResponse)
def test_llm(payload: LLMTestRequest, request: Request) -> APIResponse:
    service = get_service(request)
    return APIResponse(data=service.test_llm(payload))


@router.post("/llm/config", response_model=APIResponse)
def upsert_llm_config(payload: LLMConfigUpsertRequest, request: Request) -> APIResponse:
    service = get_service(request)
    return APIResponse(data=service.upsert_llm_config(payload))


@router.get("/llm/config", response_model=APIResponse)
def get_llm_config(request: Request) -> APIResponse:
    service = get_service(request)
    return APIResponse(data=service.get_llm_config())


@router.delete("/llm/config", response_model=APIResponse)
def delete_llm_config(request: Request) -> APIResponse:
    service = get_service(request)
    return APIResponse(data=service.delete_llm_config())


@router.get("/meta", response_model=APIResponse)
def get_meta(request: Request) -> APIResponse:
    service = get_service(request)
    return APIResponse(data=service.get_meta())
