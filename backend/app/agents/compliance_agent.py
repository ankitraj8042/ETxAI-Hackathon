"""
DCBrain Compliance Agent — Cascade Event Handler
Reacts to cascade events from other agents (e.g., commissioning test failures)
to auto-check for potential spec deviations and draft NCRs.
"""

import asyncio
from datetime import datetime

from app.core.llm import gemini_client
from app.graph.neo4j_client import graph_client
from app.agents.cascade_bus import cascade_bus, CascadeEventPayload
from pydantic import BaseModel, Field


class SpecDeviationCheckSchema(BaseModel):
    is_spec_deviation: bool = Field(description="True if the test failure represents a specification deviation")
    deviation_description: str = Field(description="Description of the specification deviation if applicable")
    recommended_action: str = Field(description="Recommended action — 'raise_ncr', 'monitor', or 'no_action'")
    reasoning: str = Field(description="Technical reasoning for the determination")


SYSTEM_PROMPT = """
You are the DCBrain Compliance Agent. When a commissioning test fails, you must determine whether
the failure represents a specification deviation that warrants a Non-Conformance Report (NCR).

Evaluate:
1. Whether the test failure parameters indicate an equipment specification mismatch.
2. If the root cause suggests the equipment was delivered out-of-spec vs. an installation/calibration issue.
3. Recommend 'raise_ncr' only if the failure is clearly a vendor/equipment specification deviation.
   Recommend 'monitor' if more data is needed. Recommend 'no_action' if it's an installation issue.
"""


class ComplianceAgent:
    """Cascade handler for the Compliance Agent — reacts to test failures and other events."""

    async def handle_test_failed(self, event: CascadeEventPayload):
        """Called when a commissioning test fails. Checks if failure represents a spec deviation."""
        test_code = event.entity_id
        print(f"🔍 ComplianceAgent: Evaluating test {test_code} failure for spec deviation...")

        # Get test context from graph
        test_context = await graph_client.get_test_dependencies(test_code)
        equipment = test_context.get("e", {})

        details = event.details or {}
        measured = details.get("measured_values", {})
        criteria = details.get("acceptance_criteria", {})

        prompt = f"""
        === FAILED TEST ===
        Test Code: {test_code}
        Equipment: {equipment.get('tag', 'Unknown')} ({equipment.get('name', 'Unknown')})
        Category: {equipment.get('category', 'Unknown')}

        === MEASURED VALUES ===
        {measured}

        === ACCEPTANCE CRITERIA ===
        {criteria}

        === DIAGNOSIS FROM COMMISSIONING AGENT ===
        {event.explainability.get('diagnosis', 'N/A')}
        Root Causes: {event.explainability.get('root_causes', [])}

        Determine if this test failure represents a vendor/equipment specification deviation
        or if it is an installation/calibration issue that does not warrant an NCR.
        """

        result: SpecDeviationCheckSchema = await gemini_client.generate_structured(
            prompt=prompt,
            schema=SpecDeviationCheckSchema,
            system_instruction=SYSTEM_PROMPT
        )

        # Publish event based on result
        if result.is_spec_deviation and result.recommended_action == "raise_ncr":
            evt = CascadeEventPayload(
                source_agent="compliance",
                event_type="spec_deviation_detected",
                entity_type="commissioning_test",
                entity_id=test_code,
                summary=f"Compliance Agent: Spec deviation detected in {test_code}. Recommending NCR for {equipment.get('tag', 'Unknown')}.",
                details={
                    "test_code": test_code,
                    "equipment_tag": equipment.get("tag"),
                    "deviation": result.deviation_description,
                    "recommended_action": result.recommended_action,
                },
                explainability={
                    "reasoning": result.reasoning,
                    "deviation_description": result.deviation_description,
                },
                trace_id=event.trace_id,
                severity="warning"
            )
        else:
            evt = CascadeEventPayload(
                source_agent="compliance",
                event_type="spec_check_passed",
                entity_type="commissioning_test",
                entity_id=test_code,
                summary=f"Compliance Agent: Test {test_code} failure is an installation issue, not a spec deviation. Action: {result.recommended_action}.",
                details={
                    "test_code": test_code,
                    "recommended_action": result.recommended_action,
                },
                explainability={
                    "reasoning": result.reasoning,
                },
                trace_id=event.trace_id,
                severity="info"
            )

        await cascade_bus.publish(evt)


# Singleton agent
compliance_agent = ComplianceAgent()
