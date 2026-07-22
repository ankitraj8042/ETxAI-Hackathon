"""
DCBrain Commissioning Agent — Cascade Event Handler
Reacts to NCR events by blocking dependent commissioning tests,
and to schedule delays by adjusting test sequence priorities.
"""

import asyncio
from datetime import datetime

from app.core.llm import gemini_client
from app.graph.neo4j_client import graph_client
from app.agents.cascade_bus import cascade_bus, CascadeEventPayload
from pydantic import BaseModel, Field
from typing import List


class TestSequenceAdjustmentSchema(BaseModel):
    affected_tests: List[str] = Field(description="List of test codes that are affected by the delay")
    recommended_sequence: str = Field(description="Recommended test re-sequencing strategy")
    estimated_delay_days: int = Field(description="Estimated additional delay to commissioning timeline in days")
    reasoning: str = Field(description="Technical reasoning for the sequence adjustment")


SYSTEM_PROMPT = """
You are the DCBrain Commissioning Agent. When schedule delays are predicted, you must evaluate
the impact on the commissioning test sequence and recommend adjustments.

Consider:
1. Which commissioning tests depend on the delayed task or equipment.
2. Whether tests can be re-sequenced to continue useful work during the delay.
3. The IST level dependencies (L1 → L2 → L3 → L4 → L5) and which levels are affected.
4. Any tests that can be performed in parallel or brought forward.
"""


class CommissioningAgent:
    """Cascade handler for the Commissioning Agent."""

    async def handle_ncr_raised(self, event: CascadeEventPayload):
        """Called when an NCR is raised. Blocks dependent commissioning tests."""
        ncr_number = event.entity_id
        equipment_tag = event.details.get("equipment_tag", "Unknown")
        print(f"✅ CommissioningAgent: NCR {ncr_number} raised. Blocking tests for {equipment_tag}...")

        # Query graph for tests linked to this equipment
        eq_context = await graph_client.get_equipment_context(equipment_tag)
        tests = eq_context.get("tests", [])

        blocked_count = 0
        blocked_test_codes = []

        # Update test blocking status in the database
        try:
            from app.core.database import async_session_factory
            from app.models import CommissioningTest
            from sqlalchemy import select

            async with async_session_factory() as session:
                for test in tests:
                    test_code = test.get("test_code")
                    if test_code:
                        db_res = await session.execute(
                            select(CommissioningTest).where(CommissioningTest.test_code == test_code)
                        )
                        db_test = db_res.scalar_one_or_none()
                        if db_test and db_test.result.value != "pass":
                            db_test.is_blocked = True
                            db_test.blocked_by = f"{ncr_number} pending resolution"
                            blocked_count += 1
                            blocked_test_codes.append(test_code)
                await session.commit()
        except Exception as e:
            print(f"⚠️ CommissioningAgent: Failed to update test blocking: {e}")

        # Publish cascade event
        evt = CascadeEventPayload(
            source_agent="commissioning",
            event_type="commissioning_blocked",
            entity_type="commissioning_test",
            entity_id=equipment_tag,
            summary=f"Commissioning Agent: Blocked {blocked_count} tests for {equipment_tag} pending {ncr_number} resolution.",
            details={
                "ncr_number": ncr_number,
                "equipment_tag": equipment_tag,
                "blocked_tests": blocked_test_codes,
                "blocked_count": blocked_count,
            },
            explainability={
                "reasoning": f"Tests {', '.join(blocked_test_codes)} depend on {equipment_tag} which has open NCR {ncr_number}. "
                             f"Tests cannot proceed until the equipment specification deviation is resolved.",
                "ist_impact": "IST Level 3+ tests blocked — system-level integration testing paused for this equipment.",
            },
            trace_id=event.trace_id,
            severity="warning"
        )
        await cascade_bus.publish(evt)

    async def handle_delay_predicted(self, event: CascadeEventPayload):
        """Called when Schedule Agent predicts a delay. Adjusts test sequence priorities."""
        task_code = event.entity_id
        delay_days = event.details.get("delay_days", 0)
        print(f"✅ CommissioningAgent: {delay_days}-day delay on {task_code}. Evaluating test sequence...")

        # Get recovery plans context from the event
        recovery_plans = event.details.get("recovery_plans", [])

        prompt = f"""
        === SCHEDULE DELAY EVENT ===
        Task: {task_code}
        Delay: {delay_days} days
        Downstream blocked tasks: {event.details.get('downstream_blocked_tasks', 0)}
        Downstream blocked tests: {event.details.get('downstream_blocked_tests', 0)}

        === AVAILABLE RECOVERY PLANS ===
        {recovery_plans}

        Evaluate the impact on the commissioning test sequence. Which tests are affected?
        Can any IST Level 1-2 tests be brought forward to maximize productive time?
        Recommend a test re-sequencing strategy.
        """

        result: TestSequenceAdjustmentSchema = await gemini_client.generate_structured(
            prompt=prompt,
            schema=TestSequenceAdjustmentSchema,
            system_instruction=SYSTEM_PROMPT
        )

        evt = CascadeEventPayload(
            source_agent="commissioning",
            event_type="cx_sequence_adjusted",
            entity_type="commissioning_test",
            entity_id=task_code,
            summary=f"Commissioning Agent: Adjusted test sequence due to {delay_days}-day delay. {len(result.affected_tests)} tests re-prioritized.",
            details={
                "task_code": task_code,
                "delay_days": delay_days,
                "affected_tests": result.affected_tests,
                "recommended_sequence": result.recommended_sequence,
                "additional_cx_delay": result.estimated_delay_days,
            },
            explainability={
                "reasoning": result.reasoning,
                "sequence_strategy": result.recommended_sequence,
            },
            trace_id=event.trace_id,
            severity="warning"
        )
        await cascade_bus.publish(evt)


# Singleton agent
commissioning_agent = CommissioningAgent()
