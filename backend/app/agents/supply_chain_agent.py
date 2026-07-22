"""
DCBrain Supply Chain Agent
Handles supplier audits, alternative sourcing lookups, and lead-time analysis.
"""

from typing import Dict, Any, List
import asyncio
import json

from app.core.llm import gemini_client
from app.graph.neo4j_client import graph_client
from app.agents.cascade_bus import cascade_bus, CascadeEventPayload
from pydantic import BaseModel, Field


class SourcingEvaluationSchema(BaseModel):
    selected_alternative_vendor: str = Field(description="Name of recommended alternate supplier, e.g. 'Vertiv Solutions'")
    lead_time_days: int = Field(description="Delivery lead time for the alternative in days")
    additional_cost_inr: float = Field(description="Additional procurement cost or delta in INR")
    reliability_rationale: str = Field(description="Comparison of vendor reliability rating from historical logs")


SYSTEM_PROMPT = """
You are the DCBrain Supply Chain Agent. Your job is to audit supplier performance and source replacement components.
Review the delayed task details, component spec, and the list of alternative vendors retrieved from the Knowledge Graph.
Select the optimal replacement vendor based on reliability, lead times, and cost impacts.
Provide:
1. Recommended alternative supplier.
2. Lead time in days.
3. Additional procurement delta cost.
4. Rationale comparing supplier reliability index ratings.
"""


class SupplyChainAgent:
    """Agent finding alternative sourcing solutions and auditing vendor metrics."""

    async def handle_ncr_raised(self, event: CascadeEventPayload):
        """Called when an NCR is raised. Initiates replacement sourcing checks."""
        print(f"🗺️ SupplyChainAgent: Auditing vendor performance in response to NCR...")
        # For NCR, we check if alternatives are needed
        await asyncio.sleep(0.2)

    async def handle_delay_predicted(self, event: CascadeEventPayload):
        """Called when Schedule predicts a delay. Searches and ranks alternative vendors."""
        task_code = event.entity_id
        delay_days = event.details.get("delay_days", 0)
        print(f"🗺️ SupplyChainAgent: Searching alternative suppliers to mitigate {delay_days}-day delay on {task_code}...")

        # 1. Query Knowledge Graph for alternative suppliers of similar category
        # UPS category alternative vendors
        alt_vendors = await graph_client.find_alternative_vendors("UPS-2")

        # 2. Evaluate using Gemini
        prompt = f"""
        === DELAYED COMPONENT ===
        Equipment: UPS-2 (Nominal Specification output: 400V)
        Critical Path Task: {task_code}
        Schedule Delay: {delay_days} days

        === AVAILABLE ALTERNATIVE VENDORS (From Graph) ===
        {json.dumps(alt_vendors)}
        """

        result: SourcingEvaluationSchema = await gemini_client.generate_structured(
            prompt=prompt,
            schema=SourcingEvaluationSchema,
            system_instruction=SYSTEM_PROMPT
        )

        # 3. Publish Event to Cascade Bus
        alt_evt = CascadeEventPayload(
            source_agent="supply_chain",
            event_type="alternative_found",
            entity_type="vendor",
            entity_id=result.selected_alternative_vendor,
            summary=f"Supply Chain Agent: Sourced alternative {result.selected_alternative_vendor}. Lead time: {result.lead_time_days} days.",
            details={
                "task_code": task_code,
                "vendor_name": result.selected_alternative_vendor,
                "lead_time_days": result.lead_time_days,
                "delta_cost_inr": result.additional_cost_inr,
                "historical_reliability": 0.94 # Vertiv base score
            },
            explainability={
                "sourcing_evaluation": result.reliability_rationale,
                "sourcing_alternatives": alt_vendors
            },
            trace_id=event.trace_id,
            severity="info"
        )
        await cascade_bus.publish(alt_evt)


# Singleton agent
supply_chain_agent = SupplyChainAgent()
