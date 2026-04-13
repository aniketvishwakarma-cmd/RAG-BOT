from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class AuditLogSchema(BaseModel):
    id: str
    action: str
    entity_type: str
    entity_id: str
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    status: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    class Config:
        from_attributes = True


class AuditValidationRequest(BaseModel):
    query_id: str
    status: str
    notes: Optional[str] = None
    reviewer_id: Optional[str] = "auditor"

