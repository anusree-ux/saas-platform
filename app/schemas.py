from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class TenantCreate(BaseModel):
    name: str


class TenantResponse(BaseModel):
    tenant_id: UUID
    name: str
    api_key: str

class EventCreate(BaseModel):
    event_name: str
    idempotency_key: str
    properties: dict[str, Any]
    occurred_at: datetime


class EventResponse(BaseModel):
    id: UUID
    event_name: str
    properties: dict[str, Any]
    occurred_at: datetime
    received_at: datetime