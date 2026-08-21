from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.logger import logger
from app.models.Audit_model import OperationEvent

router = APIRouter()

DB_CONNECTION = settings.conn_str
ERROR_MESSAGE_LIMIT = 500

# Successful step -> ticket counter key used in /summary
_SUCCESS_STEP_TO_TICKET_KEY = {
    "topdesk_create": "created",
    "topdesk_update": "updated",
    "topdesk_close": "closed",
    "no_change": "no_change",
}


def _day_window(day: date) -> Tuple[datetime, datetime]:
    """Naive local [day 00:00, day+1 00:00) matching datetime.now() used elsewhere."""
    start = datetime.combine(day, datetime.min.time())
    end = start + timedelta(days=1)
    return start, end


def _parse_day(day: Optional[str]) -> date:
    if day is None:
        return date.today()
    try:
        return date.fromisoformat(day)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date; expected YYYY-MM-DD") from exc


def _topdesk_url(topdesk_id: Optional[str]) -> Optional[str]:
    if not topdesk_id:
        return None
    base = settings.topdesk_base_url.rstrip("/")
    return f"{base}/tas/secure/incident?unid={topdesk_id}"


def _serialize_event(event: OperationEvent, verbose: bool = False) -> Dict[str, Any]:
    message = event.error_message
    if message and not verbose and len(message) > ERROR_MESSAGE_LIMIT:
        message = message[:ERROR_MESSAGE_LIMIT] + "…"
    return {
        "id": event.id,
        "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
        "operation": event.operation,
        "step": event.step,
        "outcome": event.outcome,
        "opsramp_id": event.opsramp_id,
        "opsramp_url": event.access_url,
        "topdesk_id": event.topdesk_id,
        "topdesk_number": event.topdesk_number,
        "topdesk_url": _topdesk_url(event.topdesk_id),
        "subject": event.subject,
        "client_name": event.client_name,
        "http_status": event.http_status,
        "error_type": event.error_type,
        "error_message": message,
        "duration_ms": event.duration_ms,
    }


