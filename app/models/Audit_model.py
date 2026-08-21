from contextlib import contextmanager
from datetime import datetime
from time import perf_counter
from typing import Any, Dict, Generator, Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.logger import logger
from app.models.base import Base

DB_CONNECTION = settings.conn_str


class OperationEvent(Base):
    __tablename__ = "operation_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    occurred_at = Column(DateTime, nullable=False, index=True, default=datetime.now)
    operation = Column(String(32), nullable=False)  # create / update / close / skip
    step = Column(String(64), nullable=False)
    outcome = Column(String(16), nullable=False)  # success / failure

    opsramp_id = Column(String(255), nullable=True, index=True)
    topdesk_id = Column(String(255), nullable=True)
    topdesk_number = Column(String(64), nullable=True)
    access_url = Column(String(1024), nullable=True)

    subject = Column(String(512), nullable=True)
    client_name = Column(String(255), nullable=True)

    http_status = Column(Integer, nullable=True)
    error_type = Column(String(128), nullable=True)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)


def record_event(**kwargs: Any) -> None:
    """Persist one audit row. Never raises — monitoring must not break integration."""
    engine = None
    try:
        payload = dict(kwargs)
        payload.setdefault("occurred_at", datetime.now())
        engine = create_engine(DB_CONNECTION)
        Session = sessionmaker(bind=engine)
        with Session() as session:
            session.add(OperationEvent(**payload))
            session.commit()
    except Exception as e:
        logger.error(f"Failed to record operation event: {e}")
    finally:
        if engine is not None:
            engine.dispose()


def _extract_http_status(exc: BaseException) -> Optional[int]:
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        return status
    return None


@contextmanager
def track(
    operation: str,
    step: str,
    ctx: Optional[Dict[str, Any]] = None,
) -> Generator[Dict[str, Any], None, None]:
    """
    Record success on clean exit, failure (+ error detail) on exception, then re-raise.
    Yields a mutable context dict so callers can enrich lookup keys mid-step.
    """
    context: Dict[str, Any] = dict(ctx or {})
    started = perf_counter()
    try:
        yield context
    except Exception as exc:
        duration_ms = int((perf_counter() - started) * 1000)
        record_event(
            operation=operation,
            step=step,
            outcome="failure",
            opsramp_id=context.get("opsramp_id"),
            topdesk_id=context.get("topdesk_id"),
            topdesk_number=context.get("topdesk_number"),
            access_url=context.get("access_url"),
            subject=context.get("subject"),
            client_name=context.get("client_name"),
            http_status=_extract_http_status(exc),
            error_type=type(exc).__name__,
            error_message=str(exc),
            duration_ms=duration_ms,
        )
        try:
            setattr(exc, "_operation_event_recorded", True)
        except Exception:
            pass
        raise
    else:
        duration_ms = int((perf_counter() - started) * 1000)
        record_event(
            operation=operation,
            step=step,
            outcome="success",
            opsramp_id=context.get("opsramp_id"),
            topdesk_id=context.get("topdesk_id"),
            topdesk_number=context.get("topdesk_number"),
            access_url=context.get("access_url"),
            subject=context.get("subject"),
            client_name=context.get("client_name"),
            http_status=context.get("http_status"),
            duration_ms=duration_ms,
        )
