from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.logger import logger
from app.models.Retry_model import (
    FailedOperation,
    cancel_operation,
    claim_by_id,
    get_by_id,
    list_operations,
)
from app.retry_worker import run_operation

router = APIRouter()

ERROR_MESSAGE_LIMIT = 500


def _serialize_row(row: FailedOperation, verbose: bool = False) -> Dict[str, Any]:
    message = row.error_message
    if message and not verbose and len(message) > ERROR_MESSAGE_LIMIT:
        message = message[:ERROR_MESSAGE_LIMIT] + "…"
    return {
        "id": row.id,
        "source": row.source,
        "operation": row.operation,
        "opsramp_id": row.opsramp_id,
        "status": row.status,
        "attempts": row.attempts,
        "max_attempts": row.max_attempts,
        "next_attempt_at": row.next_attempt_at.isoformat() if row.next_attempt_at else None,
        "last_attempt_at": row.last_attempt_at.isoformat() if row.last_attempt_at else None,
        "error_type": row.error_type,
        "error_message": message,
        "http_status": row.http_status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("")
async def list_retries(
    status: Optional[str] = None,
    opsramp_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    verbose: bool = False,
):
    """List failed_operations queue rows (newest first)."""
    try:
        rows, total = list_operations(
            status=status,
            opsramp_id=opsramp_id,
            limit=limit,
            offset=offset,
        )
        return JSONResponse(
            content={
                "count": total,
                "limit": limit,
                "offset": offset,
                "operations": [_serialize_row(r, verbose=verbose) for r in rows],
            }
        )
    except Exception as e:
        logger.error(f"Error listing retries: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to list retry operations"},
        )


@router.get("/{row_id}")
async def get_retry(row_id: int, verbose: bool = True):
    """Fetch one failed_operations row (full error by default)."""
    try:
        row = get_by_id(row_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Retry operation not found")
        return JSONResponse(content=_serialize_row(row, verbose=verbose))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching retry {row_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to fetch retry operation"},
        )


@router.post("/{row_id}")
async def force_retry(row_id: int):
    """
    Force-retry a pending or dead operation immediately (ignores next_attempt_at).
    Returns 404 if unknown, 409 if already processing or invalid status.
    """
    import asyncio

    try:
        row = claim_by_id(row_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Retry operation not found")
    except ValueError as e:
        msg = str(e)
        if msg == "already_processing":
            raise HTTPException(status_code=409, detail="Operation already processing") from e
        if msg.startswith("invalid_status:"):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot retry operation with status {msg.split(':', 1)[1]}",
            ) from e
        raise HTTPException(status_code=409, detail=msg) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error claiming retry {row_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to claim retry operation"},
        )

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_operation, row)
        refreshed = get_by_id(row_id)
        return JSONResponse(
            content={
                "result": result,
                "operation": _serialize_row(refreshed, verbose=True) if refreshed else None,
            }
        )
    except Exception as e:
        logger.error(f"Error running manual retry {row_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to run retry operation"},
        )


@router.post("/{row_id}/cancel")
async def cancel_retry(row_id: int):
    """Cancel a pending/dead operation so it stops consuming attempts."""
    try:
        row = cancel_operation(row_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Retry operation not found")
        return JSONResponse(content=_serialize_row(row, verbose=True))
    except ValueError as e:
        msg = str(e)
        if msg == "already_processing":
            raise HTTPException(status_code=409, detail="Operation already processing") from e
        if msg.startswith("invalid_status:"):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot cancel operation with status {msg.split(':', 1)[1]}",
            ) from e
        raise HTTPException(status_code=409, detail=msg) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling retry {row_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to cancel retry operation"},
        )
