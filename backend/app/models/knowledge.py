"""
DCBrain SQLAlchemy Models — Knowledge & Documents
Project documents, RFIs, and chat history for the Knowledge Agent.
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Text, Float, Integer, DateTime, ForeignKey, Enum, JSON, Boolean
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class RFIStatus(str, PyEnum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    ANSWERED = "answered"
    CLOSED = "closed"


class RFIPriority(str, PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProjectDocument(Base):
    """A project document ingested into the RAG system."""
    __tablename__ = "project_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doc_code = Column(String(50), unique=True, nullable=False)
    title = Column(String(300), nullable=False)
    doc_type = Column(String(50))  # specification, submittal, rfi, meeting_minutes, change_order, contract
    category = Column(String(100))  # electrical, mechanical, etc.
    file_path = Column(String(500))
    file_name = Column(String(200))
    file_size_bytes = Column(Integer, default=0)

    # RAG metadata
    chunk_count = Column(Integer, default=0)
    is_indexed = Column(Boolean, default=False)
    content_summary = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class RFI(Base):
    """Request for Information — technical/contractual query."""
    __tablename__ = "rfis"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rfi_number = Column(String(20), unique=True, nullable=False)  # e.g., RFI-047
    subject = Column(String(300), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    status = Column(Enum(RFIStatus), default=RFIStatus.OPEN)
    priority = Column(Enum(RFIPriority), default=RFIPriority.MEDIUM)

    # Categorization
    category = Column(String(100))  # electrical, mechanical, etc.
    discipline = Column(String(100))

    # Dates
    raised_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=True)
    answered_date = Column(DateTime, nullable=True)
    closed_date = Column(DateTime, nullable=True)

    # Participants
    raised_by = Column(String(200))
    assigned_to = Column(String(200))

    # Links
    equipment_id = Column(UUID(as_uuid=True), ForeignKey("equipment.id"), nullable=True)
    related_doc_id = Column(UUID(as_uuid=True), ForeignKey("project_documents.id"), nullable=True)

    # AI
    similar_rfis = Column(JSON, default=list)  # List of similar RFI numbers found by AI
    ai_suggested_answer = Column(Text, nullable=True)
    resolution_time_hours = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CascadeEvent(Base):
    """An event in the agent cascade — for audit trail and timeline display."""
    __tablename__ = "cascade_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trace_id = Column(String(50), nullable=False)  # Groups events in the same cascade
    source_agent = Column(String(50), nullable=False)  # compliance, schedule, etc.
    event_type = Column(String(100), nullable=False)    # ncr_raised, delay_predicted, etc.
    severity = Column(String(20), default="info")       # info, warning, critical
    entity_type = Column(String(50))                    # equipment, shipment, etc.
    entity_id = Column(String(50))                      # UPS-2, SHIP-007, etc.
    summary = Column(Text, nullable=False)
    details = Column(JSON, default=dict)
    explainability = Column(JSON, default=dict)  # Evidence chain for [Why?]

    created_at = Column(DateTime, default=datetime.utcnow)
