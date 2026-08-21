import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models.base import Base
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import mysql

#logging
from app.logger import logger

#Model
from app.models.Control_model import Control
from app.models.OpsRamp_models import Ticket
from app.models.Catalog_model import CategoryCatalog
from app.models.Audit_model import OperationEvent  # noqa: F401 — register with Base.metadata
from app.models.Retry_model import FailedOperation  # noqa: F401 — register with Base.metadata

DB_CONNECTION = settings.conn_str

CATALOG_CSV = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "catalog.csv"
)


def load_catalog(engine):
    """
    Populate the category_catalog table from app/data/catalog.csv when empty.
    """
    if not os.path.exists(CATALOG_CSV):
        logger.warning(f"Catalog CSV not found at {CATALOG_CSV}, skipping catalog load.")
        return

    Session = sessionmaker(bind=engine)
    with Session() as session:
        if session.query(CategoryCatalog).first() is not None:
            logger.debug("category_catalog already populated, skipping load.")
            return

        with open(CATALOG_CSV, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=";")
            rows = [
                CategoryCatalog(
                    monitor_name=row.get("monitor_name") or None,
                    metric_name=row.get("metric_name") or None,
                    subcatgoria=row.get("subcatgoria") or None,
                    category_name=row.get("category_name") or None,
                    subcategory_name=row.get("subcategory_name") or None,
                    category_id=row.get("category_id") or None,
                    subcategory_id=row.get("subcategory_id") or None,
                    alert_subject=row.get("alert_subject") or None,
                    alert_body=row.get("alert_body") or None,
                )
                for row in reader
            ]

        if rows:
            session.bulk_save_objects(rows)
            session.commit()
            logger.info(f"Loaded {len(rows)} rows into category_catalog.")
        else:
            logger.warning("Catalog CSV had no rows to load.")


def init_db():
    """
    Initialize the database and create tables if they do not exist.
    """
    try:
        # Create an engine
        engine = create_engine(DB_CONNECTION, echo=True, future=True)

        # Create all tables in the database
        Base.metadata.create_all(engine)

        # Populate the category catalog if needed
        load_catalog(engine)

        # Log the successful initialization
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
