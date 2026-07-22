"""
DCBrain Schedule Agent
Handles project schedule tracking, critical path delay analysis, and recovery plan generation.
"""

from typing import Dict, Any, List
import asyncio
import json
from datetime import datetime

from app.core.llm import gemini_client
from app.graph.neo4j_client import graph_client
from app.agents.cascade_bus import cascade_bus, CascadeEventPayload
from pydantic import BaseModel, Field


class RecoveryPlanSchema(BaseModel):
    plan_name: str = Field(description="Short identifier, e.g., 'Plan A: Warranty Swap'")
    description: str = Field(description="Details of the recovery actions required")
    time_saved_days: int = Field(description="Days saved from original delayed timeline")
    cost_impact_inr: float = Field(description="Cost implication in Indian Rupees (INR), negative if savings")
    operational_risk: str = Field(description="Operational or uptime risk associated with this option")


class ScheduleAnalysisSchema(BaseModel):
    delay_predicted_days: int = Field(description="Predicted delay on critical path task in days")
    critical_path_affected: bool = Field(description="True if the affected task lies on the critical path")
    analysis_narrative: str = Field(description="Operational impact analysis detailing downstream task blockage")
    recovery_plans: List[RecoveryPlanSchema] = Field(description="Exactly 3 distinct mitigation recovery plans")


SYSTEM_PROMPT = """
You are the DCBrain Schedule Agent. You analyze construction timeline delays and formulate mitigation recovery plans.
You will be provided with details of a raised NCR, the affected equipment, and downstream schedule dependencies.
Provide:
1. The estimated task delay (in days).
2. A detailed narrative of what downstream tests and tasks are blocked.
3. Exactly three distinct recovery plans:
   - Plan A: Call on manufacturer warranties, contract clauses, or direct swaps.
   - Plan B: Alternate procurement options (local suppliers, different models).
   - Plan C: Work sequence re-routing (doing other work first, delayed testing).
"""


class ScheduleAgent:
    """Agent analyzing schedule impacts and generating recovery paths."""

    async def handle_ncr_raised(self, event: CascadeEventPayload):
        """Called when an NCR is raised. Performs path delay analysis and publishes result."""
        ncr_number = event.entity_id
        print(f"📊 ScheduleAgent: Assessing impact for raised NCR {ncr_number}...")

        # 1. Fetch NCR impact path from Knowledge Graph
        ncr_impact = await graph_client.get_ncr_impact(ncr_number)
        
        ncr_data = ncr_impact.get("ncr", {})
        eq_data = ncr_impact.get("e", {})
        affected_tasks = ncr_impact.get("affected_tasks", [])
        downstream_tasks = ncr_impact.get("downstream_tasks", [])
        blocked_tests = ncr_impact.get("blocked_tests", [])

        # Format prompt details
        prompt = f"""
        === NCR DETAILS ===
        NCR Code: {ncr_number}
        Deviation: {ncr_data.get('deviation_details')}
        Equipment: {eq_data.get('tag')} ({eq_data.get('name')})

        === DIRECT AFFECTED TASK ===
        {json.dumps(affected_tasks)}

        === DOWNSTREAM BLOCKED TASKS & TESTS ===
        Tasks: {json.dumps(downstream_tasks)}
        Tests: {json.dumps(blocked_tests)}
        """

        # 2. Invoke Gemini for schedule reasoning
        result: ScheduleAnalysisSchema = await gemini_client.generate_structured(
            prompt=prompt,
            schema=ScheduleAnalysisSchema,
            system_instruction=SYSTEM_PROMPT
        )

        # 3. Update SQL Database task status to 'blocked'
        # We perform the state update to ensure database consistency
        try:
            from app.core.database import async_session_factory
            from app.models import ScheduleTask, TaskStatus
            from sqlalchemy import select, update
            
            async with async_session_factory() as session:
                for task in affected_tasks:
                    task_id = task.get("id")
                    if task_id:
                        # Update task in DB
                        db_res = await session.execute(
                            select(ScheduleTask).where(ScheduleTask.id == task_id)
                        )
                        db_task = db_res.scalar_one_or_none()
                        if db_task:
                            db_task.status = TaskStatus.DELAYED
                            db_task.delay_days = result.delay_predicted_days
                            db_task.risk_score = 0.80
                            db_task.recovery_plans = [p.model_dump() for p in result.recovery_plans]
                await session.commit()
        except Exception as e:
            print(f"⚠️ ScheduleAgent: Failed to update task database state: {e}")

        # 4. Publish Event to Cascade Bus
        delay_evt = CascadeEventPayload(
            source_agent="schedule",
            event_type="delay_predicted",
            entity_type="schedule_task",
            entity_id=affected_tasks[0].get("task_code") if affected_tasks else "TASK-142",
            summary=f"Schedule Agent: Predicted {result.delay_predicted_days}-day delay on critical path task Install UPS-2.",
            details={
                "ncr_number": ncr_number,
                "delay_days": result.delay_predicted_days,
                "downstream_blocked_tasks": len(downstream_tasks),
                "downstream_blocked_tests": len(blocked_tests),
                "recovery_plans": [p.model_dump() for p in result.recovery_plans]
            },
            explainability={
                "impact_analysis": result.analysis_narrative,
                "recovery_plans": [p.model_dump() for p in result.recovery_plans]
            },
            trace_id=event.trace_id,
            severity="warning" if result.delay_predicted_days < 10 else "critical"
        )
        await cascade_bus.publish(delay_evt)

    async def handle_test_failed(self, event: CascadeEventPayload):
        """Called when a commissioning test fails."""
        test_code = event.entity_id
        print(f"📊 ScheduleAgent: Test {test_code} failure reported. Adjusting downstream commissioning tasks...")
        # Simulates sequence routing
        await asyncio.sleep(0.5)
        
        evt = CascadeEventPayload(
            source_agent="schedule",
            event_type="cx_sequence_adjusted",
            entity_type="commissioning_test",
            entity_id=test_code,
            summary=f"Schedule Agent: Flagged sequence block. Downstream IST-L3-Cooling shifted by 3 days.",
            details={"test_code": test_code, "sequence_delay_days": 3},
            trace_id=event.trace_id,
            severity="warning"
        )
        await cascade_bus.publish(evt)


# Singleton agent
schedule_agent = ScheduleAgent()
