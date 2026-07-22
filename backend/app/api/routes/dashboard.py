"""
DCBrain API — Dashboard / AI Executive Command Center
Serves KPIs, AI recommendations, cascade events, and project health.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models import (
    Equipment, EquipmentStatus, NCR, NCRStatus, NCRSeverity,
    ScheduleTask, TaskStatus, CommissioningTest, TestResult,
    Shipment, ShipmentStatus, CascadeEvent
)

router = APIRouter()


@router.get("/health-summary")
async def get_project_health(db: AsyncSession = Depends(get_db)):
    """Get overall project health KPIs for the Command Center."""

    # Equipment stats
    total_equipment = await db.scalar(select(func.count(Equipment.id)))
    ncr_equipment = await db.scalar(
        select(func.count(Equipment.id)).where(Equipment.status == EquipmentStatus.NCR_RAISED)
    )

    # NCR stats
    open_ncrs = await db.scalar(
        select(func.count(NCR.id)).where(NCR.status == NCRStatus.OPEN)
    )
    critical_ncrs = await db.scalar(
        select(func.count(NCR.id)).where(
            NCR.status == NCRStatus.OPEN,
            NCR.severity == NCRSeverity.CRITICAL
        )
    )

    # Schedule stats
    total_tasks = await db.scalar(select(func.count(ScheduleTask.id)))
    delayed_tasks = await db.scalar(
        select(func.count(ScheduleTask.id)).where(ScheduleTask.status == TaskStatus.DELAYED)
    )
    completed_tasks = await db.scalar(
        select(func.count(ScheduleTask.id)).where(ScheduleTask.status == TaskStatus.COMPLETED)
    )

    # Commissioning stats
    total_tests = await db.scalar(select(func.count(CommissioningTest.id)))
    passed_tests = await db.scalar(
        select(func.count(CommissioningTest.id)).where(CommissioningTest.result == TestResult.PASS)
    )
    failed_tests = await db.scalar(
        select(func.count(CommissioningTest.id)).where(CommissioningTest.result == TestResult.FAIL)
    )

    # Supply chain stats
    delayed_shipments = await db.scalar(
        select(func.count(Shipment.id)).where(Shipment.status == ShipmentStatus.DELAYED)
    )

    # Calculate health score (weighted)
    schedule_health = ((completed_tasks or 0) / max(total_tasks or 1, 1)) * 100
    compliance_health = max(0, 100 - ((open_ncrs or 0) * 10))
    commissioning_health = ((passed_tests or 0) / max(total_tests or 1, 1)) * 100
    overall_health = int(
        schedule_health * 0.3 + compliance_health * 0.3 + commissioning_health * 0.4
    )

    # Critical risks count
    critical_risks = (critical_ncrs or 0) + (delayed_tasks or 0) + (delayed_shipments or 0)

    return {
        "overall_health": min(overall_health, 100),
        "critical_risks": critical_risks,
        "equipment_delayed": delayed_shipments or 0,
        "compliance_violations": open_ncrs or 0,
        "commissioning_readiness": int(commissioning_health),
        "estimated_completion": "2026-09-14",
        "risk_level": "high" if critical_risks > 3 else "medium" if critical_risks > 1 else "low",
        "stats": {
            "total_equipment": total_equipment or 0,
            "total_tasks": total_tasks or 0,
            "completed_tasks": completed_tasks or 0,
            "delayed_tasks": delayed_tasks or 0,
            "total_tests": total_tests or 0,
            "passed_tests": passed_tests or 0,
            "failed_tests": failed_tests or 0,
            "open_ncrs": open_ncrs or 0,
        }
    }


@router.get("/cascade-events")
async def get_cascade_events(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """Get recent cascade events for the timeline."""
    result = await db.execute(
        select(CascadeEvent)
        .order_by(CascadeEvent.created_at.desc())
        .limit(limit)
    )
    events = result.scalars().all()

    return [
        {
            "id": str(e.id),
            "trace_id": e.trace_id,
            "source_agent": e.source_agent,
            "event_type": e.event_type,
            "severity": e.severity,
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "summary": e.summary,
            "details": e.details,
            "explainability": e.explainability,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]


@router.get("/recommendations")
async def get_ai_recommendations(db: AsyncSession = Depends(get_db)):
    """Get AI-generated recommendations (priority ordered)."""
    # Build recommendations from current state
    recommendations = []

    # Check for open critical NCRs
    result = await db.execute(
        select(NCR).where(NCR.status == NCRStatus.OPEN, NCR.severity == NCRSeverity.CRITICAL)
    )
    critical_ncrs = result.scalars().all()
    for ncr in critical_ncrs:
        recommendations.append({
            "id": str(ncr.id),
            "priority": "critical",
            "title": f"Resolve {ncr.ncr_number}: {ncr.title}",
            "description": ncr.description,
            "potential_savings": f"{ncr.schedule_impact_days} days",
            "source_agent": "compliance",
            "explainability": ncr.ai_reasoning,
            "actions": ["accept", "modify", "dismiss"],
        })

    # Check for delayed tasks on critical path
    result = await db.execute(
        select(ScheduleTask).where(
            ScheduleTask.status == TaskStatus.DELAYED,
            ScheduleTask.is_critical_path == True,
        )
    )
    delayed_critical = result.scalars().all()
    for task in delayed_critical:
        recommendations.append({
            "id": str(task.id),
            "priority": "high",
            "title": f"Critical path delay: {task.name}",
            "description": f"Delayed by {task.delay_days} days. {len(task.recovery_plans)} recovery plans available.",
            "potential_savings": f"{task.delay_days} days",
            "source_agent": "schedule",
            "recovery_plans": task.recovery_plans,
            "actions": ["accept", "modify", "dismiss"],
        })

    # Sort by priority
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    recommendations.sort(key=lambda x: priority_order.get(x["priority"], 4))

    return recommendations


@router.post("/approve/{recommendation_id}")
async def approve_recommendation(recommendation_id: str):
    """Approve a recommendation and execute the resolution cascade."""
    from app.agents.orchestrator import orchestrator
    res = await orchestrator.handle_user_approval(recommendation_id)
    return res


@router.get("/daily-brief")
async def generate_daily_brief(db: AsyncSession = Depends(get_db)):
    """Generate AI Daily Brief — executive summary aggregated from all agents."""
    from app.core.llm import gemini_client

    # Gather current project state
    total_eq = await db.scalar(select(func.count(Equipment.id))) or 0
    ncr_eq = await db.scalar(select(func.count(Equipment.id)).where(Equipment.status == EquipmentStatus.NCR_RAISED)) or 0
    open_ncrs = await db.scalar(select(func.count(NCR.id)).where(NCR.status == NCRStatus.OPEN)) or 0
    critical_ncrs = await db.scalar(select(func.count(NCR.id)).where(NCR.status == NCRStatus.OPEN, NCR.severity == NCRSeverity.CRITICAL)) or 0
    total_tasks = await db.scalar(select(func.count(ScheduleTask.id))) or 0
    delayed_tasks = await db.scalar(select(func.count(ScheduleTask.id)).where(ScheduleTask.status == TaskStatus.DELAYED)) or 0
    completed_tasks = await db.scalar(select(func.count(ScheduleTask.id)).where(ScheduleTask.status == TaskStatus.COMPLETED)) or 0
    total_tests = await db.scalar(select(func.count(CommissioningTest.id))) or 0
    passed_tests = await db.scalar(select(func.count(CommissioningTest.id)).where(CommissioningTest.result == TestResult.PASS)) or 0
    failed_tests = await db.scalar(select(func.count(CommissioningTest.id)).where(CommissioningTest.result == TestResult.FAIL)) or 0

    # Recent cascade events
    events_res = await db.execute(select(CascadeEvent).order_by(CascadeEvent.created_at.desc()).limit(10))
    recent_events = events_res.scalars().all()
    event_summaries = [f"- [{e.source_agent.upper()}] {e.summary}" for e in recent_events]

    prompt = f"""Generate an executive daily brief for the DC-Alpha Data Centre EPC Project.

