"""
DCBrain Central Agent Orchestrator
Coordinates the agent cascade bus and registers all specialized agent handlers.
"""

from typing import Dict, Any, List
import asyncio
import json

from app.agents.cascade_bus import cascade_bus, CascadeEventPayload


class Orchestrator:
    """Central manager for agent initialization, subscription wiring, and execution."""

    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self._is_initialized = False

    def initialize_agents(self):
        """Lazy load and initialize all specialized agents to avoid circular imports."""
        if self._is_initialized:
            return

        print("🤖 Orchestrator: Initializing AI Agents...")

        from app.agents.schedule_agent import schedule_agent
        from app.agents.supply_chain_agent import supply_chain_agent

        self.agents = {
            "compliance": ComplianceAgentMock(),
            "schedule": schedule_agent,
            "supply_chain": supply_chain_agent,
            "commissioning": CommissioningAgentMock(),
            "knowledge": KnowledgeAgentMock(),
        }

        # ── Cascade Subscription Map ─────────────────────────────────

        # 1. When Compliance raises an NCR:
        cascade_bus.subscribe("ncr_raised", self.agents["schedule"].handle_ncr_raised)
        cascade_bus.subscribe("ncr_raised", self.agents["supply_chain"].handle_ncr_raised)
        cascade_bus.subscribe("ncr_raised", self.agents["knowledge"].handle_ncr_raised)
        cascade_bus.subscribe("ncr_raised", self.agents["commissioning"].handle_ncr_raised)

        # 2. When Schedule predicts a critical path delay:
        cascade_bus.subscribe("delay_predicted", self.agents["supply_chain"].handle_delay_predicted)
        cascade_bus.subscribe("delay_predicted", self.agents["commissioning"].handle_delay_predicted)

        # 3. When Commissioning fails a test:
        cascade_bus.subscribe("test_failed", self.agents["compliance"].handle_test_failed)
        cascade_bus.subscribe("test_failed", self.agents["schedule"].handle_test_failed)
        cascade_bus.subscribe("test_failed", self.agents["knowledge"].handle_test_failed)

        self._is_initialized = True
        print("🤖 Orchestrator: All agent cascade listeners bound successfully.")

    async def handle_user_approval(self, recommendation_id: str, plan_selected: str = "Plan A") -> Dict[str, Any]:
        """
        Closes the loop: User clicks [Approve] -> updates SQL, Graph, Twin,
        and publishes a final event to the Cascade Bus.
        """
        # Load agents if not done
        self.initialize_agents()

        print(f"✔️ Orchestrator: User approved recommendation {recommendation_id} using {plan_selected}")

        # Simulating database/graph changes:
        # For our demo scenario (UPS-2 NCR):
        # 1. Update the NCR status to resolved.
        # 2. Update the Equipment status to 'tested' or 'commissioned'.
        # 3. Release task blocks.
        
        try:
            from app.core.database import async_session_factory
            from app.models import NCR, Equipment, EquipmentStatus, NCRStatus, ScheduleTask, TaskStatus, CommissioningTest, TestResult
            from sqlalchemy import select, update
            
            async with async_session_factory() as session:
                # Find the NCR (could query by id or tag)
                # Let's get the open critical NCR
                ncr_res = await session.execute(select(NCR).where(NCR.status == NCRStatus.OPEN))
                ncr = ncr_res.scalar_one_or_none()

                if ncr:
                    # Resolve NCR
                    ncr.status = NCRStatus.RESOLVED
                    ncr.resolution = f"Approved {plan_selected}: Initiated Eaton autotransformer Tap tapping resolution per RFI-047 precedent."
                    
                    # Update Equipment status
                    eq_res = await session.execute(select(Equipment).where(Equipment.id == ncr.equipment_id))
                    eq = eq_res.scalar_one_or_none()
                    if eq:
                        eq.status = EquipmentStatus.COMMISSIONED
                        eq.risk_score = 0.05
                        eq.is_critical_path = False
                    
                    # Unblock downstream tasks
                    task_res = await session.execute(
                        select(ScheduleTask).where(ScheduleTask.equipment_id == ncr.equipment_id)
                    )
                    tasks = task_res.scalars().all()
                    for t in tasks:
                        t.status = TaskStatus.COMPLETED
                        t.progress_pct = 100.0
                        t.delay_days = 0

                    # Unblock tests
                    test_res = await session.execute(
                        select(CommissioningTest).where(CommissioningTest.equipment_id == ncr.equipment_id)
                    )
                    tests = test_res.scalars().all()
                    for cx in tests:
                        cx.is_blocked = False
                        cx.blocked_by = None
                        cx.result = TestResult.PASS

                    await session.commit()
                    
                    # Publish final cascade resolution event
                    evt = CascadeEventPayload(
                        source_agent="compliance",
                        event_type="ncr_resolved",
                        entity_type="equipment",
                        entity_id=eq.tag if eq else "UPS-2",
                        summary=f"User approved {plan_selected}. Eaton Tap adjustment completed. UPS-2 resolved.",
                        details={
                            "action": "tap_adjustment",
                            "warranty_clause": "4.2.1",
                            "cost": 0,
                            "time_saved_days": 6
                        },
                        severity="info"
                    )
                    await cascade_bus.publish(evt)
                    
                    return {"status": "success", "message": "Recommendation successfully executed and project state updated."}
        except Exception as e:
            print(f"❌ Orchestrator: Failed to execute user approval: {e}")
            return {"status": "error", "message": str(e)}

        return {"status": "error", "message": "No active recommendations to execute."}


