import os
from http import HTTPStatus

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import SessionLocal, init_db
from .schemas import (
    AnalyticsEventAcceptedResponse,
    AnalyticsEventRequest,
    DashboardResponse,
    DailyReportRow,
    SummaryResponse,
)
from .services import (
    get_dashboard,
    get_daily_reports,
    get_event_type_counts,
    get_summary,
    ingest_event,
)


SERVICE_NAME = os.getenv("SERVICE_NAME", "analytics-service")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.5.0")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "local-dev-token")

app = FastAPI(
    title="FIT4110 Lab 05 - Analytics Service",
    version=SERVICE_VERSION,
    description=(
        "Analytics Service for Smart Campus. "
        "This service stores and aggregates event data from other microservices."
    ),
)


class ProblemDetails(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str | None = None


def build_problem(*, status_code: int, title: str, detail: str, instance: str | None = None, problem_type: str = "about:blank") -> dict:
    problem = {
        "type": problem_type,
        "title": title,
        "status": status_code,
        "detail": detail,
    }
    if instance:
        problem["instance"] = instance
    return problem


@app.on_event("startup")
def startup_event() -> None:
    init_db()


def get_db() -> Session:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        problem = exc.detail
    else:
        problem = build_problem(
            status_code=exc.status_code,
            title=HTTPStatus(exc.status_code).phrase,
            detail=str(exc.detail),
            instance=str(request.url.path),
        )

    problem.setdefault("status", exc.status_code)
    problem.setdefault("title", status.HTTP_500_INTERNAL_SERVER_ERROR)
    problem.setdefault("type", "about:blank")
    problem.setdefault("detail", "Request failed")
    problem.setdefault("instance", str(request.url.path))

    return JSONResponse(
        status_code=exc.status_code,
        content=problem,
        media_type="application/problem+json",
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else {}
    location = ".".join(str(item) for item in first_error.get("loc", []))
    message = first_error.get("msg", "Request validation error")
    detail = f"{location}: {message}" if location else message

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=build_problem(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Validation error",
            detail=detail,
            instance=str(request.url.path),
            problem_type="https://smart-campus.local/problems/validation-error",
        ),
        media_type="application/problem+json",
    )


def verify_bearer_token(authorization: str | None = Header(default=None)) -> None:
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=build_problem(
                status_code=status.HTTP_401_UNAUTHORIZED,
                title="Unauthorized",
                detail="Missing Authorization header",
                instance="/analytics/events",
                problem_type="https://smart-campus.local/problems/unauthorized",
            ),
        )
    expected = f"Bearer {AUTH_TOKEN}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=build_problem(
                status_code=status.HTTP_401_UNAUTHORIZED,
                title="Unauthorized",
                detail="Invalid bearer token",
                instance="/analytics/events",
                problem_type="https://smart-campus.local/problems/unauthorized",
            ),
        )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}


@app.post(
    "/analytics/events",
    response_model=AnalyticsEventAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {"model": AnalyticsEventAcceptedResponse},
        400: {"model": ProblemDetails},
        409: {"model": ProblemDetails},
        422: {"model": ProblemDetails},
        401: {"model": ProblemDetails},
    },
)
def receive_analytics_event(
    payload: AnalyticsEventRequest,
    authorization: str | None = Depends(verify_bearer_token),
    db: Session = Depends(get_db),
) -> AnalyticsEventAcceptedResponse:
    try:
        ingest_event(db, payload)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_problem(
                status_code=status.HTTP_409_CONFLICT,
                title="Duplicate event",
                detail="eventId has already been processed",
                instance="/analytics/events",
                problem_type="https://smart-campus.local/problems/duplicate-event",
            ),
        )

    return AnalyticsEventAcceptedResponse(
        eventId=payload.eventId,
        status="accepted",
        message="Event accepted for processing",
    )


@app.get("/analytics/summary", response_model=SummaryResponse)
def get_summary_endpoint(db: Session = Depends(get_db)) -> SummaryResponse:
    summary = get_summary(db)
    return SummaryResponse(**summary)


@app.get("/analytics/event-types")
def get_event_types_endpoint(db: Session = Depends(get_db)) -> dict[str, int]:
    return get_event_type_counts(db)


@app.get("/analytics/dashboard", response_model=DashboardResponse)
def get_dashboard_endpoint(db: Session = Depends(get_db)) -> DashboardResponse:
    dashboard = get_dashboard(db)
    return DashboardResponse(**dashboard)


@app.get("/analytics/reports/daily")
def get_daily_reports_endpoint(db: Session = Depends(get_db)) -> list[DailyReportRow]:
    return [DailyReportRow(**row) for row in get_daily_reports(db)]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("APP_PORT", "8000")))