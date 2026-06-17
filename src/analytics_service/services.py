from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .repositories import (
    count_by_event_type,
    count_by_source,
    count_events,
    create_event,
    get_daily_event_counts,
    get_event_by_event_id,
    get_latest_event_time,
    get_top_event_type,
    get_top_source_service,
)
from .schemas import AnalyticsEventRequest


def ingest_event(session: Session, payload: AnalyticsEventRequest) -> None:
    if get_event_by_event_id(session, payload.eventId):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "https://smart-campus.local/problems/duplicate-event",
                "title": "Duplicate event",
                "status": status.HTTP_409_CONFLICT,
                "detail": "eventId has already been processed",
            },
        )

    create_event(session, payload.to_repository_dict())


def get_summary(session: Session) -> dict:
    return {
        "totalEvents": count_events(session),
        "sources": count_by_source(session),
    }


def get_event_type_counts(session: Session) -> dict[str, int]:
    return count_by_event_type(session)


def get_dashboard(session: Session) -> dict:
    return {
        "totalEvents": count_events(session),
        "topSourceService": get_top_source_service(session),
        "latestEventTime": get_latest_event_time(session),
        "topEventType": get_top_event_type(session),
    }


def get_daily_reports(session: Session) -> list[dict[str, int]]:
    return get_daily_event_counts(session)