=== PROJECT STATUS (as of today) ===
Equipment: {total_eq} total, {ncr_eq} with active NCRs
NCRs: {open_ncrs} open ({critical_ncrs} critical)
Schedule: {total_tasks} tasks total, {completed_tasks} completed, {delayed_tasks} delayed
Commissioning: {total_tests} tests total, {passed_tests} passed, {failed_tests} failed

=== RECENT AI AGENT ACTIVITY ===
{chr(10).join(event_summaries) if event_summaries else "No recent events."}

Generate a brief with these sections:
1. **Executive Summary** (2-3 sentences)
2. **Critical Risks** (bullet list)
3. **Progress Update** (equipment, schedule, commissioning)
4. **AI Recommendations** (top 3 actions)
5. **Metrics** (completion %, risk level, estimated completion)

Use professional tone. Be specific with numbers."""

    brief_text = await gemini_client.generate_response(
        prompt=prompt,
        system_instruction="You are the DCBrain AI Daily Brief generator. Produce concise, actionable executive summaries for data centre construction project managers."
    )

    schedule_pct = int((completed_tasks / max(total_tasks, 1)) * 100)
    cx_pct = int((passed_tests / max(total_tests, 1)) * 100)

    return {
        "brief": brief_text,
        "generated_at": __import__("datetime").datetime.utcnow().isoformat(),
        "metrics": {
            "schedule_completion": schedule_pct,
            "commissioning_readiness": cx_pct,
            "open_ncrs": open_ncrs,
            "critical_risks": critical_ncrs + delayed_tasks,
            "total_equipment": total_eq,
        }
    }


# ── Time Machine Snapshots ────────────────────────────────────────────

TIME_MACHINE_SNAPSHOTS = {
    1: {
        "week": 1, "label": "Week 1 — Design & Procurement",
        "overall_health": 92, "critical_risks": 0, "equipment_delayed": 0,
        "compliance_violations": 0, "commissioning_readiness": 0,
        "estimated_completion": "2026-08-28", "risk_level": "low",
        "stats": {
            "total_equipment": 12, "total_tasks": 24, "completed_tasks": 4,
            "delayed_tasks": 0, "total_tests": 16, "passed_tests": 0,
            "failed_tests": 0, "open_ncrs": 0,
        },
        "narrative": "Project initiated. All 12 major equipment items specified. Procurement underway with 4 POs issued. No risks identified.",
        "equipment_states": {
            "UPS-1": "ordered", "UPS-2": "ordered", "GEN-1": "specified", "GEN-2": "specified",
            "SWG-1": "specified", "SWG-2": "specified", "CT-1": "specified", "CRAH-2": "specified",
        }
    },
    2: {
        "week": 2, "label": "Week 2 — Delivery & Installation",
        "overall_health": 78, "critical_risks": 1, "equipment_delayed": 1,
        "compliance_violations": 0, "commissioning_readiness": 12,
        "estimated_completion": "2026-09-04", "risk_level": "medium",
        "stats": {
            "total_equipment": 12, "total_tasks": 24, "completed_tasks": 10,
            "delayed_tasks": 1, "total_tests": 16, "passed_tests": 2,
            "failed_tests": 0, "open_ncrs": 0,
        },
        "narrative": "Major equipment arriving. UPS-1 installed and tested. GEN-1 delayed by 3 days due to port congestion. First commissioning tests underway.",
        "equipment_states": {
            "UPS-1": "installed", "UPS-2": "in_transit", "GEN-1": "in_transit", "GEN-2": "delivered",
            "SWG-1": "installed", "SWG-2": "delivered", "CT-1": "delivered", "CRAH-2": "ordered",
        }
    },
    3: {
        "week": 3, "label": "Week 3 — Testing & NCR Discovery",
        "overall_health": 58, "critical_risks": 3, "equipment_delayed": 1,
        "compliance_violations": 1, "commissioning_readiness": 31,
        "estimated_completion": "2026-09-14", "risk_level": "high",
        "stats": {
            "total_equipment": 12, "total_tasks": 24, "completed_tasks": 14,
            "delayed_tasks": 3, "total_tests": 16, "passed_tests": 5,
            "failed_tests": 1, "open_ncrs": 1,
        },
        "narrative": "CRITICAL: UPS-2 vendor submittal reveals voltage mismatch (380V vs 400V spec). NCR-023 raised. Schedule Agent predicts 10-day critical path delay. CRAH-2 airflow test failed.",
        "equipment_states": {
            "UPS-1": "commissioned", "UPS-2": "ncr_raised", "GEN-1": "installed", "GEN-2": "installed",
            "SWG-1": "tested", "SWG-2": "installed", "CT-1": "installed", "CRAH-2": "ncr_raised",
        }
    },
    4: {
        "week": 4, "label": "Week 4 — Current State",
        "overall_health": 72, "critical_risks": 2, "equipment_delayed": 0,
        "compliance_violations": 1, "commissioning_readiness": 44,
        "estimated_completion": "2026-09-14", "risk_level": "high",
        "stats": {
            "total_equipment": 12, "total_tasks": 24, "completed_tasks": 16,
            "delayed_tasks": 2, "total_tests": 16, "passed_tests": 7,
            "failed_tests": 1, "open_ncrs": 1,
        },
        "narrative": "AI agents have identified recovery plans for UPS-2 NCR. Supply Chain Agent sourced Vertiv alternative. Awaiting project manager approval to resolve. 7/16 commissioning tests passed.",
        "equipment_states": {
            "UPS-1": "commissioned", "UPS-2": "ncr_raised", "GEN-1": "tested", "GEN-2": "tested",
            "SWG-1": "commissioned", "SWG-2": "tested", "CT-1": "tested", "CRAH-2": "installed",
        }
    },
}


@router.get("/time-machine/{week}")
async def get_time_machine_snapshot(week: int):
    """Get a pre-computed weekly snapshot for the Time Machine slider."""
    if week not in TIME_MACHINE_SNAPSHOTS:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Week {week} snapshot not found. Valid: 1-4")
    return TIME_MACHINE_SNAPSHOTS[week]

