
from datetime import datetime
import json
import requests
from requests.auth import HTTPBasicAuth
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unidecode import unidecode
from app.config import settings
from app.logger import logger
from urllib.parse import quote


# MODELS
from app.models.Control_model import Control


DB_CONNECTION = settings.conn_str
HTTP_TIMEOUT = 30


class TopDeskAPIError(Exception):
    """Structured TopDesk API failure carrying HTTP status and response body."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        body: Optional[str] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class Branch(BaseModel):
    id: str


class Caller(BaseModel):
    dynamicName: str
    branch: Branch


class Category(BaseModel):
    id: str


class Subcategory(BaseModel):
    id: str


class CallType(BaseModel):
    id: str


class EntryType(BaseModel):
    id: str


class Impact(BaseModel):
    id: str


class Urgency(BaseModel):
    id: str


class Priority(BaseModel):
    id: str


class Duration(BaseModel):
    id: str


class OperatorGroup(BaseModel):
    id: str


class ProcessingStatus(BaseModel):
    id: str

class ClosureCode(BaseModel):
    id: str
    name: str

class callerlookup(BaseModel):
    email: str



class TDIncident(BaseModel):
    status: Optional[str] = None
    request: Optional[str] = None
    action: Optional[str] = None
    caller: Optional[Caller] = None
    callerLookup: Optional[callerlookup] = None
    briefDescription: Optional[str] = None 
    category: Optional[Category] = None
    subcategory: Optional[Subcategory] = None
    callType: Optional[CallType] = None
    entryType: Optional[EntryType] = None
    impact: Optional[Impact] = None
    urgency: Optional[Urgency] = None
    priority: Optional[Priority] = None
    duration: Optional[Duration] = None
    operatorGroup: Optional[OperatorGroup] = None
    processingStatus: Optional[ProcessingStatus] = None
    responded: Optional[bool] = False
    closed: Optional[bool] = False
    respondedDate: Optional[datetime] = None
    closureCode: Optional[ClosureCode] = None

class TopDeskdata(BaseModel):
    payload: Optional[TDIncident]
    baseUrl: str = settings.topdesk_base_url
    user: str = settings.topdesk_user
    password: str = settings.topdesk_password

    def getTopdeskToken(self):
        url = self.baseUrl + "/tas/api/login/operator"
        headers = {"Content-type": 'text/plain;charset="UTF-8"'}
        r = requests.get(url, auth=(self.user, self.password), headers=headers, timeout=HTTP_TIMEOUT)
        if r.status_code != 200:
            logger.error(f"Erro ao gerar token: {r.status_code} - {r.text}")
            raise TopDeskAPIError("Erro ao gerar token", status_code=r.status_code, body=r.text)
        return str(r.text)
    
    def getId(self,endpoint: str, itype: str, sc: str = "") -> str:
        """
        Retrieves an ID from the TopDesk API based on the provided endpoint, itype, and sc.

        Args:
            endpoint (str): The endpoint to query in the TopDesk API.
            itype (str): The type of ID to retrieve.
            sc (str, optional): Additional search criteria. Defaults to "".

        Returns:
            str: The retrieved ID or "-1" if not found.
        """
        url = self.baseUrl + endpoint
        ntype = ""
        headers = {
            "Content-type": 'application/json;charset="UTF-8"',
        }
        if "persons" in endpoint:
            if "@" in itype:
                url = url + "?query=email=='" + quote(itype) + "'"
            else:
                ntype = itype.replace(".", " ")
                url = url + "?query=dynamicName=='" + quote(ntype) + "'"
        if "operatorgroups" in endpoint:
            url = url + "?start=0&page_size=100"
            ntype = itype.upper()

        r = requests.get(
            url,
            auth=HTTPBasicAuth(self.user, self.password),
            headers=headers,
            timeout=HTTP_TIMEOUT,
        )
        if r.status_code != 200:
            logger.error(f"Erro ao coletar ID {endpoint} - {itype}: {r.status_code} - {r.text}")
            raise TopDeskAPIError(
                f"Erro ao coletar ID {endpoint} - {itype}",
                status_code=r.status_code,
                body=r.text,
            )
        data = r.json()
        id = None
        for item in data:
            if "operatorgroups" in endpoint:
                if ntype in item["groupName"]:
                    id = item["id"]
                    break
            elif "subcategories" in endpoint:
                if itype in item["name"] and sc in item["category"]["name"]:
                    id = item["id"]
                    break
            elif "processing_status" in endpoint or "closure_codes" in endpoint:
                if itype in item["name"]:
                    id = item
                    break
            elif "durations" in endpoint:
                if unidecode(itype).lower() in unidecode(item["name"]).lower():
                    id = item["id"]
                    break
            elif unidecode(itype) in unidecode(item["name"]):
                id = item["id"]
                break
        return id if id else "-1"
    
    def sendToTopDesk(self):
        url = self.baseUrl + "/tas/api/incidents"
        headers = {
            "Content-type": 'application/json;charset="UTF-8"',
        }
        if self.payload is None:
            logger.error("Payload cannot be None")
            raise ValueError("Payload cannot be None")
        r = requests.post(
            url,
            auth=HTTPBasicAuth(self.user, self.password),
            headers=headers,
            data=self.payload.model_dump_json(exclude_none=True, exclude_unset=True),
            timeout=HTTP_TIMEOUT,
        )
        logger.info(f'Reqquest {r.request.body} - {r.request.url} - {r.request.headers} - {r.request.method}')
        if r.status_code not in [200, 201]:
            logger.info(f"Data sent to Topdesk: {self.payload.model_dump_json(exclude_none=True, exclude_unset=True)}")
            logger.error(f"Erro ao enviar incidente: {r.status_code} - {r.text} - {r.json()}")
            if 'category' in r.text or 'subcategory' in r.text:
                logger.error(f"Erro enviar categoria ou subcategoria: {r.text} - self.payload: {self.payload.model_dump_json(exclude_none=True, exclude_unset=True)['category']} - {self.payload.model_dump_json(exclude_none=True, exclude_unset=True)['subcategory']}")
            raise TopDeskAPIError(
                f"Erro ao enviar incidente: {r.status_code}--{r.text}",
                status_code=r.status_code,
                body=r.text,
            )
        logger.debug(f"Data: {r.json()}")
        incident_id = r.json()['id']
        logger.info(f"Incident created successfully with ID: {incident_id}") 
  
        return r.json()
    
    def update_control(self, opsramp_id: str, data: dict):
        logger.debug(f"Updating control with OpsRamp ID {opsramp_id} in the database.")
        engine = create_engine(DB_CONNECTION)
        Session = sessionmaker(bind=engine)
        update_data = {
            Control.status: data.get("status"),
            Control.updated_at: datetime.now(),
        }
        if "topdesk_id" in data:
            update_data[Control.topdesk_id] = data.get("topdesk_id")
        if "topdesk_number" in data:
            update_data[Control.topdesk_number] = data.get("topdesk_number")
        with Session() as session:
            control = session.query(Control).filter(Control.opsramp_id == opsramp_id).first()
            if control is None:
                logger.error(f"Control with OpsRamp ID {opsramp_id} does not exist in the database.")
                raise ValueError(f"Control with OpsRamp ID {opsramp_id} does not exist in the database.")
            session.query(Control).filter(Control.opsramp_id == opsramp_id).update(update_data)
            session.commit()
            logger.debug(f"Control with OpsRamp ID {opsramp_id} updated successfully.")
        engine.dispose()


    def update_ticket(self, topdesk_id: str, data: dict):
        url = self.baseUrl + f"/tas/api/incidents/id/{topdesk_id}"
        headers = {
            "Content-type": 'application/json;charset="UTF-8"',
        }
        r = requests.put(
            url,
            auth=HTTPBasicAuth(self.user, self.password),
            headers=headers,
            data=json.dumps(data),
            timeout=HTTP_TIMEOUT,
        )
        logger.debug(f'Reqquest {r.request.body} - {r.request.url} - {r.request.headers} - {r.request.method}')
        if r.status_code != 200:
            logger.error(f"Erro ao atualizar ticket: {r.status_code} - {r.text}")
            raise TopDeskAPIError(
                f"Erro ao atualizar ticket: {r.status_code} - {r.text}",
                status_code=r.status_code,
                body=r.text,
            )
        logger.info(f"Ticket {topdesk_id} atualizado com sucesso.")

    def close_ticket(self, topdesk_id: str):
        url = self.baseUrl + f"/tas/api/incidents/id/{topdesk_id}"
        headers = {
            "Content-type": 'application/json;charset="UTF-8"',
        }
        closure_code_id = self.getId("/tas/api/incidents/closure_codes", "Normalizado Automático")
        status_id = self.getId("/tas/api/incidents/statuses", "Resolvido")
        data = {
            # "closed": True,
            # "closedDate": datetime.now().strftime("%Y-%m-%d"),
            # "closureCode": closure_code_id,
            "processingStatus": {
                "id": status_id
            },
            "action": "Incidente encerrado no OpsRamp",
        }
        r = requests.put(
            url,
            auth=HTTPBasicAuth(self.user, self.password),
            headers=headers,
            data=json.dumps(data),
            timeout=HTTP_TIMEOUT,
        )
        logger.debug(f'Reqquest {r.request.body} - {r.request.url} - {r.request.headers} - {r.request.method}')
        if r.status_code != 200:
            logger.error(f"Erro ao fechar ticket: {r.status_code} - {r.text}")
            raise TopDeskAPIError(
                f"Erro ao fechar ticket: {r.status_code} - {r.text}",
                status_code=r.status_code,
                body=r.text,
            )
        logger.info(f"Ticket {topdesk_id} fechado com sucesso.")


class TopDeskCloseModel(BaseModel):
    id: str
    status: str
    closureCode: ClosureCode
    closed: bool = True
    closedDate: datetime = datetime.now()
