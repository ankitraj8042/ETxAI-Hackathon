"""
DCBrain SQLAlchemy Models — Equipment & Infrastructure
Core entities: Equipment, Vendor, Zone, and their relationships.
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Text, Float, Integer, DateTime, ForeignKey, Enum, JSON, Boolean
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class EquipmentStatus(str, PyEnum):
    """Status of equipment in the project lifecycle."""
    SPECIFIED = "specified"
    ORDERED = "ordered"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    INSTALLED = "installed"
    TESTED = "tested"
    COMMISSIONED = "commissioned"
    NCR_RAISED = "ncr_raised"


class EquipmentCategory(str, PyEnum):
    """Equipment categories for data centre infrastructure."""
    UPS = "ups"
    GENERATOR = "generator"
    SWITCHGEAR = "switchgear"
    PDU = "pdu"
    ATS = "ats"
    TRANSFORMER = "transformer"
    CHILLER = "chiller"
    COOLING_TOWER = "cooling_tower"
    CRAH = "crah"
    CRAC = "crac"
    FIRE_SUPPRESSION = "fire_suppression"
    FIRE_DETECTION = "fire_detection"
    BMS = "bms"
    ACCESS_CONTROL = "access_control"
    CABLING = "cabling"
    RACK = "rack"
    BUSWAY = "busway"
    OTHER = "other"


class Zone(Base):
    """A physical zone/room in the data centre."""
    __tablename__ = "zones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    zone_type = Column(String(50), nullable=False)  # power_room, cooling_plant, it_hall, etc.
    floor = Column(String(20), default="Ground")
    tier_level = Column(String(10), default="III")
    description = Column(Text)
    # Position on the digital twin floor plan
    x_position = Column(Float, default=0)
    y_position = Column(Float, default=0)
    width = Column(Float, default=200)
    height = Column(Float, default=150)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    equipment = relationship("Equipment", back_populates="zone")


class Vendor(Base):
    """Equipment vendor / supplier."""
    __tablename__ = "vendors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    category = Column(String(100))  # electrical, mechanical, fire_safety
    country = Column(String(100), default="India")
    city = Column(String(100))
    reliability_score = Column(Float, default=0.85)  # 0-1 score
    on_time_delivery_rate = Column(Float, default=0.80)
    contact_email = Column(String(200))
    contact_phone = Column(String(50))
    notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    equipment = relationship("Equipment", back_populates="vendor")
    purchase_orders = relationship("PurchaseOrder", back_populates="vendor")


class Equipment(Base):
    """A piece of equipment in the data centre."""
    __tablename__ = "equipment"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tag = Column(String(50), unique=True, nullable=False)  # e.g., UPS-1, GEN-2, CH-1
    name = Column(String(200), nullable=False)
    category = Column(Enum(EquipmentCategory), nullable=False)
    make = Column(String(100))  # Manufacturer
    model = Column(String(100))
    status = Column(Enum(EquipmentStatus), default=EquipmentStatus.SPECIFIED)

    # Specifications
    rated_capacity = Column(String(100))  # e.g., "400 kVA", "2000 kW"
    voltage_rating = Column(String(50))   # e.g., "400V", "11kV"
    redundancy = Column(String(20))       # e.g., "N+1", "2N"
    specifications = Column(JSON, default=dict)  # Flexible spec storage

    # Location
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"))
    zone = relationship("Zone", back_populates="equipment")

    # Vendor
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True)
    vendor = relationship("Vendor", back_populates="equipment")

    # Digital Twin position (within zone)
    x_position = Column(Float, default=0)
    y_position = Column(Float, default=0)

    # Flags
    is_critical_path = Column(Boolean, default=False)
    risk_score = Column(Float, default=0.0)  # 0-1

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    purchase_orders = relationship("PurchaseOrder", back_populates="equipment")
    ncrs = relationship("NCR", back_populates="equipment")
    commissioning_tests = relationship("CommissioningTest", back_populates="equipment")
