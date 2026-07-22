"""
DCBrain Knowledge Graph — Cypher Query Library
Pre-built queries for agent reasoning across the Knowledge Graph.
"""


class GraphQueries:
    """Collection of Cypher queries used by agents for relationship reasoning."""

    # ── Equipment Intelligence ─────────────────────────────────────────

    EQUIPMENT_FULL_CONTEXT = """
    MATCH (e:Equipment {tag: $tag})
    OPTIONAL MATCH (e)-[:INSTALLED_IN]->(z:Zone)
    OPTIONAL MATCH (e)-[:SUPPLIED_BY]->(v:Vendor)
    OPTIONAL MATCH (e)-[:SPECIFIED_IN]->(s:Specification)
    OPTIONAL MATCH (e)-[:ORDERED_VIA]->(po:PurchaseOrder)
    OPTIONAL MATCH (ncr:NCR)-[:RAISED_AGAINST]->(e)
    OPTIONAL MATCH (cx:CommissioningTest)-[:TESTS]->(e)
    OPTIONAL MATCH (rfi:RFI)-[:RELATES_TO]->(e)
    OPTIONAL MATCH (task:ScheduleTask)-[:REQUIRES]->(e)
    RETURN e, z, v, s,
           collect(DISTINCT po) as purchase_orders,
           collect(DISTINCT ncr) as ncrs,
           collect(DISTINCT cx) as tests,
           collect(DISTINCT rfi) as rfis,
           collect(DISTINCT task) as tasks
    """

    # ── Impact Chain ───────────────────────────────────────────────────

    EQUIPMENT_IMPACT_CHAIN = """
    MATCH (e:Equipment {tag: $tag})
    OPTIONAL MATCH path1 = (e)<-[:REQUIRES]-(task:ScheduleTask)
    OPTIONAL MATCH path2 = (task)<-[:DEPENDS_ON*1..5]-(downstream:ScheduleTask)
    OPTIONAL MATCH path3 = (e)<-[:TESTS]-(cx:CommissioningTest)
    OPTIONAL MATCH path4 = (cx)<-[:DEPENDS_ON*1..3]-(downstream_test:CommissioningTest)
    RETURN e.tag as equipment,
           collect(DISTINCT task.task_code) as direct_tasks,
           collect(DISTINCT downstream.task_code) as downstream_tasks,
           collect(DISTINCT cx.test_code) as direct_tests,
           collect(DISTINCT downstream_test.test_code) as downstream_tests
    """

    # ── NCR Impact ─────────────────────────────────────────────────────

    NCR_FULL_IMPACT = """
    MATCH (ncr:NCR {ncr_number: $ncr_number})
    MATCH (ncr)-[:RAISED_AGAINST]->(e:Equipment)
    OPTIONAL MATCH (e)-[:INSTALLED_IN]->(z:Zone)
    OPTIONAL MATCH (e)-[:SUPPLIED_BY]->(v:Vendor)
    OPTIONAL MATCH (task:ScheduleTask)-[:REQUIRES]->(e)
    OPTIONAL MATCH (task)<-[:DEPENDS_ON*1..5]-(downstream:ScheduleTask)
    OPTIONAL MATCH (cx:CommissioningTest)-[:TESTS]->(e)
    OPTIONAL MATCH (cx)<-[:DEPENDS_ON*1..3]-(blocked:CommissioningTest)
    RETURN ncr, e, z, v,
           collect(DISTINCT task) as affected_tasks,
           collect(DISTINCT downstream) as downstream_tasks,
           collect(DISTINCT cx) as affected_tests,
           collect(DISTINCT blocked) as blocked_tests
    """

    # ── Vendor Analysis ────────────────────────────────────────────────

    VENDOR_EQUIPMENT_AND_HISTORY = """
    MATCH (v:Vendor {code: $vendor_code})
    OPTIONAL MATCH (e:Equipment)-[:SUPPLIED_BY]->(v)
    OPTIONAL MATCH (po:PurchaseOrder)-[:PLACED_WITH]->(v)
    OPTIONAL MATCH (ncr:NCR)-[:RAISED_AGAINST]->(e)
    RETURN v,
           collect(DISTINCT {tag: e.tag, category: e.category, status: e.status}) as equipment,
           collect(DISTINCT {po: po.po_number, status: po.status}) as orders,
           collect(DISTINCT {ncr: ncr.ncr_number, severity: ncr.severity}) as ncrs
    """

    # ── Similar RFI Detection ──────────────────────────────────────────

    SIMILAR_RFIS = """
    MATCH (rfi:RFI {rfi_number: $rfi_number})
    MATCH (rfi)-[:RELATES_TO]->(e:Equipment)
    MATCH (similar_rfi:RFI)-[:RELATES_TO]->(e2:Equipment)
    WHERE similar_rfi.rfi_number <> $rfi_number
      AND e.category = e2.category
      AND similar_rfi.status = 'answered'
    RETURN similar_rfi.rfi_number as rfi_number,
           similar_rfi.subject as subject,
           similar_rfi.answer as answer,
           similar_rfi.answered_date as answered_date
    LIMIT 5
    """

    # ── Critical Path Analysis ─────────────────────────────────────────

    CRITICAL_PATH_TASKS = """
    MATCH (t:ScheduleTask {is_critical_path: true})
    OPTIONAL MATCH (t)-[:REQUIRES]->(e:Equipment)
    OPTIONAL MATCH (t)-[:DEPENDS_ON]->(pred:ScheduleTask)
    RETURN t.task_code as task_code,
           t.name as name,
           t.planned_start as start,
           t.planned_end as end,
           t.status as status,
           t.risk_score as risk,
           collect(DISTINCT e.tag) as equipment,
           collect(DISTINCT pred.task_code) as predecessors
    ORDER BY t.planned_start
    """

    # ── Commissioning Dependency Chain ─────────────────────────────────

    TEST_DEPENDENCY_CHAIN = """
    MATCH (cx:CommissioningTest {test_code: $test_code})
    OPTIONAL MATCH (cx)-[:TESTS]->(e:Equipment)
    OPTIONAL MATCH (cx)-[:DEPENDS_ON]->(prereq:CommissioningTest)
    OPTIONAL MATCH (downstream:CommissioningTest)-[:DEPENDS_ON]->(cx)
    OPTIONAL MATCH (cx)-[:BLOCKED_BY]->(ncr:NCR)
    RETURN cx, e,
           collect(DISTINCT prereq.test_code) as prerequisites,
           collect(DISTINCT downstream.test_code) as dependents,
           collect(DISTINCT ncr.ncr_number) as blocking_ncrs
    """

    # ── Alternative Suppliers ──────────────────────────────────────────

    FIND_ALTERNATIVE_VENDORS = """
    MATCH (e:Equipment {tag: $tag})-[:SUPPLIED_BY]->(current_vendor:Vendor)
    MATCH (alt_equip:Equipment)-[:SUPPLIED_BY]->(alt_vendor:Vendor)
    WHERE alt_vendor <> current_vendor
      AND alt_equip.category = e.category
    RETURN DISTINCT alt_vendor.name as vendor_name,
           alt_vendor.code as vendor_code,
           alt_vendor.reliability_score as reliability,
           alt_vendor.on_time_delivery_rate as on_time_rate,
           count(alt_equip) as equipment_supplied
    ORDER BY alt_vendor.reliability_score DESC
    LIMIT 5
    """

    # ── Graph Visualization ────────────────────────────────────────────

    SUBGRAPH_AROUND_ENTITY = """
    MATCH (center {tag: $tag})
    OPTIONAL MATCH path = (center)-[r*1..2]-(connected)
    RETURN center, collect(DISTINCT path) as paths
    """
