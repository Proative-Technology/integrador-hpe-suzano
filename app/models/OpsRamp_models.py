import json
from typing import Optional, Dict, Any
from pydantic import ConfigDict
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeMeta
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.inspection import inspect
import requests
from app.config import settings
from app.logger import logger
from app.models.base import Base

#MODELS
from app.models.Control_model import Control
from app.models.TopDesk_model import TDIncident, TopDeskdata
from app.models.Catalog_model import resolve_catalog_match, extract_severity
from app.models.Audit_model import record_event, track

DB_CONNECTION = settings.conn_str
HTTP_TIMEOUT = 30


class OpsRampAPIError(Exception):
    """Structured OpsRamp API failure carrying HTTP status and response body."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        body: Optional[str] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


def compare_ticket_model_and_db(pydantic_model: BaseModel, sqlalchemy_instance: DeclarativeMeta) -> Dict[str, Dict[str, Any]]:
    """
    Compare a Pydantic TicketModel instance with a SQLAlchemy Ticket instance.
    
    Returns a dict with keys as field names and values as a dict of 'db' and 'model' differing values.
    """
    differences = {}

    # Get all columns from the SQLAlchemy instance
    mapper = inspect(sqlalchemy_instance.__class__)
    if not mapper:
        logger.error("SQLAlchemy instance does not have a mapper.")
        return differences

    db_fields = {column.key for column in mapper.attrs}


    for field in pydantic_model.__class__.model_fields:
        if field in db_fields:
            model_value = getattr(pydantic_model, field, None)
            db_value = getattr(sqlalchemy_instance, field, None)

            # Normalize if needed
            if model_value != db_value:
                differences[field] = {
                    'db': db_value,
                    'model': model_value
                }

    return differences



class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id = Column(String(255), primary_key=True)

    access_url = Column(Text, nullable=True)
    alert_ids = Column(String(255), nullable=True)
    alert_source = Column(String(255), nullable=True)
    alert_state = Column(String(100), nullable=True)
    assigned_device_ids = Column(Text, nullable=True)
    assigned_device_location = Column(String(255), nullable=True)
    assigned_names = Column(Text, nullable=True)
    assigned_user = Column(String(255), nullable=True)
    assignee_group_name = Column(String(255), nullable=True)
    associated_change_request_id = Column(String(255), nullable=True)
    associated_incident_id = Column(String(255), nullable=True)
    associated_problem_id = Column(String(255), nullable=True)

    attachment_base64_binary = Column(Text, nullable=True)
    attachment_file_name = Column(String(512), nullable=True)
    attachment_type = Column(String(255), nullable=True)

    category = Column(String(255), nullable=True)
    client_name = Column(String(255), nullable=True)
    client_unique_id = Column(String(255), nullable=True)
    comment = Column(Text, nullable=True)

    created_date = Column(String(100), nullable=True)
    created_date_1 = Column(DateTime, nullable=True)
    created_date_2 = Column(DateTime, nullable=True)
    created_date_iso8601 = Column(String(100), nullable=True)

    description = Column(Text, nullable=True)
    due_date = Column(String(100), nullable=True)
    external_ticket_id = Column(String(255), nullable=True)
    incident_id = Column(String(255), nullable=True)

    latest_comment_added_by = Column(String(255), nullable=True)
    latest_comment_description = Column(Text, nullable=True)
    latest_comment_subject = Column(String(512), nullable=True)
    latest_comment_visible_to_customer = Column(String(50), nullable=True)

    partner_name = Column(String(255), nullable=True)
    partner_unique_id = Column(String(255), nullable=True)
    priority = Column(String(100), nullable=True)
    priority_updated_by = Column(String(255), nullable=True)
    psa_ticket_id = Column(String(255), nullable=True)

    reason_to_change_status = Column(Text, nullable=True)
    reported_user_name = Column(String(255), nullable=True)
    resolution_summary = Column(Text, nullable=True)

    source_entity = Column(String(255), nullable=True)
    source_entity_id = Column(String(255), nullable=True)
    source_policy = Column(String(255), nullable=True)
    source_policy_id = Column(String(255), nullable=True)

    status = Column(String(100), nullable=True)
    status_updated_by = Column(String(255), nullable=True)
    sub_category = Column(String(255), nullable=True)
    subject = Column(String(512), nullable=True)
    suspend_end_date = Column(String(100), nullable=True)
    ticket_response_id = Column(String(255), nullable=True)

class TicketModel(BaseModel):
    access_url: Optional[HttpUrl] = None
    alert_ids: Optional[str] = None
    alert_source: Optional[str] = None
    alert_state: Optional[str] = None
    assigned_device_ids: Optional[str] = None
    assigned_device_location: Optional[str] = None
    assigned_names: Optional[str] = None
    assigned_user: Optional[str] = None
    assignee_group_name: Optional[str] = None
    associated_change_request_id: Optional[str] = None
    associated_incident_id: Optional[str] = None
    associated_problem_id: Optional[str] = None
    attachment_base64_binary: Optional[str] = None
    attachment_file_name: Optional[str] = None
    attachment_type: Optional[str] = None
    category: Optional[str] = None
    client_name: Optional[str] = None
    client_unique_id: Optional[str] = None
    comment: Optional[str] = None

    # Custom-parsable or unclear date formats left as strings
    created_date: Optional[str] = None
    created_date_1: Optional[datetime] = None
    created_date_2: Optional[datetime] = None
    created_date_iso8601: Optional[str] = None

    description: Optional[str] = None
    due_date: Optional[str] = None
    external_ticket_id: Optional[str] = None
    incident_id: Optional[str] = None
    latest_comment_added_by: Optional[str] = None
    latest_comment_description: Optional[str] = None
    latest_comment_subject: Optional[str] = None
    latest_comment_visible_to_customer: Optional[str] = None
    partner_name: Optional[str] = None
    partner_unique_id: Optional[str] = None
    priority: Optional[str] = None
    priority_updated_by: Optional[str] = None
    psa_ticket_id: Optional[str] = None
    reason_to_change_status: Optional[str] = None
    reported_user_name: Optional[str] = None
    resolution_summary: Optional[str] = None
    source_entity: Optional[str] = None
    source_entity_id: Optional[str] = None
    source_policy: Optional[str] = None
    source_policy_id: Optional[str] = None
    status: Optional[str] = None
    status_updated_by: Optional[str] = None
    sub_category: Optional[str] = None
    subject: Optional[str] = None
    suspend_end_date: Optional[str] = None
    ticket_response_id: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True,
        arbitrary_types_allowed=True,
    )

    def authenticate(self) -> str:
        logger.debug(f"Authenticating TicketModel with id {self.incident_id}.")
        url = f"{settings.opsramp_base_url}/tenancy/auth/oauth/token"
        payload = f"grant_type=client_credentials&client_id={settings.opsramp_client_id}&client_secret={settings.opsramp_client_secret}"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        response = requests.request("POST", url, headers=headers, data=payload, timeout=HTTP_TIMEOUT)
        if response.status_code != 200:
            logger.error(f"Erro ao autenticar: {response.status_code} - {response.text}")
            raise OpsRampAPIError(
                "Erro ao autenticar",
                status_code=response.status_code,
                body=response.text,
            )
        
        return response.json()['access_token']

    def to_topdesk(self):
        """
        Convert the TicketModel instance to a dictionary suitable for Topdesk API.
        """
        logger.debug(f"Converting TicketModel with id {self.incident_id} to Topdesk format.")
        if not self.incident_id:
            logger.error("Cannot convert TicketModel without incident_id.")
            raise ValueError("Cannot convert TicketModel without incident_id.")
        
        base_data = TopDeskdata(payload=None)

        # Severity -> (impact, urgency, priority). Lowest defaults when severity
        # cannot be located in the description.
        severity_map = {
            "CRITICAL": ("GRANDE", "ALTO", "PRIORIDADE 1"),
            "WARNING": ("MÉDIO", "MÉDIO", "PRIORIDADE 2"),
            "OK": ("PEQUENO", "BAIXO", "PRIORIDADE 3"),
            "INFO": ("PEQUENO", "BAIXO", "PRIORIDADE 4"),
        }

        # Default category/subcategory used when the catalog has no match.
        category_id = "9eca47e4-28cb-4964-84b8-eb70f7a62982"
        subcategory_id = base_data.getId("/tas/api/incidents/subcategories", "Infraestrutura")
        catalog_row = resolve_catalog_match(self.subject, self.description)
        if catalog_row is not None:
            category_id = str(catalog_row.category_id)
            subcategory_id = str(catalog_row.subcategory_id)
            logger.debug(
                f"Resolved category/subcategory from catalog for ticket {self.incident_id}: "
                f"category={category_id} subcategory={subcategory_id}"
            )
        else:
            logger.warning(
                f"No catalog match for ticket {self.incident_id}, using default category/subcategory."
            )

        alert_body_template = catalog_row.alert_body if catalog_row is not None else None
        severity = extract_severity(self.description, alert_body_template)
        if catalog_row is not None and str(catalog_row.category_name) == "HPE SUZANO - GATEWAY":
            severity = "CRITICAL"
            logger.debug(
                f"Category is GATEWAY for ticket {self.incident_id}, forcing severity to CRITICAL."
            )
        if severity in severity_map:
            inpacto, urgency, priority = severity_map[severity]
            logger.debug(f"Severity '{severity}' resolved for ticket {self.incident_id}.")
        else:
            inpacto, urgency, priority = "PEQUENO", "BAIXO", "PRIORIDADE 4"
            logger.warning(
                f"Could not resolve severity for ticket {self.incident_id}, "
                f"defaulting to '{inpacto}'/'{urgency}'/'{priority}'."
            )
        ticket_data = {
            # "caller": {
            #     "dynamicName": "Integrador Hpe",
            #     # "id": base_data.getId("/tas/api/persons", "integrador.hpe@proativetec.com.br"),
            #     "branch": {
            #         "id": "ffac733b-1da0-4f3e-972a-a085009c3734",
            #     },
            # },
            "callerLookup": {
                "email": "integrador.hpe@proativetec.com.br"
            },
            "status": 'secondLine',
            "action": "Ticket criado via Integrador OpsRamp",
            "briefDescription": f"OpsRamp - {self.incident_id}",
            # "request": self.description.replace("\n", "<br>") if self.description else "No description provided ",
            "request": self.description if self.description else "No description provided",
            "callType": {
                "id": base_data.getId("/tas/api/incidents/call_types", "INCIDENTE"),
            },
            "entryType": {
                "id": base_data.getId("/tas/api/incidents/entry_types", "AUTOMATICO"),
            },
            "category": {
                "id": category_id,
            },
            "subcategory": {
                "id": subcategory_id,
            },
            "impact": {
                "id": base_data.getId("/tas/api/incidents/impacts", inpacto),
            },
            "urgency": {
                "id": base_data.getId("/tas/api/incidents/urgencies", urgency),
            },
            "priority": {
                "id": base_data.getId("/tas/api/incidents/priorities", priority),
            },
            "duration": {
                "id": base_data.getId("/tas/api/incidents/durations", "1 hora"),
            },
            "operatorGroup": {
                "id": '176871b8-3ab5-4e70-8789-06d25dc55476',
            },
            "processingStatus": {
                "id": "a3e2ad64-16e2-4fe3-9c66-9e50ad9c4d69", # Assuming this is a valid ID for 'secondLine'
            },
        }
        td_data = TopDeskdata(payload=TDIncident(**ticket_data))
        return td_data

    def exists_db(self) -> bool:
        logger.debug(f"Checking if ticket with id {self.incident_id} exists in the database.")
        if not self.incident_id:
            logger.debug("No access_url provided, skipping existence check.")
            return False
        engine = create_engine(DB_CONNECTION)
        Session = sessionmaker(bind=engine)
        with Session() as session:
            exists = session.query(Control).filter(Control.opsramp_id == self.incident_id).first() is not None
            logger.debug(f"Ticket exists: {exists}") 
        engine.dispose()
        return exists
            
    def add_db(self) -> bool:
        add = False
        logger.debug(f"Adding ticket with id {self.incident_id} to the database.")
        if self.exists_db():
            tiket_id = self.update_db()
            logger.debug(f"Ticket with access_url {self.access_url} already exists, updated with id {tiket_id}.")
            add = True
        else:
            tiket_id = self.insert_db()
            logger.debug(f"Ticket with access_url {self.access_url} inserted with id {tiket_id}.")
        
        return add
        
    def update_db(self):
        logger.debug(f"Updating ticket with id {self.incident_id} in the database.")
        engine = create_engine(DB_CONNECTION)
        Session = sessionmaker(bind=engine)
        with Session() as session:
            control = session.query(Control).filter(Control.opsramp_id == self.incident_id).first()
            if control is None:
                logger.error(f"Ticket with id {self.incident_id} does not exist in the database.")
                raise ValueError(f"Ticket with id {self.incident_id} does not exist in the database.")
            session.query(Control).filter(Control.opsramp_id == self.incident_id).update(
                {
                    Control.status: self.status if self.status else control.status,
                    Control.updated_at: datetime.now(),
                }
            )
            session.commit()
            logger.debug(f"Ticket with id {self.incident_id} updated on database successfully.")
        engine.dispose()

    def insert_db(self):
        logger.debug(f"Inserting ticket with id {self.incident_id} into the database.")
        if not self.incident_id:
            logger.error("Cannot insert ticket without incident_id.")
            raise ValueError("Cannot insert ticket without incident_id.")
        engine = create_engine(DB_CONNECTION)
        Session = sessionmaker(bind=engine)
        with Session() as session:
            control = Control(
                opsramp_id=self.incident_id,
                status=self.status,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            session.add(control)
            session.commit()
            logger.debug(f"Ticket with id {self.incident_id} inserted on database successfully.")
        engine.dispose()

    def get_topdesk_id(self) -> Optional[str]:
        """
        Retrieve the Topdesk ID for the ticket from the database.
        """
        logger.debug(f"Retrieving Topdesk ID for ticket with id {self.incident_id}.")
        if not self.incident_id:
            logger.error("Cannot retrieve Topdesk ID without incident_id.")
            raise ValueError("Cannot retrieve Topdesk ID without incident_id.")
        engine = create_engine(DB_CONNECTION)
        Session = sessionmaker(bind=engine)
        with Session() as session:
            control = session.query(Control).filter(Control.opsramp_id == self.incident_id).first()
            if control is None:
                logger.debug(f"No control found for OpsRamp ID {self.incident_id}.")
                return None
            topdesk_id = control.topdesk_id
            logger.debug(f"Topdesk ID for ticket with id {self.incident_id} is {topdesk_id}.")
        engine.dispose()
        return str(topdesk_id) if topdesk_id else None

    def _audit_ctx(self, **extra: Any) -> Dict[str, Any]:
        """Base lookup keys for operation_events rows."""
        ctx: Dict[str, Any] = {
            "opsramp_id": self.incident_id,
            "access_url": str(self.access_url) if self.access_url else None,
            "subject": self.subject,
            "client_name": self.client_name,
        }
        ctx.update(extra)
        return ctx

    def update_td_ticketNumber(self, topdesk_id: str) -> None:
        """
        Update the Opsramp ticket with the corresponding topdesk ticket number.

        Non-2xx responses are recorded as opsramp_writeback failures but do not raise,
        preserving historical integration behaviour.
        """
        logger.debug(f"Updating Topdesk ticket number for ticket with id {self.incident_id}.")
        if not self.incident_id:
            logger.error("Cannot update Topdesk ticket number without incident_id.")
            raise ValueError("Cannot update Topdesk ticket number without incident_id.")
        started = datetime.now()
        url = f"{settings.opsramp_base_url}/api/v2/tenants/{settings.opsramp_tenant}/incidents/{self.incident_id}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.authenticate()}",
        }
        data = {
            "customFields": [
                {
                    "id": "UDF0000000073",
                    "value": topdesk_id
                }
            ],
        }
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=HTTP_TIMEOUT)
        duration_ms = int((datetime.now() - started).total_seconds() * 1000)
        audit = self._audit_ctx(topdesk_number=topdesk_id)
        if response.status_code in [200, 201]:
            logger.debug(f"Topdesk ticket number for ticket with id {self.incident_id} updated successfully.")
            record_event(
                operation="create",
                step="opsramp_writeback",
                outcome="success",
                duration_ms=duration_ms,
                http_status=response.status_code,
                **audit,
            )
        else:
            logger.error(
                f"Failed to update Topdesk ticket number for ticket with id {self.incident_id}. "
                f"Status code: {response.status_code}, Response: {response.text}"
            )
            record_event(
                operation="create",
                step="opsramp_writeback",
                outcome="failure",
                duration_ms=duration_ms,
                http_status=response.status_code,
                error_type="OpsRampAPIError",
                error_message=response.text,
                **audit,
            )

    def get_ticketdata(self) -> Optional[Ticket]:
        """
        Retrieve the ticket data from the database.
        """
        logger.debug(f"Retrieving ticket data for ticket with id {self.incident_id}.")
        if not self.incident_id:
            logger.error("Cannot retrieve ticket data without incident_id.")
            raise ValueError("Cannot retrieve ticket data without incident_id.")
        engine = create_engine(DB_CONNECTION)
        Session = sessionmaker(bind=engine)
        with Session() as session:
            ticket = session.query(Ticket).filter(Ticket.ticket_id == self.incident_id).first()
            if ticket is None:
                logger.debug(f"No ticket found with id {self.incident_id}.")
                return None
            logger.debug(f"Ticket data for ticket with id {self.incident_id} retrieved successfully.")
        engine.dispose()
        return ticket

    def save_tickdata(self) -> None:
        """
        Save the ticket data to the database.
        """
        logger.debug(f"Saving ticket data for ticket with id {self.incident_id}.")
        if not self.incident_id:
            logger.error("Cannot save ticket data without incident_id.")
            raise ValueError("Cannot save ticket data without incident_id.")
        engine = create_engine(DB_CONNECTION)
        Session = sessionmaker(bind=engine)
        with Session() as session:
            session.query(Ticket).filter(Ticket.ticket_id == self.incident_id).delete()
            ticket = Ticket(
                ticket_id=self.incident_id,
                **self.model_dump(exclude_none=True, exclude_unset=True, exclude={"access_url"}),
            )
            session.add(ticket)
            session.commit()
            logger.debug(f"Ticket data for ticket with id {self.incident_id} saved successfully.")
        engine.dispose()

    def add(self, retro: bool = False) -> None:
        """
        Add the ticket to the database and convert it to Topdesk format.
        """
        if not self.incident_id:
            logger.error("Cannot add ticket without incident_id.")
            raise ValueError("Cannot add ticket without incident_id.")
        logger.debug(f"Adding ticket with id {self.incident_id} to the database and converting to Topdesk format.")
        with track("create", "control_upsert", self._audit_ctx()):
            control_exists = self.add_db()
        if not control_exists or retro:
            with track("create", "catalog_resolve", self._audit_ctx()) as ctx:
                td_data = self.to_topdesk()
            logger.info(f"Ticket with id {self.incident_id} converted to Topdesk format successfully.")
            with track("create", "topdesk_create", self._audit_ctx()) as ctx:
                td_response = td_data.sendToTopDesk()
                ctx["topdesk_id"] = td_response.get("id", "")
                ctx["topdesk_number"] = td_response.get("number")
            control_data = {
                "status": td_response.get("status", "UNKNOWN"),
                "topdesk_id": td_response.get("id", ""),
                "topdesk_number": td_response.get("number"),
            }
            td_data.update_control(self.incident_id, control_data)
            logger.info(f"Ticket with id {self.incident_id} sent to Topdesk successfully number {td_response['id']}.")
            # opsramp_writeback records its own success/failure (non-raising on HTTP error)
            self.update_td_ticketNumber(td_response["number"])
            with track(
                "create",
                "db_save",
                self._audit_ctx(
                    topdesk_id=td_response.get("id"),
                    topdesk_number=td_response.get("number"),
                ),
            ):
                self.save_tickdata()
            logger.info(f"Ticket with id {self.incident_id} saved to database successfully.")
        else:
            logger.info(f"Ticket with id {self.incident_id} already exists in the database.")
            topdesk_id = self.get_topdesk_id()
            if not topdesk_id:
                logger.error(f"Ticket with id {self.incident_id} exists in the database but has no Topdesk ID.")
                self.add(retro=True)
            old_ticket = self.get_ticketdata()
            if not old_ticket:
                logger.error(f"Ticket with id {self.incident_id} exists in the database but could not retrieve ticket data.")
                self.save_tickdata()
                raise ValueError(f"Ticket with id {self.incident_id} exists in the database but could not retrieve ticket data.")
            differences = compare_ticket_model_and_db(self, old_ticket)
            if differences:
                logger.info(f"Ticket with id {self.incident_id} has differences with the database: {differences}.")
                with track("update", "catalog_resolve", self._audit_ctx(topdesk_id=topdesk_id)):
                    td_data = self.to_topdesk()
                topdesk_id = self.get_topdesk_id()
                if not topdesk_id:
                    logger.error(f"Ticket with id {self.incident_id} has no Topdesk ID, cannot update ticket.")
                    raise ValueError(f"Ticket with id {self.incident_id} has no Topdesk ID, cannot update ticket.")
                differences_str = "\n ".join([f"{k}: {v['db']} -> {v['model']}" for k, v in differences.items()])
                update_data = {
                    "action": f"Campos atualizados no OpsRamp - {differences_str}",
                }
                with track("update", "topdesk_update", self._audit_ctx(topdesk_id=topdesk_id)):
                    td_data.update_ticket(topdesk_id, update_data)
                with track("update", "db_save", self._audit_ctx(topdesk_id=topdesk_id)):
                    self.save_tickdata()
                logger.info(f"Ticket with id {self.incident_id} updated in Topdesk successfully.")
            else:
                record_event(
                    operation="skip",
                    step="no_change",
                    outcome="success",
                    **self._audit_ctx(topdesk_id=topdesk_id),
                )
                logger.info(f"Ticket with id {self.incident_id} has no differences; recorded no_change.")

        if self.status == "Closed" or self.status == "Resolved":
            logger.debug(f"Ticket with id {self.incident_id} is closed, updating control status.")
            td_ticket_id = self.get_topdesk_id()
            if not td_ticket_id:
                logger.error(f"Ticket with id {self.incident_id} has no Topdesk ID, cannot close ticket.")
                raise ValueError(f"Ticket with id {self.incident_id} has no Topdesk ID, cannot close ticket.")
            with track("close", "catalog_resolve", self._audit_ctx(topdesk_id=td_ticket_id)):
                td_data = self.to_topdesk()
            control_data = {
                "status": self.status,
                "topdesk_id": td_ticket_id,
            }
            td_data.update_control(self.incident_id, control_data)
            logger.debug(f"Ticket with id {self.incident_id} updated on database successfully.")
            with track("close", "topdesk_close", self._audit_ctx(topdesk_id=td_ticket_id)):
                td_data.close_ticket(td_ticket_id)
            logger.debug(f"Ticket with id {self.incident_id} closed successfully in Topdesk.")

