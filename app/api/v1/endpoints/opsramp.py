from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from app.logger import logger

#MODELS
from app.models.OpsRamp_models import TicketModel
from app.models.Audit_model import record_event
from app.models.Retry_model import enqueue_failure, is_retryable
from app.config import settings

router = APIRouter()

@router.post("/ticket", status_code=status.HTTP_201_CREATED)
async def create_ticket(ticket: TicketModel):
    """
    update a new ticket in OpsRamp.
    """
    try:
        logger.info(f"Creating ticket with data: {ticket}")
        ticket.add()
        return JSONResponse(status_code=status.HTTP_201_CREATED, content={"message": "Ticket created successfully"})
    except Exception as e:
        logger.error(f"Error creating ticket: {e}")
        if not getattr(e, "_operation_event_recorded", False):
            record_event(
                operation="create",
                step="unhandled",
                outcome="failure",
                opsramp_id=ticket.incident_id,
                access_url=str(ticket.access_url) if ticket.access_url else None,
                subject=ticket.subject,
                client_name=ticket.client_name,
                error_type=type(e).__name__,
                error_message=str(e),
            )
        if is_retryable(e):
            queue_id = enqueue_failure(
                source="opsramp_ticket",
                operation="create",
                opsramp_id=ticket.incident_id,
                payload=ticket.model_dump_json(),
                exc=e,
                max_attempts=settings.retry_max_attempts,
            )
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "message": "Transient failure; operation queued for retry",
                    "retry_id": queue_id,
                },
            )
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"message": "Failed to create ticket"})
