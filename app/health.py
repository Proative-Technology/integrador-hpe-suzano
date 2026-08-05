from typing import Dict, Optional

import requests
from requests.auth import HTTPBasicAuth
from sqlalchemy import create_engine, text

from app.config import settings
from app.logger import logger

# Per-service timeout (seconds) to keep the health route from hanging.
HEALTH_TIMEOUT = 10


def _ok() -> Dict[str, Optional[str]]:
    return {"status": "ok", "detail": None}


def _down(detail: str) -> Dict[str, Optional[str]]:
    return {"status": "down", "detail": detail}


def check_db() -> Dict[str, Optional[str]]:
    """Verify the database connection by running a trivial query."""
    engine = None
    try:
        engine = create_engine(settings.conn_str)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return _ok()
    except Exception as e:
        logger.error(f"Health check - database down: {e}")
        return _down(str(e))
    finally:
        if engine is not None:
            engine.dispose()


def check_topdesk() -> Dict[str, Optional[str]]:
    """Verify the TopDesk API using the same basic-auth pattern the app uses
    for real calls (the /login/operator endpoint rejects basic auth with 401)."""
    try:
        url = settings.topdesk_base_url + "/tas/api/incidents/call_types"
        headers = {"Content-type": 'application/json;charset="UTF-8"'}
        r = requests.get(
            url,
            auth=HTTPBasicAuth(settings.topdesk_user, settings.topdesk_password),
            headers=headers,
            timeout=HEALTH_TIMEOUT,
        )
        if r.status_code == 200:
            return _ok()
        return _down(f"HTTP {r.status_code}")
    except Exception as e:
        logger.error(f"Health check - topdesk down: {e}")
        return _down(str(e))


def check_opsramp() -> Dict[str, Optional[str]]:
    """Verify the OpsRamp API via the OAuth token endpoint."""
    try:
        url = settings.opsramp_base_url + "/tenancy/auth/oauth/token"
        payload = (
            f"grant_type=client_credentials"
            f"&client_id={settings.opsramp_client_id}"
            f"&client_secret={settings.opsramp_client_secret}"
        )
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        r = requests.post(url, headers=headers, data=payload, timeout=HEALTH_TIMEOUT)
        if r.status_code == 200:
            return _ok()
        return _down(f"HTTP {r.status_code}")
    except Exception as e:
        logger.error(f"Health check - opsramp down: {e}")
        return _down(str(e))
