from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from app.logger import logger

#MODELS
from app.models.OpsRamp_models import TicketModel

router = APIRouter()

@router.get("/close", status_code=status.HTTP_200_OK)
async def close_ticket():
    """
    Close a ticket in topdesk.
    """
    try:
        # Logic to close the ticket would go here
        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Ticket closed successfully"})
    except Exception as e:
        logger.error(f"Error closing ticket: {e}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"message": "Failed to close ticket"})

@router.post("/ticket", status_code=status.HTTP_201_CREATED)
async def create_ticket(ticket: TicketModel):
    """
    update a new ticket in topdesk.
    """
    try:
        
        return JSONResponse(status_code=status.HTTP_201_CREATED, content={"message": "Ticket created successfully"})
    except Exception as e:
        logger.error(f"Error creating ticket: {e}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"message": "Failed to create ticket"})
