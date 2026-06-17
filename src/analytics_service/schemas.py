from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field


class AnalyticsEventRequest(BaseModel):
    eventId: str = Field(..., min_length=1, alias="eventId")
    eventType: str = Field(..., min_length=1, alias="eventType")
    sourceService: str = Field(..., min_length=1, alias="sourceService")
    occurredAt: datetime = Field(..., alias="occurredAt")
    payload: Dict[str, Any] = Field(default_factory=dict, alias="payload")

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    def to_repository_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.eventId,
            "event_type": self.eventType,
            "source_service": self.sourceService,
            "occurred_at": self.occurredAt,
            "payload": self.payload,
        }


class AnalyticsEventAcceptedResponse(BaseModel):
    eventId: str
    status: str
    message: str


class SummaryResponse(BaseModel):
    totalEvents: int
    sources: Dict[str, int]


class DashboardResponse(BaseModel):
    totalEvents: int
    topSourceService: str | None = None
    latestEventTime: datetime | None = None
    topEventType: str | None = None


class DailyReportRow(BaseModel):
    date: str
    events: int
