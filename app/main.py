from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.routers.national import router as national_router
from app.services.national import NationalServiceError
from app.state import app_state
from src.data_loader import DataValidationError
from src.forecast.sarima_model import ForecastingError
from src.preprocess import DataProcessingError


BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
FRONTEND_DIST_DIR = FRONTEND_DIR / "dist"
FRONTEND_ASSETS_DIR = FRONTEND_DIST_DIR / "assets"


app = FastAPI(
    title="National Power Forecast Platform API",
    description="National electricity forecasting and analysis API aligned with PowerModel.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(national_router)

if FRONTEND_ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_ASSETS_DIR), name="assets")


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"message": "National Power Forecast Platform API is running"})


@app.exception_handler(NationalServiceError)
@app.exception_handler(DataValidationError)
@app.exception_handler(DataProcessingError)
@app.exception_handler(ForecastingError)
def handle_known_errors(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=400, content={"code": 1, "message": str(exc), "detail": str(exc), "data": {}})


@app.exception_handler(RequestValidationError)
def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"code": 1, "message": "request validation failed", "detail": exc.errors(), "data": {}})


@app.get("/")
def root():
    index_file = FRONTEND_DIST_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)

    return HTMLResponse(
        content=(
            "<h1>Frontend build not found</h1>"
            "<p>Run <code>npm install</code> and <code>npm run build</code> in "
            "<code>frontend</code>.</p>"
        ),
        status_code=503,
    )


@app.get("/app.py")
def legacy_app_reference() -> HTMLResponse:
    return HTMLResponse(
        content=(
            "<p><code>app.py</code> is kept as a legacy Streamlit reference only. "
            "Use <code>uvicorn app.main:app --reload</code> to run the refactored application.</p>"
        )
    )


app.state.runtime = app_state
