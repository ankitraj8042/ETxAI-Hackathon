"""
DCBrain Schedule API Routes
Endpoints for project schedule tasks, Gantt chart data, and critical path analysis.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import ScheduleTask, TaskDependency, TaskStatus


router = APIRouter()


@router.get("/tasks")
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status: not_started, in_progress, completed, delayed"),
    phase: Optional[str] = Query(None, description="Filter by phase"),
    is_critical_path: Optional[bool] = Query(None, description="Filter critical path tasks only"),
    db: AsyncSession = Depends(get_db),
):
    """List all schedule tasks with optional filters."""
    query = select(ScheduleTask)

    if status:
        try:
            status_enum = TaskStatus(status)
            query = query.where(ScheduleTask.status == status_enum)
        except ValueError:
            pass

    if phase:
        query = query.where(ScheduleTask.phase == phase)

    if is_critical_path is not None:
        query = query.where(ScheduleTask.is_critical_path == is_critical_path)

    query = query.order_by(ScheduleTask.planned_start)
    result = await db.execute(query)
    tasks = result.scalars().all()

    return [
        {
            "id": str(t.id),
            "task_code": t.task_code,
            "name": t.name,
            "phase": t.phase,
            "category": t.category,
            "planned_start": t.planned_start.isoformat() if t.planned_start else None,
            "planned_end": t.planned_end.isoformat() if t.planned_end else None,
            "status": t.status.value,
            "progress_pct": t.progress_pct,
            "is_critical_path": t.is_critical_path,
            "equipment_id": str(t.equipment_id) if t.equipment_id else None,
            "risk_score": t.risk_score,
            "delay_days": t.delay_days,
            "recovery_plans": t.recovery_plans or [],
        }
        for t in tasks
    ]


@router.get("/tasks/{task_code}")
async def get_task_detail(task_code: str, db: AsyncSession = Depends(get_db)):
    """Get full task detail including dependencies and recovery plans."""
    result = await db.execute(
        select(ScheduleTask).where(ScheduleTask.task_code == task_code)
    )
    task = result.scalar_one_or_none()
    if not task:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Task {task_code} not found")

    # Get predecessors
    pred_result = await db.execute(
        select(TaskDependency).where(TaskDependency.successor_id == task.id)
    )
    predecessors = pred_result.scalars().all()

    pred_codes = []
    for dep in predecessors:
        pred_task_res = await db.execute(
            select(ScheduleTask).where(ScheduleTask.id == dep.predecessor_id)
        )
        pred_task = pred_task_res.scalar_one_or_none()
        if pred_task:
            pred_codes.append(pred_task.task_code)

    # Get successors
    succ_result = await db.execute(
        select(TaskDependency).where(TaskDependency.predecessor_id == task.id)
    )
    successors = succ_result.scalars().all()

    succ_codes = []
    for dep in successors:
        succ_task_res = await db.execute(
            select(ScheduleTask).where(ScheduleTask.id == dep.successor_id)
        )
        succ_task = succ_task_res.scalar_one_or_none()
        if succ_task:
            succ_codes.append(succ_task.task_code)

    return {
        "id": str(task.id),
        "task_code": task.task_code,
        "name": task.name,
        "phase": task.phase,
        "category": task.category,
        "planned_start": task.planned_start.isoformat() if task.planned_start else None,
        "planned_end": task.planned_end.isoformat() if task.planned_end else None,
        "status": task.status.value,
        "progress_pct": task.progress_pct,
        "is_critical_path": task.is_critical_path,
        "risk_score": task.risk_score,
        "delay_days": task.delay_days,
        "recovery_plans": task.recovery_plans or [],
        "predecessors": pred_codes,
        "successors": succ_codes,
    }


@router.get("/gantt")
async def get_gantt_data(db: AsyncSession = Depends(get_db)):
    """Return all tasks formatted for Gantt chart rendering."""
    result = await db.execute(
        select(ScheduleTask).order_by(ScheduleTask.planned_start)
    )
    tasks = result.scalars().all()

    # Build dependency map
    dep_result = await db.execute(select(TaskDependency))
    deps = dep_result.scalars().all()

    # Map task IDs to codes
    id_to_code = {str(t.id): t.task_code for t in tasks}

    gantt_items = []
    for t in tasks:
        # Find predecessors for this task
        task_preds = [
            id_to_code.get(str(d.predecessor_id))
            for d in deps
            if str(d.successor_id) == str(t.id) and str(d.predecessor_id) in id_to_code
        ]

        gantt_items.append({
            "task_code": t.task_code,
            "name": t.name,
            "phase": t.phase,
            "start": t.planned_start.isoformat() if t.planned_start else None,
            "end": t.planned_end.isoformat() if t.planned_end else None,
            "progress": t.progress_pct,
            "status": t.status.value,
            "is_critical_path": t.is_critical_path,
            "dependencies": [p for p in task_preds if p],
        })

    return {"tasks": gantt_items}


@router.get("/critical-path")
async def get_critical_path(db: AsyncSession = Depends(get_db)):
    """Get all tasks on the critical path with their dependency chain."""
    result = await db.execute(
        select(ScheduleTask)
        .where(ScheduleTask.is_critical_path == True)
        .order_by(ScheduleTask.planned_start)
    )
    tasks = result.scalars().all()

    return [
        {
            "task_code": t.task_code,
            "name": t.name,
            "phase": t.phase,
            "planned_start": t.planned_start.isoformat() if t.planned_start else None,
            "planned_end": t.planned_end.isoformat() if t.planned_end else None,
            "status": t.status.value,
            "progress_pct": t.progress_pct,
            "risk_score": t.risk_score,
            "delay_days": t.delay_days,
            "recovery_plans": t.recovery_plans or [],
        }
        for t in tasks
    ]
