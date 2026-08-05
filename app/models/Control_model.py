from sqlalchemy import Column, String, DateTime, Integer
from app.models.base import Base
from app.config import settings


DB_CONNECTION = settings.conn_str

class Control(Base):
    __tablename__ = 'control'

    id = Column(Integer, primary_key=True, autoincrement=True)
    opsramp_id = Column(String(255), nullable=False, unique=True)
    topdesk_id = Column(String(255), nullable=True, unique=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=False)

    
