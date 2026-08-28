from datetime import datetime, timedelta
from typing import List, Optional

import requests
from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.logger import logger
from app.models.Audit_model import record_event
from app.models.base import Base

DB_CONNECTION = settings.conn_str

RETRYABLE_HTTP_STATUS = {408, 429, 500, 502, 503, 504}

# pymysql errnos that indicate transient connectivity / lock contention.
TRANSIENT_MYSQL_ERRNOS = {2003, 2006, 2013, 1040, 1205, 1213}

# Stale processing rows older than this are reclaimable (worker crash mid-retry).
STALE_PROCESSING_MINUTES = 30


class FailedOperation(Base):
    __tablename__ = "failed_operations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(32), nullable=False)  # dispatch key, e.g. opsramp_ticket
    operation = Column(String(32), nullable=False)  # create / update / close
    opsramp_id = Column(String(255), nullable=True, index=True)
    payload = Column(Text, nullable=False)

    status = Column(String(32), nullable=False, index=True, default="pending")
    # pending / processing / succeeded / dead / cancelled

    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=5)
    next_attempt_at = Column(DateTime, nullable=False, index=True)
    last_attempt_at = Column(DateTime, nullable=True)

    error_type = Column(String(128), nullable=True)
    error_message = Column(Text, nullable=True)
    http_status = Column(Integer, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now)


def backoff(attempt: int) -> timedelta:
    """Exponential backoff: base * 2^(attempt-1), capped at max_delay."""
    base = settings.retry_base_delay_minutes
    cap = settings.retry_max_delay_minutes
    minutes = min(base * (2 ** max(attempt - 1, 0)), cap)
    return timedelta(minutes=minutes)


def _mysql_errno(exc: BaseException) -> Optional[int]:
    orig = getattr(exc, "orig", None)
    if orig is not None:
        args = getattr(orig, "args", ())
        if args and isinstance(args[0], int):
            return args[0]
    return None


def _http_status_from_exc(exc: BaseException) -> Optional[int]:
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        return status
    response = getattr(exc, "response", None)
    if response is not None:
        code = getattr(response, "status_code", None)
        if isinstance(code, int):
            return code
    return None


