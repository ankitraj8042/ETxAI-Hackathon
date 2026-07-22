"""
DCBrain SQLAlchemy Models — Commissioning & Testing
Commissioning tests, procedures, and results.
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Text, Float, Integer, DateTime, ForeignKey, Enum, JSON, Boolean
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class TestResult(str, PyEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PASS = "pass"
    FAIL = "fail"
    CONDITIONAL_PASS = "conditional_pass"


class TestCategory(str, PyEnum):
    ELECTRICAL = "electrical"
    MECHANICAL = "mechanical"
    FIRE_SAFETY = "fire_safety"
    INTEGRATED_SYSTEM = "integrated_system"
    PERFORMANCE = "performance"


class CommissioningTest(Base):
    """A commissioning test procedure and its results."""
    __tablename__ = "commissioning_tests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_code = Column(String(30), unique=True, nullable=False)  # e.g., CX-044
    name = Column(String(300), nullable=False)
    description = Column(Text)
    category = Column(Enum(TestCategory), nullable=False)
    standard_reference = Column(String(100))  # TIA-942, BICSI, Uptime Institute
    tier_requirement = Column(String(10), default="III")  # III or IV

    # Test procedure
    procedure_steps = Column(JSON, default=list)
    # Example: [{"step": 1, "action": "Apply 100% load to UPS", "criteria": "Transfer <10ms"}]
    acceptance_criteria = Column(JSON, default=dict)
    # Example: {"transfer_time_ms": {"max": 10}, "voltage_stability": {"min": 395, "max": 405}}

    # Results
    result = Column(Enum(TestResult), default=TestResult.NOT_STARTED)
    test_date = Column(DateTime, nullable=True)
    measured_values = Column(JSON, default=dict)
    # Example: {"transfer_time_ms": 8, "voltage_stability": 401, "temperature_c": 28.3}

    # AI Analysis
    ai_diagnosis = Column(Text, nullable=True)
    ai_fix_suggestion = Column(Text, nullable=True)
    ai_root_cause = Column(JSON, default=list)
    # Example: ["CRAH-2 airflow reduced", "Valve V17 calibration drift"]

    # Blocking
    is_blocked = Column(Boolean, default=False)
    blocked_by = Column(String(200), nullable=True)  # e.g., "UPS-2 NCR pending"
    blocking_tests = Column(JSON, default=list)  # Tests that this blocks

    # IST Level
    ist_level = Column(Integer, nullable=True)  # 1-5 for Integrated System Testing

    # Links
    equipment_id = Column(UUID(as_uuid=True), ForeignKey("equipment.id"), nullable=True)
    schedule_task_id = Column(UUID(as_uuid=True), ForeignKey("schedule_tasks.id"), nullable=True)

    # Relationships
    from sqlalchemy.orm import relationship
    equipment = relationship("Equipment", back_populates="commissioning_tests")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