# ── Mocks for Phase 1 ─────────────────────────────────────────────────

class AgentMock:
    """Base class for stubbing out agents in Phase 1 scaffolding."""
    def log_trigger(self, agent_name: str, event: CascadeEventPayload):
        print(f"  🧠 [{agent_name.upper()} AGENT] Triggered by '{event.event_type}' for {event.entity_type} {event.entity_id}")


class ComplianceAgentMock(AgentMock):
    async def handle_test_failed(self, event: CascadeEventPayload):
        self.log_trigger("compliance", event)


class ScheduleAgentMock(AgentMock):
    async def handle_ncr_raised(self, event: CascadeEventPayload):
        self.log_trigger("schedule", event)
        # Emit a simulated schedule impact calculation after 1s
        await asyncio.sleep(1)
        impact_evt = CascadeEventPayload(
            source_agent="schedule",
            event_type="delay_predicted",
            entity_type="schedule_task",
            entity_id="TASK-142",
            summary="Schedule Agent: Predicted 10-day delay on TASK-142. Overall completion shifted to Sept 14.",
            details={"critical_path": True, "delay_days": 10},
            trace_id=event.trace_id,
            severity="warning"
        )
        await cascade_bus.publish(impact_evt)

    async def handle_test_failed(self, event: CascadeEventPayload):
        self.log_trigger("schedule", event)


class SupplyChainAgentMock(AgentMock):
    async def handle_ncr_raised(self, event: CascadeEventPayload):
        self.log_trigger("supply_chain", event)

    async def handle_delay_predicted(self, event: CascadeEventPayload):
        self.log_trigger("supply_chain", event)
        # Emit a simulated alternative finder event
        await asyncio.sleep(1)
        alt_evt = CascadeEventPayload(
            source_agent="supply_chain",
            event_type="alternative_found",
            entity_type="vendor",
            entity_id="VEND-VERTIV",
            summary="Supply Chain Agent: Sourced compatible Vertiv replacement. Delivery lead time: 4 days (+12,400 INR).",
            details={"option": "purchase_alternative", "vendor": "Vertiv", "lead_time_days": 4},
            trace_id=event.trace_id,
            severity="info"
        )
        await cascade_bus.publish(alt_evt)


class CommissioningAgentMock(AgentMock):
    async def handle_ncr_raised(self, event: CascadeEventPayload):
        self.log_trigger("commissioning", event)

    async def handle_delay_predicted(self, event: CascadeEventPayload):
        self.log_trigger("commissioning", event)


class KnowledgeAgentMock(AgentMock):
    async def handle_ncr_raised(self, event: CascadeEventPayload):
        self.log_trigger("knowledge", event)
        # Emit a simulated similar RFI lookup precedent
        await asyncio.sleep(1)
        precedent_evt = CascadeEventPayload(
            source_agent="knowledge",
            event_type="precedent_found",
            entity_type="rfi",
            entity_id="RFI-047",
            summary="Knowledge Agent: Identified identical tap tap resolution precedent under RFI-047.",
            details={"precedent": "RFI-047", "resolution": "tap_tap_adjustment", "cost": 0},
            trace_id=event.trace_id,
            severity="info"
        )
        await cascade_bus.publish(precedent_evt)

    async def handle_test_failed(self, event: CascadeEventPayload):
        self.log_trigger("knowledge", event)


# Singleton orchestrator
orchestrator = Orchestrator()
