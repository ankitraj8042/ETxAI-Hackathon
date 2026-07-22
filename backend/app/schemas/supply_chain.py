"""
DCBrain Pydantic Schemas — Supply Chain
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import date, datetime
from app.models.supply_chain import ShipmentStatus


class ShipmentBase(BaseModel):
    tracking_id: str
    description: Optional[str] = None
    status: Optional[ShipmentStatus] = ShipmentStatus.AT_FACTORY
    origin_city: Optional[str] = None
    origin_country: Optional[str] = None
    current_location: Optional[str] = None
    destination: Optional[str] = "Project Site, Mumbai"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    ship_date: Optional[date] = None
    expected_arrival: date
    actual_arrival: Optional[date] = None
    delay_days: Optional[int] = 0
    risk_score: Optional[float] = 0.0
    risk_factors: Optional[List[str]] = None
    equipment_id: Optional[UUID] = None
    purchase_order_id: Optional[UUID] = None
    vendor_id: Optional[UUID] = None
    ai_alternatives: Optional[List[Dict[str, Any]]] = None
    ai_impact_analysis: Optional[Dict[str, Any]] = None


class ShipmentResponse(ShipmentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