@router.get("/summary")
async def monitoring_summary(date_str: Optional[str] = Query(None, alias="date")):
    """Daily integrator execution summary from operation_events."""
    day = _parse_day(date_str)
    window_start, window_end = _day_window(day)
    engine = None
    try:
        engine = create_engine(DB_CONNECTION)
        Session = sessionmaker(bind=engine)
        with Session() as session:
            base = session.query(OperationEvent).filter(
                OperationEvent.occurred_at >= window_start,
                OperationEvent.occurred_at < window_end,
            )

            total_events = base.count()
            success_count = base.filter(OperationEvent.outcome == "success").count()
            failure_count = base.filter(OperationEvent.outcome == "failure").count()
            success_rate = round(success_count / total_events, 4) if total_events else 0.0

            distinct_affected = (
                session.query(func.count(func.distinct(OperationEvent.opsramp_id)))
                .filter(
                    OperationEvent.occurred_at >= window_start,
                    OperationEvent.occurred_at < window_end,
                    OperationEvent.opsramp_id.isnot(None),
                )
                .scalar()
                or 0
            )

            ticket_counts = {"created": 0, "updated": 0, "closed": 0, "no_change": 0}
            success_by_step = (
                session.query(
                    OperationEvent.step,
                    func.count(func.distinct(OperationEvent.opsramp_id)),
                )
                .filter(
                    OperationEvent.occurred_at >= window_start,
                    OperationEvent.occurred_at < window_end,
                    OperationEvent.outcome == "success",
                    OperationEvent.step.in_(list(_SUCCESS_STEP_TO_TICKET_KEY.keys())),
                )
                .group_by(OperationEvent.step)
                .all()
            )
            for step, count in success_by_step:
                key = _SUCCESS_STEP_TO_TICKET_KEY.get(step)
                if key:
                    ticket_counts[key] = int(count)

            failure_distinct = (
                session.query(func.count(func.distinct(OperationEvent.opsramp_id)))
                .filter(
                    OperationEvent.occurred_at >= window_start,
                    OperationEvent.occurred_at < window_end,
                    OperationEvent.outcome == "failure",
                    OperationEvent.opsramp_id.isnot(None),
                )
                .scalar()
                or 0
            )

            failure_by_step_rows = (
                session.query(OperationEvent.step, func.count(OperationEvent.id))
                .filter(
                    OperationEvent.occurred_at >= window_start,
                    OperationEvent.occurred_at < window_end,
                    OperationEvent.outcome == "failure",
                )
                .group_by(OperationEvent.step)
                .all()
            )
            failures_by_step = {step: int(count) for step, count in failure_by_step_rows}

            by_step_rows = (
                session.query(
                    OperationEvent.step,
                    OperationEvent.outcome,
                    func.count(OperationEvent.id),
                )
                .filter(
                    OperationEvent.occurred_at >= window_start,
                    OperationEvent.occurred_at < window_end,
                )
                .group_by(OperationEvent.step, OperationEvent.outcome)
                .all()
            )
            by_step_map: Dict[str, Dict[str, int]] = {}
            for step, outcome, count in by_step_rows:
                entry = by_step_map.setdefault(step, {"step": step, "success": 0, "failure": 0})
                if outcome in ("success", "failure"):
                    entry[outcome] = int(count)
            by_step: List[Dict[str, Any]] = sorted(by_step_map.values(), key=lambda x: x["step"])

            first_at = (
                session.query(func.min(OperationEvent.occurred_at))
                .filter(
                    OperationEvent.occurred_at >= window_start,
                    OperationEvent.occurred_at < window_end,
                )
                .scalar()
            )
            last_at = (
                session.query(func.max(OperationEvent.occurred_at))
                .filter(
                    OperationEvent.occurred_at >= window_start,
                    OperationEvent.occurred_at < window_end,
                )
                .scalar()
            )

        return JSONResponse(
            content={
                "date": day.isoformat(),
                "window": {
                    "from": window_start.isoformat(),
                    "to": window_end.isoformat(),
                },
                "totals": {
                    "events": total_events,
                    "success": success_count,
                    "failure": failure_count,
                    "success_rate": success_rate,
                },
                "tickets": {
                    **ticket_counts,
                    "distinct_affected": distinct_affected,
                },
                "failures": {
                    "total": failure_count,
                    "distinct_tickets": failure_distinct,
                    "by_step": failures_by_step,
                },
                "by_step": by_step,
                "first_event_at": first_at.isoformat() if first_at else None,
                "last_event_at": last_at.isoformat() if last_at else None,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error building monitoring summary: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to build monitoring summary"},
        )
    finally:
        if engine is not None:
            engine.dispose()


@router.get("/failures")
async def monitoring_failures(
    date_str: Optional[str] = Query(None, alias="date"),
    step: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    verbose: bool = False,
):
    """Concise list of failed operations for a day, with OpsRamp/TopDesk lookup keys."""
    day = _parse_day(date_str)
    window_start, window_end = _day_window(day)
    engine = None
    try:
        engine = create_engine(DB_CONNECTION)
        Session = sessionmaker(bind=engine)
        with Session() as session:
            query = session.query(OperationEvent).filter(
                OperationEvent.occurred_at >= window_start,
                OperationEvent.occurred_at < window_end,
                OperationEvent.outcome == "failure",
            )
            if step:
                query = query.filter(OperationEvent.step == step)
            total = query.count()
            events = (
                query.order_by(OperationEvent.occurred_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

        return JSONResponse(
            content={
                "date": day.isoformat(),
                "count": total,
                "limit": limit,
                "offset": offset,
                "failures": [_serialize_event(e, verbose=verbose) for e in events],
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing monitoring failures: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to list monitoring failures"},
        )
    finally:
        if engine is not None:
            engine.dispose()


@router.get("/ticket/{opsramp_id}")
async def monitoring_ticket(opsramp_id: str, verbose: bool = False):
    """Full event timeline for one OpsRamp ticket."""
    engine = None
    try:
        engine = create_engine(DB_CONNECTION)
        Session = sessionmaker(bind=engine)
        with Session() as session:
            events = (
                session.query(OperationEvent)
                .filter(OperationEvent.opsramp_id == opsramp_id)
                .order_by(OperationEvent.occurred_at.asc(), OperationEvent.id.asc())
                .all()
            )

        return JSONResponse(
            content={
                "opsramp_id": opsramp_id,
                "count": len(events),
                "events": [_serialize_event(e, verbose=verbose) for e in events],
            }
        )
    except Exception as e:
        logger.error(f"Error listing ticket events for {opsramp_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to list ticket events"},
        )
    finally:
        if engine is not None:
            engine.dispose()
