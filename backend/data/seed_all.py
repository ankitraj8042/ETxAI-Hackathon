"""
DCBrain Master Seeder Script
Coordinates seeding of the SQL Database, Neo4j Knowledge Graph, and ChromaDB Vector Store.
Supports SQLite database and in-memory graph fallback for zero-config startup.
"""

import os
import sys
import asyncio
import json
import uuid
from datetime import datetime
from typing import Optional

# Adjust path to import backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_factory, init_db, engine
from app.core.dependencies import get_neo4j_driver, get_chroma_client
from app.graph.seed import get_in_memory_data, write_local_graph_json, seed_neo4j

# Import models
from app.models import (
    Zone, Vendor, Equipment, Specification, PurchaseOrder,
    NCR, ScheduleTask, TaskDependency, Shipment, CommissioningTest,
    RFI, ProjectDocument, CascadeEvent
)


def to_uuid(val: str) -> Optional[uuid.UUID]:
    """Converts a string ID to a deterministic UUID object using UUIDv5."""
    if not val:
        return None
    try:
        # Check if already a valid UUID string
        return uuid.UUID(val)
    except ValueError:
        # Generate stable UUID from string name
        return uuid.uuid5(uuid.NAMESPACE_DNS, val)


async def seed_relational_db(db: AsyncSession):
    """Seed the relational database with SQLAlchemy models."""
    print("🛢️ Seeding SQL Database...")
    data = get_in_memory_data()

    # Clear existing tables in sequence to avoid foreign key violations
    tables_to_clear = [
        CascadeEvent, TaskDependency, RFI, Shipment, CommissioningTest, ScheduleTask,
        NCR, PurchaseOrder, Specification, Equipment, Vendor, Zone, ProjectDocument
    ]
    for table in tables_to_clear:
        await db.execute(table.__table__.delete())
    await db.commit()
    print("  Cleared old SQL tables")

    # 1. Zones
    for z in data["zones"]:
        inst = Zone(
            id=to_uuid(z["id"]),
            name=z["name"],
            zone_type=z["zone_type"],
            floor=z["floor"],
            tier_level=z["tier_level"],
            description=z["description"],
            x_position=z["x_position"],
            y_position=z["y_position"],
            width=z["width"],
            height=z["height"]
        )
        db.add(inst)
    
    # 2. Vendors
    for v in data["vendors"]:
        inst = Vendor(
            id=to_uuid(v["id"]),
            name=v["name"],
            code=v["code"],
            category=v["category"],
            reliability_score=v["reliability_score"],
            on_time_delivery_rate=v["on_time_delivery_rate"],
            contact_email=v["contact_email"]
        )
        db.add(inst)

    await db.flush()

    # 3. Equipment
    for eq in data["equipment"]:
        inst = Equipment(
            id=to_uuid(eq["id"]),
            tag=eq["tag"],
            name=eq["name"],
            category=eq["category"],
            make=eq["make"],
            model=eq["model"],
            status=eq["status"],
            rated_capacity=eq["rated_capacity"],
            voltage_rating=eq["voltage_rating"],
            redundancy=eq["redundancy"],
            zone_id=to_uuid(eq["zone_id"]),
            vendor_id=to_uuid(eq["vendor_id"]),
            x_position=eq["x_position"],
            y_position=eq["y_position"],
            is_critical_path=eq["is_critical_path"],
            risk_score=eq["risk_score"]
        )
        db.add(inst)

    # 4. Specifications
    for s in data["specifications"]:
        inst = Specification(
            id=to_uuid(s["id"]),
            doc_code=s["doc_code"],
            title=s["title"],
            category=s["category"],
            version=s["version"],
            requirements=s["requirements"]
        )
        db.add(inst)

    await db.flush()

    # 5. Purchase Orders
    for po in data["purchase_orders"]:
        inst = PurchaseOrder(
            id=to_uuid(po["id"]),
            po_number=po["po_number"],
            description=po["description"],
            value=po["value"],
            status=po["status"],
            order_date=datetime.strptime(po["order_date"], "%Y-%m-%d"),
            expected_delivery=datetime.strptime(po["expected_delivery"], "%Y-%m-%d"),
            submittal_status=po["submittal_status"],
            submittal_data=po["submittal_data"],
            equipment_id=to_uuid(po["equipment_id"]),
            vendor_id=to_uuid(po["vendor_id"])
        )
        db.add(inst)

    await db.flush()

    # 6. NCRs
    for n in data["ncrs"]:
        inst = NCR(
            id=to_uuid(n["id"]),
            ncr_number=n["ncr_number"],
            title=n["title"],
            description=n["description"],
            severity=n["severity"],
            status=n["status"],
            spec_requirement=n["spec_requirement"],
            spec_reference=n["spec_reference"],
            actual_value=n["actual_value"],
            deviation_details=n["deviation_details"],
            schedule_impact_days=n["schedule_impact_days"],
            cost_impact=n["cost_impact"],
            critical_path_affected=n["critical_path_affected"],
            equipment_id=to_uuid(n["equipment_id"]),
            specification_id=to_uuid(n["specification_id"]),
            purchase_order_id=to_uuid(n["purchase_order_id"]),
            ai_reasoning=n["ai_reasoning"]
        )
        db.add(inst)

    # 7. Schedule Tasks
    for t in data["tasks"]:
        inst = ScheduleTask(
            id=to_uuid(t["id"]),
            task_code=t["task_code"],
            name=t["name"],
            phase=t["phase"],
            category=t["category"],
            planned_start=datetime.strptime(t["planned_start"], "%Y-%m-%d").date(),
            planned_end=datetime.strptime(t["planned_end"], "%Y-%m-%d").date(),
            status=t["status"],
            progress_pct=t["progress_pct"],
            is_critical_path=t["is_critical_path"],
            equipment_id=to_uuid(t.get("equipment_id")),
            risk_score=t.get("risk_score", 0.0),
            delay_days=t.get("delay_days", 0),
            recovery_plans=t.get("recovery_plans", [])
        )
        db.add(inst)

    await db.flush()

    # Task dependencies
    for dep in data["dependencies"]:
        inst = TaskDependency(
            predecessor_id=to_uuid(dep["predecessor_id"]),
            successor_id=to_uuid(dep["successor_id"])
        )
        db.add(inst)

    # 8. Shipments
    for s in data["shipments"]:
        inst = Shipment(
            id=to_uuid(s["id"]),
            tracking_id=s["tracking_id"],
            description=s["description"],
            status=s["status"],
            origin_city=s["origin_city"],
            origin_country=s["origin_country"],
            current_location=s["current_location"],
            latitude=s["latitude"],
            longitude=s["longitude"],
            expected_arrival=datetime.strptime(s["expected_arrival"], "%Y-%m-%d").date(),
            delay_days=s["delay_days"],
            risk_score=s["risk_score"],
            risk_factors=s.get("risk_factors", []),
            equipment_id=to_uuid(s.get("equipment_id")),
            purchase_order_id=to_uuid(s.get("purchase_order_id")),
            vendor_id=to_uuid(s.get("vendor_id")),
            ai_alternatives=s.get("ai_alternatives", []),
            ai_impact_analysis=s.get("ai_impact_analysis", {})
        )
        db.add(inst)

    # 9. Commissioning Tests
    for cx in data["tests"]:
        inst = CommissioningTest(
            id=to_uuid(cx["id"]),
            test_code=cx["test_code"],
            name=cx["name"],
            category=cx["category"],
            standard_reference=cx.get("standard_reference"),
            tier_requirement=cx.get("tier_requirement", "III"),
            result=cx.get("result", "not_started"),
            is_blocked=cx.get("is_blocked", False),
            blocked_by=cx.get("blocked_by"),
            blocking_tests=cx.get("blocking_tests", []),
            ist_level=cx.get("ist_level"),
            equipment_id=to_uuid(cx.get("equipment_id")),
            schedule_task_id=to_uuid(cx.get("schedule_task_id")),
            procedure_steps=cx.get("procedure_steps", []),
            acceptance_criteria=cx.get("acceptance_criteria", {}),
            measured_values=cx.get("measured_values", {}),
            ai_diagnosis=cx.get("ai_diagnosis"),
            ai_fix_suggestion=cx.get("ai_fix_suggestion"),
            ai_root_cause=cx.get("ai_root_cause", [])
        )
        db.add(inst)

    # 10. RFIs
    for r in data["rfis"]:
        inst = RFI(
            id=to_uuid(r["id"]),
            rfi_number=r["rfi_number"],
            subject=r["subject"],
            question=r["question"],
            answer=r.get("answer"),
            status=r.get("status", "open"),
            priority=r.get("priority", "medium"),
            category=r.get("category"),
            discipline=r.get("discipline"),
            raised_by=r.get("raised_by"),
            assigned_to=r.get("assigned_to"),
            resolution_time_hours=r.get("resolution_time_hours"),
            similar_rfis=r.get("similar_rfis", []),
            equipment_id=to_uuid(r.get("equipment_id"))
        )
        db.add(inst)

    # 11. Documents
    for d in data["documents"]:
        inst = ProjectDocument(
            id=to_uuid(d["id"]),
            doc_code=d["doc_code"],
            title=d["title"],
            doc_type=d["doc_type"],
            category=d["category"],
            file_name=d["file_name"],
            chunk_count=d["chunk_count"],
            is_indexed=d["is_indexed"],
            content_summary=d["content_summary"]
        )
        db.add(inst)

    # 12. Cascade Events (Demo initial events)
    demo_cascade_events = [
        {
            "id": "evt-001",
            "trace_id": "trace-demo-1001",
            "source_agent": "compliance",
            "event_type": "ncr_raised",
            "severity": "critical",
            "entity_type": "ncr",
            "entity_id": "NCR-023",
            "summary": "Compliance Agent: Raised critical NCR-023 against UPS-2 due to voltage mismatch (380V submittal vs 400V spec).",
            "details": {
                "ncr_number": "NCR-023",
                "equipment_tag": "UPS-2",
                "specification": "SPEC-ELEC-001",
                "actual_voltage": "380V",
                "expected_voltage": "400V ±5%"
            },
            "explainability": {
                "reasoning": "Vendor submittal specifies 380V output. Spec requires 400V 50Hz N+1 topology for Tier III rating.",
                "evidence": [
                    {"source": "DC-ALPHA-SPEC-ELEC", "finding": "Section 4.3.2 requires 400V AC output"},
                    {"source": "PO-UPS-2026-002", "finding": "Eaton submittal states 380V output"}
                ]
            }
        },
        {
            "id": "evt-002",
            "trace_id": "trace-demo-1001",
            "source_agent": "schedule",
            "event_type": "delay_predicted",
            "severity": "warning",
            "entity_type": "schedule_task",
            "entity_id": "TASK-142",
            "summary": "Schedule Agent: Predicted 10-day delay on TASK-142 (Install UPS-2). Critical path completion shifted to Sep 14, 2026.",
            "details": {
                "task_code": "TASK-142",
                "delay_days": 10,
                "is_critical_path": True,
                "downstream_blocked_tasks": 3
            },
            "explainability": {
                "reasoning": "UPS-2 installation is on the critical path. 10-day delay directly shifts IST Level 3 commissioning.",
                "recovery_options": ["Vertiv alternative (+4 days)", "Eaton tap adjustment (+2 days)"]
            }
        },
        {
            "id": "evt-003",
            "trace_id": "trace-demo-1001",
            "source_agent": "supply_chain",
            "event_type": "alternative_found",
            "severity": "info",
            "entity_type": "vendor",
            "entity_id": "VERTIV",
            "summary": "Supply Chain Agent: Sourced compatible Vertiv replacement unit. Delivery lead time: 4 days (+12,400 INR).",
            "details": {
                "vendor_code": "VERTIV",
                "vendor_name": "Vertiv Infrastructure",
                "lead_time_days": 4,
                "reliability_score": 0.94
            },
            "explainability": {
                "reasoning": "Vertiv has available stock of Liebert EXM 400kVA (400V native output) in regional warehouse."
            }
        },
        {
            "id": "evt-004",
            "trace_id": "trace-demo-1001",
            "source_agent": "commissioning",
            "event_type": "commissioning_blocked",
            "severity": "warning",
            "entity_type": "commissioning_test",
            "entity_id": "CX-044",
            "summary": "Commissioning Agent: Blocked CX-044 (UPS-2 Full Load Test) pending NCR-023 resolution.",
            "details": {
                "test_code": "CX-044",
                "blocked_by": "NCR-023",
                "ist_level": 3
            },
            "explainability": {
                "reasoning": "IST Level 3 integrated system test cannot proceed without verified 400V power input."
            }
        },
        {
            "id": "evt-005",
            "trace_id": "trace-demo-1001",
            "source_agent": "knowledge",
            "event_type": "precedent_found",
            "severity": "info",
            "entity_type": "rfi",
            "entity_id": "RFI-047",
            "summary": "Knowledge Agent: Identified identical tap adjustment precedent under RFI-047 (UPS-1 tap configuration).",
            "details": {
                "precedent_rfi": "RFI-047",
                "resolution": "Output autotransformer tap adjustment",
                "cost": 0,
                "time_saved_hours": 12.0
            },
            "explainability": {
                "reasoning": "Eaton autotransformer has internal ±5% taps. Field technician can re-tap unit in 1 day under warranty."
            }
        }
    ]

    for evt in demo_cascade_events:
        inst = CascadeEvent(
            id=to_uuid(evt["id"]),
            trace_id=evt["trace_id"],
            source_agent=evt["source_agent"],
            event_type=evt["event_type"],
            severity=evt["severity"],
            entity_type=evt["entity_type"],
            entity_id=evt["entity_id"],
            summary=evt["summary"],
            details=evt["details"],
            explainability=evt["explainability"]
        )
        db.add(inst)

    await db.commit()
    print("✅ SQL Database seed complete")


