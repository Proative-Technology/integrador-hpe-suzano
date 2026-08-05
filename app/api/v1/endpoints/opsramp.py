from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from app.logger import logger

#MODELS
from app.models.OpsRamp_models import TicketModel

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
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"message": "Failed to create ticket"})
