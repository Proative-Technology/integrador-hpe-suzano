import asyncio
import json
import random
from typing import Any, Dict

from app.config import settings
from app.logger import logger
from app.models.OpsRamp_models import TicketModel
from app.models.Retry_model import (
    FailedOperation,
    claim_due,
    mark_failure,
    mark_success,
)


def _dispatch_opsramp_ticket(payload: str) -> None:
    TicketModel(**json.loads(payload)).add()


_DISPATCH = {
    "opsramp_ticket": _dispatch_opsramp_ticket,
}


def run_operation(row: FailedOperation) -> Dict[str, Any]:
    """Execute one claimed failed_operations row. Returns outcome summary."""
    handler = _DISPATCH.get(row.source)
    if handler is None:
        exc = ValueError(f"Unknown retry source: {row.source}")
        mark_failure(row.id, exc)
        return {
            "id": row.id,
            "outcome": "failure",
            "status": "dead" if (row.attempts or 0) + 1 >= (row.max_attempts or 1) else "pending",
            "error": str(exc),
        }
    try:
        handler(row.payload)
        mark_success(row.id)
        return {"id": row.id, "outcome": "success", "status": "succeeded"}
    except Exception as exc:
        mark_failure(row.id, exc)
        # Re-read is not required for response; approximate status from attempts.
        next_attempts = (row.attempts or 0) + 1
        status = "dead" if next_attempts >= (row.max_attempts or settings.retry_max_attempts) else "pending"
        return {
            "id": row.id,
            "outcome": "failure",
            "status": status,
            "error": str(exc),
            "error_type": type(exc).__name__,
        }


def process_due() -> int:
    """Claim and run due retries. Returns number of rows processed."""
    rows = claim_due(settings.retry_batch_size)
    for row in rows:
        try:
            result = run_operation(row)
            logger.info(f"Retry worker processed id={row.id} outcome={result.get('outcome')}")
        except Exception as e:
            logger.error(f"Retry worker unexpected error on id={row.id}: {e}")
            try:
                mark_failure(row.id, e)
            except Exception:
                pass
    return len(rows)


async def retry_loop() -> None:
    """Background loop: poll every retry_poll_seconds and drain due queue rows."""
    jitter = random.uniform(0, min(5.0, float(settings.retry_poll_seconds)))
    logger.info(f"Retry loop starting (jitter={jitter:.1f}s, poll={settings.retry_poll_seconds}s)")
    await asyncio.sleep(jitter)
    while True:
        try:
            loop = asyncio.get_event_loop()
            processed = await loop.run_in_executor(None, process_due)
            if processed:
                logger.debug(f"Retry loop processed {processed} row(s)")
        except asyncio.CancelledError:
            logger.info("Retry loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Retry loop error: {e}")
        await asyncio.sleep(settings.retry_poll_seconds)
