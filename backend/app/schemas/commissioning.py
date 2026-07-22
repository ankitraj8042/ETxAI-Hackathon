"""
DCBrain Pydantic Schemas — Commissioning & Testing
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from app.models.commissioning import TestResult, TestCategory


class CommissioningTestBase(BaseModel):
    test_code: str
    name: str
    description: Optional[str] = None
    category: TestCategory
    standard_reference: Optional[str] = None
    tier_requirement: Optional[str] = "III"
    procedure_steps: Optional[List[Dict[str, Any]]] = None
    acceptance_criteria: Optional[Dict[str, Any]] = None
    result: Optional[TestResult] = TestResult.NOT_STARTED
    test_date: Optional[datetime] = None
    measured_values: Optional[Dict[str, Any]] = None
    ai_diagnosis: Optional[str] = None
    ai_fix_suggestion: Optional[str] = None
    ai_root_cause: Optional[List[str]] = None
    is_blocked: Optional[bool] = False
    blocked_by: Optional[str] = None
    blocking_tests: Optional[List[str]] = None
    ist_level: Optional[int] = None
    equipment_id: Optional[UUID] = None
    schedule_task_id: Optional[UUID] = None


class CommissioningTestResponse(CommissioningTestBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