def is_retryable(exc: BaseException) -> bool:
    """True for transient network / 5xx / 429 failures against TopDesk or OpsRamp."""
    # Lazy imports avoid circular deps at module load.
    from sqlalchemy.exc import DisconnectionError, InterfaceError, OperationalError

    from app.models.OpsRamp_models import OpsRampAPIError
    from app.models.TopDesk_model import TopDeskAPIError

    if isinstance(exc, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
        return True
    if isinstance(exc, requests.exceptions.RequestException):
        if getattr(exc, "response", None) is None:
            return True
        status = _http_status_from_exc(exc)
        return status in RETRYABLE_HTTP_STATUS if status is not None else True
    if isinstance(exc, (TopDeskAPIError, OpsRampAPIError)):
        status = _http_status_from_exc(exc)
        return status is None or status in RETRYABLE_HTTP_STATUS
    if isinstance(exc, (InterfaceError, DisconnectionError)):
        return True
    if isinstance(exc, OperationalError):
        errno = _mysql_errno(exc)
        return errno in TRANSIENT_MYSQL_ERRNOS if errno is not None else False
    return False


def enqueue_failure(
    source: str,
    operation: str,
    opsramp_id: Optional[str],
    payload: str,
    exc: BaseException,
    max_attempts: Optional[int] = None,
    initial_status: str = "pending",
) -> Optional[int]:
    """
    Persist a failed operation for later retry or dead-letter review.
    Reuses an existing pending row for the same (source, opsramp_id, operation).
    Never raises — queue must not break the integration path.
    """
    engine = None
    try:
        if max_attempts is None:
            max_attempts = settings.retry_max_attempts
        now = datetime.now()
        http_status = _http_status_from_exc(exc)
        error_type = type(exc).__name__
        error_message = str(exc)

        engine = create_engine(DB_CONNECTION)
        Session = sessionmaker(bind=engine)
        with Session() as session:
            existing = None
            if opsramp_id:
                existing = (
                    session.query(FailedOperation)
                    .filter(
                        FailedOperation.source == source,
                        FailedOperation.opsramp_id == opsramp_id,
                        FailedOperation.operation == operation,
                        FailedOperation.status == "pending",
                    )
                    .first()
                )
            if existing is not None:
                existing.payload = payload
                existing.error_type = error_type
                existing.error_message = error_message
                existing.http_status = http_status
                existing.status = initial_status
                existing.updated_at = now
                # Keep next_attempt_at if already scheduled; otherwise schedule soon.
                if initial_status == "pending" and (
                    existing.next_attempt_at is None or existing.next_attempt_at > now + backoff(1)
                ):
                    existing.next_attempt_at = now
                session.commit()
                row_id = existing.id
            else:
                row = FailedOperation(
                    source=source,
                    operation=operation,
                    opsramp_id=opsramp_id,
                    payload=payload,
                    status=initial_status,
                    attempts=0,
                    max_attempts=max_attempts,
                    next_attempt_at=now,
                    error_type=error_type,
                    error_message=error_message,
                    http_status=http_status,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
                session.commit()
                session.refresh(row)
                row_id = row.id

        record_event(
            operation=operation,
            step="retry_enqueued",
            outcome="failure",
            opsramp_id=opsramp_id,
            error_type=error_type,
            error_message=error_message,
            http_status=http_status,
        )
        logger.info(
            f"Enqueued failed operation id={row_id} status={initial_status} "
            f"source={source} opsramp_id={opsramp_id}"
        )
        return row_id
    except Exception as e:
        logger.critical(
            f"Failed to enqueue retry: {e} | source={source} operation={operation} "
            f"opsramp_id={opsramp_id} payload={payload}"
        )
        return None
    finally:
        if engine is not None:
            engine.dispose()


def claim_due(limit: int) -> List[FailedOperation]:
    """
    Atomically claim due pending rows (and stale processing rows).
    Conditional UPDATE WHERE status='pending' makes two gunicorn workers safe.
    """
    engine = None
    claimed: List[FailedOperation] = []
    try:
        now = datetime.now()
        stale_before = now - timedelta(minutes=STALE_PROCESSING_MINUTES)
        engine = create_engine(DB_CONNECTION)
        Session = sessionmaker(bind=engine)
        with Session() as session:
            # Reset stale processing rows so they become claimable again.
            session.query(FailedOperation).filter(
                FailedOperation.status == "processing",
                FailedOperation.last_attempt_at < stale_before,
            ).update(
                {
                    FailedOperation.status: "pending",
                    FailedOperation.updated_at: now,
                },
                synchronize_session=False,
            )
            session.commit()

            candidates = (
                session.query(FailedOperation.id)
                .filter(
                    FailedOperation.status == "pending",
                    FailedOperation.next_attempt_at <= now,
                )
                .order_by(FailedOperation.next_attempt_at.asc())
                .limit(limit)
                .all()
            )
            for (row_id,) in candidates:
                updated = (
                    session.query(FailedOperation)
                    .filter(
                        FailedOperation.id == row_id,
                        FailedOperation.status == "pending",
                    )
                    .update(
                        {
                            FailedOperation.status: "processing",
                            FailedOperation.last_attempt_at: now,
                            FailedOperation.updated_at: now,
                        },
                        synchronize_session=False,
                    )
                )
                session.commit()
                if updated == 1:
                    row = session.query(FailedOperation).filter(FailedOperation.id == row_id).first()
                    if row is not None:
                        session.expunge(row)
                        claimed.append(row)
        return claimed
    except Exception as e:
        logger.error(f"Failed to claim due retries: {e}")
        return []
    finally:
        if engine is not None:
            engine.dispose()


def claim_by_id(row_id: int) -> Optional[FailedOperation]:
    """
    Force-claim a pending or dead row for manual retry.
    Returns None if not found; raises ValueError if already processing.
    """
    engine = None
    try:
        now = datetime.now()
        engine = create_engine(DB_CONNECTION)
        Session = sessionmaker(bind=engine)
        with Session() as session:
            row = session.query(FailedOperation).filter(FailedOperation.id == row_id).first()
            if row is None:
                return None
            if row.status == "processing":
                raise ValueError("already_processing")
            if row.status not in ("pending", "dead"):
                raise ValueError(f"invalid_status:{row.status}")
            updated = (
                session.query(FailedOperation)
                .filter(
                    FailedOperation.id == row_id,
                    FailedOperation.status.in_(["pending", "dead"]),
                )
                .update(
                    {
                        FailedOperation.status: "processing",
                        FailedOperation.last_attempt_at: now,
                        FailedOperation.updated_at: now,
                    },
                    synchronize_session=False,
                )
            )
            session.commit()
            if updated != 1:
                raise ValueError("already_processing")
            row = session.query(FailedOperation).filter(FailedOperation.id == row_id).first()
            if row is None:
                return None
            session.expunge(row)
            return row
    finally:
        if engine is not None:
            engine.dispose()


def mark_success(row_id: int) -> None:
    engine = None
    try:
        now = datetime.now()
        engine = create_engine(DB_CONNECTION)
        Session = sessionmaker(bind=engine)
        with Session() as session:
            row = session.query(FailedOperation).filter(FailedOperation.id == row_id).first()
            if row is None:
                return
            row.attempts = (row.attempts or 0) + 1
            row.status = "succeeded"
            row.updated_at = now
            row.last_attempt_at = now
            row.error_type = None
            row.error_message = None
            row.http_status = None
            session.commit()
            opsramp_id = row.opsramp_id
            operation = row.operation
        record_event(
            operation=operation,
            step="retry_succeeded",
            outcome="success",
            opsramp_id=opsramp_id,
        )
        logger.info(f"Retry succeeded for failed_operation id={row_id}")
    except Exception as e:
        logger.error(f"Failed to mark retry success id={row_id}: {e}")
    finally:
        if engine is not None:
            engine.dispose()


def mark_failure(row_id: int, exc: BaseException) -> None:
    engine = None
    try:
        now = datetime.now()
        http_status = _http_status_from_exc(exc)
        error_type = type(exc).__name__
        error_message = str(exc)
        engine = create_engine(DB_CONNECTION)
        Session = sessionmaker(bind=engine)
        with Session() as session:
            row = session.query(FailedOperation).filter(FailedOperation.id == row_id).first()
            if row is None:
                return
            row.attempts = (row.attempts or 0) + 1
            row.error_type = error_type
            row.error_message = error_message
            row.http_status = http_status
            row.last_attempt_at = now
            row.updated_at = now
            if row.attempts >= row.max_attempts:
                row.status = "dead"
            else:
                row.status = "pending"
                row.next_attempt_at = now + backoff(row.attempts)
            session.commit()
            opsramp_id = row.opsramp_id
            operation = row.operation
            status = row.status
            attempts = row.attempts
        record_event(
            operation=operation,
            step="retry_failed",
            outcome="failure",
            opsramp_id=opsramp_id,
            error_type=error_type,
            error_message=error_message,
            http_status=http_status,
        )
        logger.warning(
            f"Retry failed for failed_operation id={row_id} "
            f"attempts={attempts} status={status}: {error_type}"
        )
    except Exception as e:
        logger.error(f"Failed to mark retry failure id={row_id}: {e}")
    finally:
        if engine is not None:
            engine.dispose()


def cancel_operation(row_id: int) -> Optional[FailedOperation]:
    """Set status=cancelled. Returns updated row or None if not found."""
    engine = None
    try:
        now = datetime.now()
        engine = create_engine(DB_CONNECTION)
        Session = sessionmaker(bind=engine)
        with Session() as session:
            row = session.query(FailedOperation).filter(FailedOperation.id == row_id).first()
            if row is None:
                return None
            if row.status == "processing":
                raise ValueError("already_processing")
            if row.status in ("succeeded", "cancelled"):
                raise ValueError(f"invalid_status:{row.status}")
            row.status = "cancelled"
            row.updated_at = now
            session.commit()
            session.expunge(row)
            return row
    finally:
        if engine is not None:
            engine.dispose()


def get_by_id(row_id: int) -> Optional[FailedOperation]:
    engine = None
    try:
        engine = create_engine(DB_CONNECTION)
        Session = sessionmaker(bind=engine)
        with Session() as session:
            row = session.query(FailedOperation).filter(FailedOperation.id == row_id).first()
            if row is None:
                return None
            session.expunge(row)
            return row
    finally:
        if engine is not None:
            engine.dispose()


def list_operations(
    status: Optional[str] = None,
    opsramp_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[List[FailedOperation], int]:
    engine = None
    try:
        engine = create_engine(DB_CONNECTION)
        Session = sessionmaker(bind=engine)
        with Session() as session:
            query = session.query(FailedOperation)
            if status:
                query = query.filter(FailedOperation.status == status)
            if opsramp_id:
                query = query.filter(FailedOperation.opsramp_id == opsramp_id)
            total = query.count()
            rows = (
                query.order_by(FailedOperation.created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            for row in rows:
                session.expunge(row)
            return rows, total
    finally:
        if engine is not None:
            engine.dispose()
