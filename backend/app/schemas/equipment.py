"""
DCBrain Pydantic Schemas — Equipment
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from app.models.equipment import EquipmentStatus, EquipmentCategory


class ZoneBase(BaseModel):
    name: str
    zone_type: str
    floor: Optional[str] = "Ground"
    tier_level: Optional[str] = "III"
    description: Optional[str] = None
    x_position: Optional[float] = 0
    y_position: Optional[float] = 0
    width: Optional[float] = 200
    height: Optional[float] = 150


class ZoneResponse(ZoneBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class VendorBase(BaseModel):
    name: str
    code: str
    category: Optional[str] = None
    country: Optional[str] = "India"
    city: Optional[str] = None
    reliability_score: Optional[float] = 0.85
    on_time_delivery_rate: Optional[float] = 0.80
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    notes: Optional[str] = None


class VendorResponse(VendorBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class EquipmentBase(BaseModel):
    tag: str
    name: str
    category: EquipmentCategory
    make: Optional[str] = None
    model: Optional[str] = None
    status: Optional[EquipmentStatus] = EquipmentStatus.SPECIFIED
    rated_capacity: Optional[str] = None
    voltage_rating: Optional[str] = None
    redundancy: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None
    zone_id: Optional[UUID] = None
    vendor_id: Optional[UUID] = None
    x_position: Optional[float] = 0
    y_position: Optional[float] = 0
    is_critical_path: Optional[bool] = False
    risk_score: Optional[float] = 0.0


class EquipmentResponse(EquipmentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
