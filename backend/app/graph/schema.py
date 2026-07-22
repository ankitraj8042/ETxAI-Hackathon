"""
DCBrain Knowledge Graph — Neo4j Schema & Constraints
Defines the graph schema with node types, relationship types, and constraints.
"""

# ── Node Labels ────────────────────────────────────────────────────────
#
# (:Equipment)        - UPS, Generator, Switchgear, Chiller, etc.
# (:Vendor)           - Equipment suppliers
# (:Zone)             - Physical zones in the data centre
# (:Specification)    - Project specifications and standards
# (:PurchaseOrder)    - Procurement orders
# (:NCR)              - Non-Conformance Reports
# (:ScheduleTask)     - Project schedule tasks
# (:CommissioningTest) - Commissioning test procedures
# (:RFI)              - Requests for Information
# (:Document)         - Project documents
#
# ── Relationship Types ─────────────────────────────────────────────────
#
# (:Equipment)-[:SUPPLIED_BY]->(:Vendor)
# (:Equipment)-[:INSTALLED_IN]->(:Zone)
# (:Equipment)-[:SPECIFIED_IN]->(:Specification)
# (:Equipment)-[:ORDERED_VIA]->(:PurchaseOrder)
# (:Equipment)-[:TESTED_BY]->(:CommissioningTest)
# (:Equipment)-[:REFERENCED_IN]->(:RFI)
# (:PurchaseOrder)-[:PLACED_WITH]->(:Vendor)
# (:NCR)-[:RAISED_AGAINST]->(:Equipment)
# (:NCR)-[:DEVIATES_FROM]->(:Specification)
# (:NCR)-[:AFFECTS_PO]->(:PurchaseOrder)
# (:NCR)-[:IMPACTS_TASK]->(:ScheduleTask)
# (:ScheduleTask)-[:DEPENDS_ON]->(:ScheduleTask)
# (:ScheduleTask)-[:REQUIRES]->(:Equipment)
# (:CommissioningTest)-[:BLOCKED_BY]->(:NCR)
# (:CommissioningTest)-[:DEPENDS_ON]->(:CommissioningTest)
# (:RFI)-[:RELATES_TO]->(:Equipment)
# (:RFI)-[:SIMILAR_TO]->(:RFI)
# (:Vendor)-[:HAS_HISTORY]->(:PerformanceRecord)

SETUP_CONSTRAINTS = [
    # Uniqueness constraints
    "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Equipment) REQUIRE e.tag IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (v:Vendor) REQUIRE v.code IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (z:Zone) REQUIRE z.name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Specification) REQUIRE s.doc_code IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (po:PurchaseOrder) REQUIRE po.po_number IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:NCR) REQUIRE n.ncr_number IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (t:ScheduleTask) REQUIRE t.task_code IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (cx:CommissioningTest) REQUIRE cx.test_code IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (r:RFI) REQUIRE r.rfi_number IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.doc_code IS UNIQUE",
]

SETUP_INDEXES = [
    "CREATE INDEX IF NOT EXISTS FOR (e:Equipment) ON (e.category)",
    "CREATE INDEX IF NOT EXISTS FOR (e:Equipment) ON (e.status)",
    "CREATE INDEX IF NOT EXISTS FOR (n:NCR) ON (n.severity)",
    "CREATE INDEX IF NOT EXISTS FOR (n:NCR) ON (n.status)",
    "CREATE INDEX IF NOT EXISTS FOR (t:ScheduleTask) ON (t.phase)",
    "CREATE INDEX IF NOT EXISTS FOR (t:ScheduleTask) ON (t.is_critical_path)",
    "CREATE INDEX IF NOT EXISTS FOR (cx:CommissioningTest) ON (cx.result)",
    "CREATE INDEX IF NOT EXISTS FOR (r:RFI) ON (r.status)",
]


async def setup_graph_schema(driver):
    """Apply constraints and indexes to Neo4j."""
    async with driver.session() as session:
        for constraint in SETUP_CONSTRAINTS:
            try:
                await session.run(constraint)
            except Exception as e:
                print(f"  Constraint skipped (may already exist): {e}")

        for index in SETUP_INDEXES:
            try:
                await session.run(index)
            except Exception as e:
                print(f"  Index skipped (may already exist): {e}")

    print("✅ Neo4j schema setup complete")