def seed_vector_db():
    """Seed ChromaDB with pre-computed text chunks representing our documents."""
    print("📚 Seeding ChromaDB Vector Store...")
    try:
        chroma = get_chroma_client()
        # Get or create collection
        collection = chroma.get_or_create_collection("dcbrain_documents")

        # Clear existing entries
        try:
            collection.delete(where={"project": "dcbrain"})
        except Exception:
            pass

        # Text chunks to insert
        chunks = [
            {
                "id": "chunk_elec_1",
                "text": "SPEC-ELEC-001 Section 4.3.2: The uninterruptible power supply (UPS) systems shall supply a nominal output voltage of 400V AC, three-phase, 50Hz configuration. Voltage regulation must be maintained within ±5% under all dynamic step-load operating parameters to preserve Tier III concurrent maintainability standard.",
                "metadata": {
                    "doc_code": "DC-ALPHA-SPEC-ELEC",
                    "file_name": "DC-Alpha-Electrical-Spec-v3.pdf",
                    "page": 47,
                    "section": "4.3.2",
                    "project": "dcbrain"
                }
            },
            {
                "id": "chunk_elec_2",
                "text": "SPEC-ELEC-001 Section 4.3.5: Redundancy criteria for the low-voltage UPS system mandates an N+1 topology configuration. The critical load power trains must be compartmentalized in separate zones to prevent single point failures from bringing down the concurrently maintainable system configuration.",
                "metadata": {
                    "doc_code": "DC-ALPHA-SPEC-ELEC",
                    "file_name": "DC-Alpha-Electrical-Spec-v3.pdf",
                    "page": 49,
                    "section": "4.3.5",
                    "project": "dcbrain"
                }
            },
            {
                "id": "chunk_po_1",
                "text": "PO-UPS-2026-002 submittal Eaton Power Solutions details: Eaton 93PM-400 double-conversion UPS, rated load capacity 400 kVA. Output terminal ratings specify nominal voltage output: 380V AC phase-to-phase, intended for industrial bypass configurations.",
                "metadata": {
                    "doc_code": "DC-ALPHA-PO-UPS2",
                    "file_name": "PO-UPS-2026-002-Submittal.pdf",
                    "page": 12,
                    "section": "Eaton Spec Sheet",
                    "project": "dcbrain"
                }
            },
            {
                "id": "chunk_rfi_1",
                "text": "RFI-047 Resolution: Eaton supplied a 380V tap transformer configuration on UPS-1. Standard data center voltage specifications are 400V. Eaton adjusted taps on the output autotransformer to deliver true 400V configuration, resolved under the warranty agreement clause 4.2.1 without additional charge.",
                "metadata": {
                    "doc_code": "RFI-047",
                    "file_name": "RFI-047-Resolution.pdf",
                    "page": 1,
                    "section": "Resolution Details",
                    "project": "dcbrain"
                }
            }
        ]

        # Insert chunks
        collection.add(
            ids=[c["id"] for c in chunks],
            documents=[c["text"] for c in chunks],
            metadatas=[c["metadata"] for c in chunks]
        )
        print(f"  Inserted {len(chunks)} document chunks into ChromaDB")
    except Exception as e:
        print(f"⚠️ ChromaDB seed failed or was skipped: {e}")


async def main():
    print("🏁 Starting Master Seeder...")
    
    # 1. Init SQL tables
    await init_db()
    
    # 2. Seed SQL Database
    async with async_session_factory() as session:
        await seed_relational_db(session)

    # 3. Seed Vector DB (Chroma)
    seed_vector_db()

    # 4. Seed Graph Database (Neo4j)
    try:
        driver = await get_neo4j_driver()
        # Verify Neo4j connectivity
        async with driver.session() as s:
            await s.run("RETURN 1")
        await seed_neo4j(driver)
    except Exception as e:
        print(f"⚠️ Neo4j offline ({e}). Generating fallback JSON graph file only...")
        write_local_graph_json()

    print("🎉 DCBrain database seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
