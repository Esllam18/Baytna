from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db_models import WorkerHeartbeatEntity
from app.core.security import utc_now
from app.modules.reliability.jobs import BackgroundJobService
from app.modules.reliability.outbox import OutboxService, build_publisher


class WorkerService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def heartbeat(self, worker_id: str) -> WorkerHeartbeatEntity:
        row = self.db.get(WorkerHeartbeatEntity, worker_id)
        if row is None:
            row = WorkerHeartbeatEntity(
                worker_id=worker_id,
                status="running",
            )
            self.db.add(row)
            self.db.flush()
        row.last_seen_at = utc_now()
        return row

    def run_once(self, *, worker_id: str = "baytna-worker") -> dict:
        heartbeat = self.heartbeat(worker_id)
        heartbeat.status = "running"
        heartbeat.last_error = None
        self.db.commit()

        jobs = BackgroundJobService(self.db, self.settings)
        outbox = OutboxService(self.db, self.settings)

        recovered_jobs = jobs.recover_stale()
        recovered_outbox = outbox.recover_stale(
            stale_seconds=self.settings.worker_stale_seconds
        )
        jobs.schedule_maintenance()

        try:
            job_result = jobs.run_due(
                worker_id=worker_id,
                limit=self.settings.worker_batch_size,
            )
            outbox_result = outbox.publish_due(
                worker_id=worker_id,
                publisher=build_publisher(self.settings),
                limit=self.settings.worker_batch_size,
            )

            heartbeat = self.heartbeat(worker_id)
            heartbeat.status = "idle"
            heartbeat.processed_jobs += job_result["succeeded"]
            heartbeat.published_events += outbox_result["published"]
            heartbeat.last_seen_at = utc_now()
            self.db.commit()

            return {
                "worker_id": worker_id,
                "recovered_jobs": recovered_jobs,
                "recovered_outbox": recovered_outbox,
                "jobs": job_result,
                "outbox": outbox_result,
            }
        except Exception as exc:
            self.db.rollback()
            heartbeat = self.heartbeat(worker_id)
            heartbeat.status = "error"
            heartbeat.last_error = str(exc)[:4000]
            heartbeat.last_seen_at = utc_now()
            self.db.commit()
            raise
