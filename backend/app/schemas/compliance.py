"""
DCBrain Pydantic Schemas — Compliance & Quality
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from app.models.compliance import NCRSeverity, NCRStatus


class SpecificationBase(BaseModel):
    doc_code: str
    title: str
    category: Optional[str] = None
    version: Optional[str] = "1.0"
    requirements: Optional[List[Dict[str, Any]]] = None


class SpecificationResponse(SpecificationBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class PurchaseOrderBase(BaseModel):
    po_number: str
    description: Optional[str] = None
    value: Optional[float] = 0.0
    currency: Optional[str] = "INR"
    status: Optional[str] = "issued"
    order_date: Optional[datetime] = None
    expected_delivery: Optional[datetime] = None
    actual_delivery: Optional[datetime] = None
    submittal_status: Optional[str] = "pending"
    submittal_data: Optional[Dict[str, Any]] = None
    equipment_id: UUID
    vendor_id: UUID


class PurchaseOrderResponse(PurchaseOrderBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class NCRBase(BaseModel):
    ncr_number: str
    title: str
    description: str
    severity: NCRSeverity
    status: Optional[NCRStatus] = NCRStatus.OPEN
    spec_requirement: Optional[str] = None
    spec_reference: Optional[str] = None
    actual_value: Optional[str] = None
    deviation_details: Optional[str] = None
    schedule_impact_days: Optional[int] = 0
    cost_impact: Optional[float] = 0.0
    critical_path_affected: Optional[bool] = False
    equipment_id: UUID
    specification_id: Optional[UUID] = None
    purchase_order_id: Optional[UUID] = None
    ai_reasoning: Optional[Dict[str, Any]] = None


class NCRResponse(NCRBase):
    id: UUID
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
