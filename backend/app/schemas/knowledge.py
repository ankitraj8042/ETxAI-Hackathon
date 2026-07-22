"""
DCBrain Pydantic Schemas — Knowledge & RFIs
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from app.models.knowledge import RFIStatus, RFIPriority


class ProjectDocumentBase(BaseModel):
    doc_code: str
    title: str
    doc_type: Optional[str] = None
    category: Optional[str] = None
    file_name: Optional[str] = None
    file_size_bytes: Optional[int] = 0
    chunk_count: Optional[int] = 0
    is_indexed: Optional[bool] = False
    content_summary: Optional[str] = None


class ProjectDocumentResponse(ProjectDocumentBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class RFIBase(BaseModel):
    rfi_number: str
    subject: str
    question: str
    answer: Optional[str] = None
    status: Optional[RFIStatus] = RFIStatus.OPEN
    priority: Optional[RFIPriority] = RFIPriority.MEDIUM
    category: Optional[str] = None
    discipline: Optional[str] = None
    raised_by: Optional[str] = None
    assigned_to: Optional[str] = None
    resolution_time_hours: Optional[float] = None
    similar_rfis: Optional[List[str]] = None
    equipment_id: Optional[UUID] = None


class RFIResponse(RFIBase):
    id: UUID
    raised_date: datetime
    due_date: Optional[datetime] = None
    answered_date: Optional[datetime] = None
    closed_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CascadeEventBase(BaseModel):
    trace_id: str
    source_agent: str
    event_type: str
    severity: Optional[str] = "info"
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    summary: str
    details: Optional[Dict[str, Any]] = None
    explainability: Optional[Dict[str, Any]] = None


class CascadeEventResponse(CascadeEventBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
