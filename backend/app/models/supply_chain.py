"""
DCBrain SQLAlchemy Models — Supply Chain
Shipments and supplier tracking.
"""

import uuid
from datetime import datetime, date
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Text, Float, Integer, Date, DateTime, ForeignKey, Enum, JSON, Boolean
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class ShipmentStatus(str, PyEnum):
    AT_FACTORY = "at_factory"
    IN_TRANSIT = "in_transit"
    AT_PORT = "at_port"
    CUSTOMS = "customs"
    INLAND_TRANSIT = "inland_transit"
    DELIVERED = "delivered"
    DELAYED = "delayed"


class Shipment(Base):
    """Tracks equipment shipment from vendor to site."""
    __tablename__ = "shipments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tracking_id = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    status = Column(Enum(ShipmentStatus), default=ShipmentStatus.AT_FACTORY)

    # Locations
    origin_city = Column(String(100))
    origin_country = Column(String(100))
    current_location = Column(String(200))
    destination = Column(String(200), default="Project Site, Mumbai")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Dates
    ship_date = Column(Date, nullable=True)
    expected_arrival = Column(Date)
    actual_arrival = Column(Date, nullable=True)
    delay_days = Column(Integer, default=0)

    # Risk
    risk_score = Column(Float, default=0.0)
    risk_factors = Column(JSON, default=list)

    # Links
    equipment_id = Column(UUID(as_uuid=True), ForeignKey("equipment.id"), nullable=True)
    purchase_order_id = Column(UUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=True)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True)

    # AI reasoning
    ai_alternatives = Column(JSON, default=list)
    ai_impact_analysis = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
