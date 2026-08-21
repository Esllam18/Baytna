from __future__ import annotations

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class OutboxEventResponse(BaseModel):
    id: UUID
    event_type: str
    aggregate_type: str
    aggregate_id: str
    dedupe_key: str
    status: str
    attempts: int
    max_attempts: int
    available_at: datetime
    locked_at: datetime | None
    locked_by: str | None
    published_at: datetime | None
    last_error: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


class BackgroundJobResponse(BaseModel):
    id: UUID
    job_type: str
    idempotency_key: str
    status: str
    attempts: int
    max_attempts: int
    available_at: datetime
    locked_at: datetime | None
    locked_by: str | None
    finished_at: datetime | None
    last_error: str | None
    result_json: dict
    created_at: datetime
    model_config = {"from_attributes": True}


class WorkerHeartbeatResponse(BaseModel):
    worker_id: str
    status: str
    started_at: datetime
    last_seen_at: datetime
    processed_jobs: int
    published_events: int
    last_error: str | None
    model_config = {"from_attributes": True}
