from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from pathlib import Path
from uuid import uuid4

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.modules.reliability.worker import WorkerService


def run_once(worker_id: str) -> dict:
    with SessionLocal() as db:
        return WorkerService(db, get_settings()).run_once(worker_id=worker_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Baytna background worker")
    parser.add_argument("--once", action="store_true", help="Run one worker tick and exit")
    parser.add_argument("--worker-id", default=f"baytna-worker-{uuid4().hex[:8]}")
    args = parser.parse_args()
    settings = get_settings()

    if args.once:
        print(json.dumps(run_once(args.worker_id), ensure_ascii=False, default=str))
        return

    stopped = False
    def stop(*_):
        nonlocal stopped
        stopped = True
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    while not stopped:
        try:
            result = run_once(args.worker_id)
            print(json.dumps(result, ensure_ascii=False, default=str), flush=True)
        except Exception as exc:
            print(json.dumps({"worker_id": args.worker_id, "error": str(exc)}, ensure_ascii=False), flush=True)
        if not stopped:
            time.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    main()
