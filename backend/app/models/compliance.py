"""
DCBrain SQLAlchemy Models — Compliance & Quality
Specifications, Purchase Orders, and Non-Conformance Reports.
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


class NCRSeverity(str, PyEnum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class NCRStatus(str, PyEnum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Specification(Base):
    """A project specification document or requirement."""
    __tablename__ = "specifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doc_code = Column(String(50), unique=True, nullable=False)  # e.g., DC-ALPHA-ELEC-SPEC-001
    title = Column(String(300), nullable=False)
    category = Column(String(100))  # electrical, mechanical, fire_safety, etc.
    version = Column(String(20), default="1.0")
    file_path = Column(String(500))
    content_summary = Column(Text)

    # Extracted requirements stored as structured JSON
    requirements = Column(JSON, default=list)
    # Example: [{"id": "4.3.2", "text": "UPS voltage shall be 400V ±5%", "category": "electrical"}]

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    ncrs = relationship("NCR", back_populates="specification")


class PurchaseOrder(Base):
    """A purchase order for equipment procurement."""
    __tablename__ = "purchase_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    po_number = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    value = Column(Float, default=0.0)
    currency = Column(String(10), default="INR")
    status = Column(String(50), default="issued")  # issued, acknowledged, shipped, delivered
    order_date = Column(DateTime)
    expected_delivery = Column(DateTime)
    actual_delivery = Column(DateTime, nullable=True)

    # Submittal data
    submittal_file_path = Column(String(500), nullable=True)
    submittal_status = Column(String(50), default="pending")  # pending, reviewed, approved, rejected
    submittal_data = Column(JSON, default=dict)  # Extracted specs from vendor submittal

    # Links
    equipment_id = Column(UUID(as_uuid=True), ForeignKey("equipment.id"))
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"))

    equipment = relationship("Equipment", back_populates="purchase_orders")
    vendor = relationship("Vendor", back_populates="purchase_orders")

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    ncrs = relationship("NCR", back_populates="purchase_order")


class NCR(Base):
    """Non-Conformance Report — raised when a submittal/PO deviates from spec."""
    __tablename__ = "ncrs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ncr_number = Column(String(20), unique=True, nullable=False)  # e.g., NCR-023
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(Enum(NCRSeverity), nullable=False)
    status = Column(Enum(NCRStatus), default=NCRStatus.OPEN)

    # What was expected vs what was found
    spec_requirement = Column(Text)       # "Voltage shall be 400V ±5%"
    spec_reference = Column(String(100))  # "Section 4.3.2, Page 47"
    actual_value = Column(Text)           # "380V"
    deviation_details = Column(Text)      # "20V below minimum tolerance"

    # Impact
    schedule_impact_days = Column(Integer, default=0)
    cost_impact = Column(Float, default=0.0)
    critical_path_affected = Column(Boolean, default=False)

    # Links
    equipment_id = Column(UUID(as_uuid=True), ForeignKey("equipment.id"))
    specification_id = Column(UUID(as_uuid=True), ForeignKey("specifications.id"), nullable=True)
    purchase_order_id = Column(UUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=True)

    equipment = relationship("Equipment", back_populates="ncrs")
    specification = relationship("Specification", back_populates="ncrs")
    purchase_order = relationship("PurchaseOrder", back_populates="ncrs", foreign_keys=[purchase_order_id])

    # Resolution
    resolution = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    # Explainability
    ai_reasoning = Column(JSON, default=dict)  # Full explainability chain

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
