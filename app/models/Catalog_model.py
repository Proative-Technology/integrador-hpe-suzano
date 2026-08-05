import re
from typing import Optional, Tuple

from sqlalchemy import Column, Integer, String, Text, create_engine, literal
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.logger import logger
from app.models.base import Base


DB_CONNECTION = settings.conn_str

#GATEWAY_FALLBACK_CATEGORY_ID = "9206469b-3e39-4ba1-94cc-7b7d9014547a"
#GATEWAY_FALLBACK_SUBCATEGORY_ID = "ab3b3662-45e7-44f0-84f8-c1883fae4aab"

GATEWAY_FALLBACK_CATEGORY_ID = "50f95365-ffbf-4dfd-9096-6b2262202587"
GATEWAY_FALLBACK_SUBCATEGORY_ID = "c1808480-538e-448e-b87e-ce6c4eefcb7f"

class CategoryCatalog(Base):
    __tablename__ = "category_catalog"

    id = Column(Integer, primary_key=True, autoincrement=True)
    monitor_name = Column(String(255), nullable=True)
    metric_name = Column(String(255), nullable=True)
    subcatgoria = Column(String(255), nullable=True)
    category_name = Column(String(255), nullable=True)
    subcategory_name = Column(String(255), nullable=True)
    category_id = Column(String(64), nullable=True)
    subcategory_id = Column(String(64), nullable=True)
    alert_subject = Column(Text, nullable=True)
    alert_body = Column(Text, nullable=True)


def resolve_catalog_match(subject: Optional[str], description: Optional[str]) -> Optional[CategoryCatalog]:
    """
    Resolve the matching catalog row for an OpsRamp ticket by matching its
    subject/description against the catalog.

    Matching is done in SQL (no full in-memory load): a catalog row matches when
    the ticket text contains the row's metric_name (more specific) or, failing
    that, its monitor_name. Returns the full matched row (detached) so callers
    can read category_id, subcategory_id and alert_body. Returns None when
    nothing matches.
    """
    text = f"{subject or ''} {description or ''}".strip()
    if not text:
        return None

    engine = create_engine(DB_CONNECTION)
    Session = sessionmaker(bind=engine)
    match = None
    try:
        with Session() as session:
            # Prefer metric_name (more specific) before monitor_name.
            for column in (CategoryCatalog.metric_name, CategoryCatalog.monitor_name):
                row = (
                    session.query(CategoryCatalog)
                    .filter(column.isnot(None))
                    .filter(column != "")
                    .filter(CategoryCatalog.category_id.isnot(None))
                    .filter(CategoryCatalog.subcategory_id.isnot(None))
                    .filter(literal(text).contains(column))
                    .first()
                )
                if row is not None:
                    session.expunge(row)
                    match = row
                    logger.debug(
                        f"Catalog match on {column.key}='{getattr(row, column.key)}' -> "
                        f"category={row.category_id} subcategory={row.subcategory_id}"
                    )
                    break
    finally:
        engine.dispose()

    if match is None and ("gateway" in (description or "").lower() or "gateway" in (subject or "").lower() or "SSL Certificate is missing" in (description or "") or "SSL Certificate is missing" in (subject or "") ):
        match = CategoryCatalog(
            category_name="HPE SUZANO - GATEWAY",
            subcategory_name="SERVICE.STATUS",
            category_id=GATEWAY_FALLBACK_CATEGORY_ID,
            subcategory_id=GATEWAY_FALLBACK_SUBCATEGORY_ID,
        )
        logger.debug(
            "Gateway keyword fallback applied -> category/subcategory forced to GATEWAY/SERVICE.STATUS"
        )

    if match is None:
        logger.debug("No catalog match found for ticket subject/description.")
    return match


def resolve_category(subject: Optional[str], description: Optional[str]) -> Optional[Tuple[str, str]]:
    """
    Resolve the TopDesk (category_id, subcategory_id) for an OpsRamp ticket by
    matching its subject/description against the catalog. Returns None when
    nothing matches.
    """
    row = resolve_catalog_match(subject, description)
    if row is None:
        return None
    return (str(row.category_id), str(row.subcategory_id))


_CANONICAL_SEVERITIES = {"CRITICAL", "WARNING", "OK", "INFO"}


def _canonical_severity(raw: Optional[str]) -> Optional[str]:
    """Normalize a raw severity token to its canonical upper-case value."""
    if not raw:
        return None
    value = raw.strip().strip(".,;:-").upper()
    if value in _CANONICAL_SEVERITIES:
        return value
    logger.debug(f"Extracted severity '{value}' is not a recognized value.")
    return None


def _escape_whitespace_tolerant(literal: str) -> str:
    """
    Escape a literal template chunk for regex use while treating any run of
    whitespace as flexible. OpsRamp descriptions drift from the catalog template
    on whitespace (leading spaces on continuation lines, newlines, non-breaking
    \\xa0 spaces), so literal whitespace must match one-or-more whitespace chars.
    """
    parts = re.split(r"\s+", literal)
    escaped = [re.escape(part) for part in parts if part != ""]
    pattern = r"\s+".join(escaped)
    # Allow optional surrounding whitespace that was trimmed from the ends.
    if literal[:1].isspace():
        pattern = r"\s*" + pattern
    if literal[-1:].isspace():
        pattern = pattern + r"\s*"
    return pattern


def _extract_severity_from_template(description: str, alert_body_template: str) -> Optional[str]:
    """Locate ${severity} in the template and match it against the description."""
    tokens = re.split(r"(\$\{[^}]+\})", alert_body_template)
    pattern_parts = []
    sev_seen = False
    for token in tokens:
        placeholder = re.fullmatch(r"\$\{([^}]+)\}", token)
        if placeholder:
            if placeholder.group(1).strip() == "severity" and not sev_seen:
                pattern_parts.append(r"(?P<sev>\S+)")
                sev_seen = True
            else:
                pattern_parts.append(r".+?")
        else:
            pattern_parts.append(_escape_whitespace_tolerant(token))

    if not sev_seen:
        return None

    match = re.search("".join(pattern_parts), description, re.DOTALL)
    if not match:
        return None
    return _canonical_severity(match.group("sev"))


def _extract_severity_direct(description: str) -> Optional[str]:
    """
    Template-independent fallback: scan the description for the canonical
    OpsRamp 'Severity:' field.
    """
    match = re.search(r"Severity:\s*([A-Za-z]+)", description, re.IGNORECASE)
    if not match:
        return None
    return _canonical_severity(match.group(1))


def extract_severity(description: Optional[str], alert_body_template: Optional[str]) -> Optional[str]:
    """
    Extract the alert severity from a ticket description.

    First tries to match the catalog alert_body template (locating the
    ${severity} placeholder) with whitespace-tolerant matching, then falls back
    to a direct scan of the description's 'Severity:' field. Works even when no
    template is available.

    Returns the canonical upper-case severity (CRITICAL/WARNING/OK/INFO) when it
    can be located, otherwise None.
    """
    if not description:
        return None

    if alert_body_template:
        severity = _extract_severity_from_template(description, alert_body_template)
        if severity is not None:
            return severity

    return _extract_severity_direct(description)
