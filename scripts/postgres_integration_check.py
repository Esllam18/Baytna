from __future__ import annotations

import concurrent.futures
import os
import sys
from uuid import uuid4

from sqlalchemy import select, text

from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import Settings
from app.core.database import SessionLocal
from app.core.db_models import OutboxEventEntity, RateLimitBucketEntity
from app.modules.reliability.outbox import OutboxService
from app.modules.security_hardening.service import SecurityService


def main() -> int:
    settings = Settings()
    with SessionLocal() as db:
        dialect = db.bind.dialect.name
        if dialect != "postgresql":
            print(
                "POSTGRES INTEGRATION CHECK REQUIRES REAL POSTGRESQL; "
                f"current dialect={dialect}"
            )
            return 2
        db.execute(text("SELECT 1"))

    raw_key = f"postgres-concurrency-{uuid4()}"

    def consume_once() -> int:
        with SessionLocal() as db:
            decision = SecurityService(db, settings).consume(
                scope="integration.concurrent",
                raw_key=raw_key,
                limit=1000,
                window_seconds=60,
            )
            db.commit()
            return decision.count

    workers = 12
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        list(executor.map(lambda _: consume_once(), range(workers)))

    with SessionLocal() as db:
        key_hash = SecurityService(db, settings).hash_key(raw_key)
        row = db.scalar(
            select(RateLimitBucketEntity).where(
                RateLimitBucketEntity.scope == "integration.concurrent",
                RateLimitBucketEntity.key_hash == key_hash,
            )
        )
        if row is None or row.request_count != workers:
            raise RuntimeError(
                f"Rate limiter concurrency check failed: expected={workers}, "
                f"actual={getattr(row, 'request_count', None)}"
            )

        outbox = OutboxService(db, settings)
        event = outbox.enqueue(
            event_type="integration.postgres",
            aggregate_type="integration",
            aggregate_id=str(uuid4()),
            payload={"check": True},
            dedupe_key=f"integration-postgres-{uuid4()}",
        )
        db.commit()

        claimed = outbox.claim_one(worker_id="postgres-integration-check")
        if claimed is None or claimed.id != event.id:
            raise RuntimeError("PostgreSQL outbox claim check failed")
        if claimed.status != "processing":
            raise RuntimeError("Outbox event was not claimed into processing")

    print("Real PostgreSQL integration check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
