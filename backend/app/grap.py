"""Manually recorded CAQM orders for Delhi-NCR."""
from contextlib import contextmanager
from datetime import datetime
from hmac import compare_digest
from os import environ

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg import OperationalError
from psycopg.rows import dict_row
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, field_validator

from backend.db.migrate import connect

router = APIRouter(tags=["GRAP"])


class Order(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stage: int = Field(strict=True, ge=0, le=4)
    effective_from: AwareDatetime
    source_url: HttpUrl

    @field_validator("source_url")
    @classmethod
    def official_order(cls, url):
        if (url.scheme != "https" or url.host not in {"caqm.nic.in", "www.caqm.nic.in"}
                or url.username or url.password or url.port != 443
                or not (url.path or "").lower().endswith(".pdf")):
            raise ValueError("Enter the HTTPS link to the CAQM order PDF")
        return url


class RecordedOrder(Order):
    entered_at: datetime


class Status(BaseModel):
    order: RecordedOrder | None


def require_admin(auth: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False))):
    token = environ.get("GRAP_ADMIN_TOKEN")
    if not token:
        raise HTTPException(503, "GRAP updates are disabled")
    if not auth or not compare_digest(auth.credentials.encode(), token.encode()):
        raise HTTPException(401, "Invalid admin token", headers={"WWW-Authenticate": "Bearer"})


@contextmanager
def database():
    try:
        with connect() as db:
            db.row_factory = dict_row
            yield db
    except OperationalError:
        raise HTTPException(503, "GRAP storage unavailable") from None


@router.get("/grap/status", response_model=Status)
def status():
    with database() as db:
        order = db.execute("""SELECT stage, effective_from, source_url, entered_at
                              FROM grap_status WHERE effective_from <= CURRENT_TIMESTAMP
                              ORDER BY effective_from DESC LIMIT 1""").fetchone()
    return {"order": order}


@router.put("/admin/grap-status", response_model=RecordedOrder, dependencies=[Depends(require_admin)])
def record(order: Order):
    with database() as db:
        return db.execute("""
            INSERT INTO grap_status AS saved (stage, effective_from, source_url)
            VALUES (%s, %s, %s)
            ON CONFLICT (effective_from) DO UPDATE SET
                stage = EXCLUDED.stage, source_url = EXCLUDED.source_url,
                entered_at = CASE WHEN (saved.stage, saved.source_url) =
                                       (EXCLUDED.stage, EXCLUDED.source_url)
                                  THEN saved.entered_at ELSE CURRENT_TIMESTAMP END
            RETURNING stage, effective_from, source_url, entered_at
        """, (order.stage, order.effective_from, str(order.source_url))).fetchone()
