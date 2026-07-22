"""
DCBrain SQLAlchemy Models — Schedule & Tasks
Project schedule tasks with dependencies and risk scoring.
"""

import uuid
from datetime import datetime, date
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Text, Float, Integer, Date, DateTime, ForeignKey, Enum, JSON, Boolean
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class TaskStatus(str, PyEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"
    BLOCKED = "blocked"


class ScheduleTask(Base):
    """A task in the project schedule (Gantt chart item)."""
    __tablename__ = "schedule_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_code = Column(String(30), unique=True, nullable=False)  # e.g., TASK-142
    name = Column(String(300), nullable=False)
    description = Column(Text)
    phase = Column(String(100))  # design, procurement, construction, commissioning
    category = Column(String(100))  # electrical, mechanical, civil, it

    # Schedule
    planned_start = Column(Date, nullable=False)
    planned_end = Column(Date, nullable=False)
    actual_start = Column(Date, nullable=True)
    actual_end = Column(Date, nullable=True)
    duration_days = Column(Integer)
    progress_pct = Column(Float, default=0.0)  # 0-100

    status = Column(Enum(TaskStatus), default=TaskStatus.NOT_STARTED)
    is_critical_path = Column(Boolean, default=False)
    is_milestone = Column(Boolean, default=False)

    # Risk
    risk_score = Column(Float, default=0.0)  # 0-1
    risk_factors = Column(JSON, default=list)
    delay_days = Column(Integer, default=0)

    # Equipment dependency
    equipment_id = Column(UUID(as_uuid=True), ForeignKey("equipment.id"), nullable=True)

    # Recovery plans (AI-generated)
    recovery_plans = Column(JSON, default=list)
    # Example: [{"plan": "A", "description": "...", "time_saved": 8, "cost": 5000}]

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TaskDependency(Base):
    """Dependency between two schedule tasks."""
    __tablename__ = "task_dependencies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    predecessor_id = Column(UUID(as_uuid=True), ForeignKey("schedule_tasks.id"), nullable=False)
    successor_id = Column(UUID(as_uuid=True), ForeignKey("schedule_tasks.id"), nullable=False)
    dependency_type = Column(String(10), default="FS")  # FS, FF, SS, SF
    lag_days = Column(Integer, default=0)
