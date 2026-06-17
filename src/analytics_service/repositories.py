from datetime import datetime

from sqlalchemy import Date, desc, func, select
from sqlalchemy.orm import Session

from .models import AnalyticsEvent


def get_event_by_event_id(session: Session, event_id: str) -> AnalyticsEvent | None:
    statement = select(AnalyticsEvent).where(AnalyticsEvent.event_id == event_id)
    return session.scalar(statement)


def create_event(session: Session, event_data: dict) -> AnalyticsEvent:
    event = AnalyticsEvent(**event_data)
    session.add(event)
    session.flush()
    return event


def count_events(session: Session) -> int:
    statement = select(func.count()).select_from(AnalyticsEvent)
    return int(session.scalar(statement) or 0)


def count_by_source(session: Session) -> dict[str, int]:
    statement = (
        select(AnalyticsEvent.source_service, func.count().label("count"))
        .group_by(AnalyticsEvent.source_service)
    )
    return {source: count for source, count in session.execute(statement).all()}


def count_by_event_type(session: Session) -> dict[str, int]:
    statement = (
        select(AnalyticsEvent.event_type, func.count().label("count"))
        .group_by(AnalyticsEvent.event_type)
    )
    return {event_type: count for event_type, count in session.execute(statement).all()}


def get_top_source_service(session: Session) -> str | None:
    statement = (
        select(AnalyticsEvent.source_service, func.count().label("count"))
        .group_by(AnalyticsEvent.source_service)
        .order_by(desc("count"))
        .limit(1)
    )
    row = session.execute(statement).first()
    return row[0] if row else None


def get_top_event_type(session: Session) -> str | None:
    statement = (
        select(AnalyticsEvent.event_type, func.count().label("count"))
        .group_by(AnalyticsEvent.event_type)
        .order_by(desc("count"))
        .limit(1)
    )
    row = session.execute(statement).first()
    return row[0] if row else None


def get_latest_event_time(session: Session) -> datetime | None:
    statement = select(func.max(AnalyticsEvent.occurred_at))
    return session.scalar(statement)


def get_daily_event_counts(session: Session) -> list[dict[str, int]]:
    statement = (
        select(func.date(AnalyticsEvent.occurred_at).label("date"), func.count().label("events"))
        .group_by(func.date(AnalyticsEvent.occurred_at))
        .order_by(func.date(AnalyticsEvent.occurred_at))
    )
    return [
        {"date": str(row.date), "events": int(row.events)}
        for row in session.execute(statement).all()
    ]
