"""
DCBrain Pydantic Schemas — Schedule & Tasks
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import date, datetime
from app.models.schedule import TaskStatus


class ScheduleTaskBase(BaseModel):
    task_code: str
    name: str
    description: Optional[str] = None
    phase: Optional[str] = None
    category: Optional[str] = None
    planned_start: date
    planned_end: date
    actual_start: Optional[date] = None
    actual_end: Optional[date] = None
    duration_days: Optional[int] = None
    progress_pct: Optional[float] = 0.0
    status: Optional[TaskStatus] = TaskStatus.NOT_STARTED
    is_critical_path: Optional[bool] = False
    is_milestone: Optional[bool] = False
    risk_score: Optional[float] = 0.0
    risk_factors: Optional[List[str]] = None
    delay_days: Optional[int] = 0
    equipment_id: Optional[UUID] = None
    recovery_plans: Optional[List[Dict[str, Any]]] = None


class ScheduleTaskResponse(ScheduleTaskBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskDependencyBase(BaseModel):
    predecessor_id: UUID
    successor_id: UUID
    dependency_type: Optional[str] = "FS"
    lag_days: Optional[int] = 0


class TaskDependencyResponse(TaskDependencyBase):
    id: UUID

    class Config:
        from_attributes = True
