"""
DCBrain Knowledge Graph — Master Seed Data
Defines the graph dataset (nodes and relationships) and populates Neo4j and a local fallback JSON file.
"""

import os
import json
import uuid
from datetime import datetime, date

# ── Data Definition ───────────────────────────────────────────────────

# Zones
ZONES = [
    {
        "id": "zone-power-room",
        "name": "Power Room",
        "zone_type": "power_room",
        "floor": "Ground",
        "tier_level": "III",
        "description": "Main electrical distribution and backup power hall.",
        "x_position": 50,
        "y_position": 50,
        "width": 250,
        "height": 200
    },
    {
        "id": "zone-cooling-plant",
        "name": "Cooling Plant",
        "zone_type": "cooling_plant",
        "floor": "Ground",
        "tier_level": "III",
        "description": "Chiller and primary cooling water plant.",
        "x_position": 350,
        "y_position": 50,
        "width": 250,
        "height": 200
    },
    {
        "id": "zone-it-hall-a",
        "name": "IT Hall A",
        "zone_type": "it_hall",
        "floor": "First",
        "tier_level": "III",
        "description": "High density server rack whitespace.",
        "x_position": 650,
        "y_position": 50,
        "width": 300,
        "height": 400
    }
]

# Vendors
VENDORS = [
    {
        "id": "vend-eaton",
        "code": "EATON",
        "name": "Eaton Power Solutions",
        "category": "electrical",
        "reliability_score": 0.92,
        "on_time_delivery_rate": 0.88,
        "contact_email": "support@eaton.com"
    },
    {
        "id": "vend-cat",
        "code": "CAT",
        "name": "Caterpillar India",
        "category": "electrical",
        "reliability_score": 0.89,
        "on_time_delivery_rate": 0.82,
        "contact_email": "power@cat.in"
    },
    {
        "id": "vend-schneider",
        "code": "SCHNEIDER",
        "name": "Schneider Electric",
        "category": "electrical",
        "reliability_score": 0.95,
        "on_time_delivery_rate": 0.90,
        "contact_email": "dc.support@se.com"
    },
    {
        "id": "vend-spx",
        "code": "SPX",
        "name": "SPX Marley",
        "category": "mechanical",
        "reliability_score": 0.78,
        "on_time_delivery_rate": 0.72,
        "contact_email": "cooling@spx.com"
    },
    {
        "id": "vend-vertiv",
        "code": "VERTIV",
        "name": "Vertiv Infrastructure",
        "category": "mechanical",
        "reliability_score": 0.94,
        "on_time_delivery_rate": 0.92,
        "contact_email": "hvac@vertiv.com"
    }
]

# Equipment
EQUIPMENT = [
    {
        "id": "eq-ups-1",
        "tag": "UPS-1",
        "name": "Eaton 93PM-400 UPS",
        "category": "ups",
        "make": "Eaton",
        "model": "93PM-400",
        "status": "commissioned",
        "rated_capacity": "400 kVA",
        "voltage_rating": "400V",
        "redundancy": "N+1",
        "zone_id": "zone-power-room",
        "vendor_id": "vend-eaton",
        "x_position": 20,
        "y_position": 30,
        "is_critical_path": False,
        "risk_score": 0.05
    },
    {
        "id": "eq-ups-2",
        "tag": "UPS-2",
        "name": "Eaton 93PM-400 UPS",
        "category": "ups",
        "make": "Eaton",
        "model": "93PM-400",
        "status": "ncr_raised",
        "rated_capacity": "400 kVA",
        "voltage_rating": "380V",  # Mismatch (spec requires 400V)
        "redundancy": "N+1",
        "zone_id": "zone-power-room",
        "vendor_id": "vend-eaton",
        "x_position": 20,
        "y_position": 90,
        "is_critical_path": True,
        "risk_score": 0.85
    },
    {
        "id": "eq-gen-1",
        "tag": "GEN-1",
        "name": "Caterpillar 3516B Genset",
        "category": "generator",
        "make": "Caterpillar",
        "model": "3516B",
        "status": "commissioned",
        "rated_capacity": "2000 kW",
        "voltage_rating": "11kV",
        "redundancy": "N+1",
        "zone_id": "zone-power-room",
        "vendor_id": "vend-cat",
        "x_position": 140,
        "y_position": 30,
        "is_critical_path": False,
        "risk_score": 0.1
    },
    {
        "id": "eq-gen-2",
        "tag": "GEN-2",
        "name": "Caterpillar 3516B Genset",
        "category": "generator",
        "make": "Caterpillar",
        "model": "3516B",
        "status": "installed",
        "rated_capacity": "2000 kW",
        "voltage_rating": "11kV",
        "redundancy": "N+1",
        "zone_id": "zone-power-room",
        "vendor_id": "vend-cat",
        "x_position": 140,
        "y_position": 90,
        "is_critical_path": False,
        "risk_score": 0.2
    },
    {
        "id": "eq-swg-1",
        "tag": "SWG-1",
        "name": "Schneider MasterPact LV Switchgear",
        "category": "switchgear",
        "make": "Schneider Electric",
        "model": "MasterPact",
        "status": "commissioned",
        "rated_capacity": "3200A",
        "voltage_rating": "400V",
        "redundancy": "2N",
        "zone_id": "zone-power-room",
        "vendor_id": "vend-schneider",
        "x_position": 80,
        "y_position": 30,
        "is_critical_path": False,
        "risk_score": 0.05
    },
    {
        "id": "eq-swg-2",
        "tag": "SWG-2",
        "name": "Schneider MasterPact LV Switchgear",
        "category": "switchgear",
        "make": "Schneider Electric",
        "model": "MasterPact",
        "status": "in_transit",
        "rated_capacity": "3200A",
        "voltage_rating": "400V",
        "redundancy": "2N",
        "zone_id": "zone-power-room",
        "vendor_id": "vend-schneider",
        "x_position": 80,
        "y_position": 90,
        "is_critical_path": True,
        "risk_score": 0.65
    },
    {
        "id": "eq-ct-1",
        "tag": "CT-1",
        "name": "SPX Marley Cooling Tower",
        "category": "cooling_tower",
        "make": "SPX Marley",
        "model": "Marley-NC",
        "status": "in_transit",
        "rated_capacity": "1200 TR",
        "voltage_rating": "400V",
        "redundancy": "N+1",
        "zone_id": "zone-cooling-plant",
        "vendor_id": "vend-spx",
        "x_position": 30,
        "y_position": 40,
        "is_critical_path": True,
        "risk_score": 0.75
    },
    {
        "id": "eq-crah-1",
        "tag": "CRAH-1",
        "name": "Vertiv Liebert CRAH",
        "category": "crah",
        "make": "Vertiv",
        "model": "Liebert-PCW",
        "status": "commissioned",
        "rated_capacity": "150 kW",
        "voltage_rating": "400V",
        "redundancy": "N+20%",
        "zone_id": "zone-cooling-plant",
        "vendor_id": "vend-vertiv",
        "x_position": 140,
        "y_position": 40,
        "is_critical_path": False,
        "risk_score": 0.05
    },
    {
        "id": "eq-crah-2",
        "tag": "CRAH-2",
        "name": "Vertiv Liebert CRAH",
        "category": "crah",
        "make": "Vertiv",
        "model": "Liebert-PCW",
        "status": "installed",
        "rated_capacity": "150 kW",
        "voltage_rating": "400V",
        "redundancy": "N+20%",
        "zone_id": "zone-cooling-plant",
        "vendor_id": "vend-vertiv",
        "x_position": 140,
        "y_position": 100,
        "is_critical_path": False,
        "risk_score": 0.45
    }
]

# Specifications
SPECIFICATIONS = [
    {
        "id": "spec-elec-001",
        "doc_code": "SPEC-ELEC-001",
        "title": "Low Voltage Power Distribution & UPS Specification",
        "category": "electrical",
        "version": "1.0",
        "requirements": [
            {"id": "4.3.2", "text": "UPS system voltage rating shall be 400V ±5%, three-phase, 50Hz.", "category": "electrical"},
            {"id": "4.3.5", "text": "UPS system shall provide N+1 redundancy for the active IT load.", "category": "electrical"},
            {"id": "4.4.1", "text": "Switchgear shall contain integrated arc-flash detection relays.", "category": "electrical"}
        ]
    },
    {
        "id": "spec-mech-001",
        "doc_code": "SPEC-MECH-001",
        "title": "HVAC Precision Cooling & Containment Specification",
        "category": "mechanical",
        "version": "1.2",
        "requirements": [
            {"id": "5.1.2", "text": "Precision cooling units shall maintain white space temperature at 22°C ±2°C.", "category": "mechanical"},
            {"id": "5.2.1", "text": "CRAH airflow capacity shall not fall below 12,000 CFM under full load.", "category": "mechanical"}
        ]
    }
]

# Purchase Orders
PURCHASE_ORDERS = [
    {
        "id": "po-ups2",
        "po_number": "PO-UPS-2026-002",
        "description": "Eaton 93PM-400 UPS system for Power Room Room B",
        "value": 14500000.0,
        "status": "shipped",
        "order_date": "2026-04-10",
        "expected_delivery": "2026-07-28",
        "submittal_status": "reviewed",
        "submittal_data": {
            "model": "93PM-400",
            "capacity": "400 kVA",
            "voltage": "380V"  # Mismatch! Spec requires 400V
        },
        "equipment_id": "eq-ups-2",
        "vendor_id": "vend-eaton"
    },
    {
        "id": "po-swg2",
        "po_number": "PO-SWG-2026-008",
        "description": "Schneider LV Switchgear secondary feed panels",
        "value": 8200000.0,
        "status": "shipped",
        "order_date": "2026-05-01",
        "expected_delivery": "2026-08-05",
        "submittal_status": "approved",
        "submittal_data": {
            "model": "MasterPact",
            "voltage": "400V"
        },
        "equipment_id": "eq-swg-2",
        "vendor_id": "vend-schneider"
    }
]

# NCRs
NCRS = [
    {
        "id": "ncr-023",
        "ncr_number": "NCR-023",
        "title": "Voltage Mismatch on UPS-2 Vendor Submittal",
        "description": "Vendor submittal specifies 380V output rating, whereas project specification SPEC-ELEC-001 Section 4.3.2 strictly requires 400V.",
        "severity": "critical",
        "status": "open",
        "spec_requirement": "UPS system voltage rating shall be 400V ±5%",
        "spec_reference": "Section 4.3.2, Page 47",
        "actual_value": "380V",
        "deviation_details": "Output voltage 380V is outside the permitted range of 380V-420V (400V ±5%). This will prevent direct integration with local utility feed.",
        "schedule_impact_days": 10,
        "cost_impact": 0.0,
        "critical_path_affected": True,
        "equipment_id": "eq-ups-2",
        "specification_id": "spec-elec-001",
        "purchase_order_id": "po-ups2",
        "ai_reasoning": {
            "evidence": [
                {"source": "SPEC-ELEC-001", "finding": "Voltage rating: 400V required"},
                {"source": "PO-UPS-2026-002 submittal", "finding": "Vendor specifies: 380V output"},
                {"source": "Schedule", "finding": "UPS-2 is prerequisite for downstream load bank testing Task-143"}
            ],
            "reasoning": "This voltage rating deviation is critical because 380V equipment cannot support the standard 400V three-phase configuration of the downstream IT distribution bus without intermediate step-up transformers, which adds cost and weight. Eaton accepts warranty swaps for correct voltage models as seen in RFI-047.",
            "alternatives": [
                {"option": "Warranty swap (EATON)", "time_days": 6, "cost": 0},
                {"option": "Order alternative (VERTIV)", "time_days": 4, "cost": 12400}
            ]
        }
    }
]

# Schedule Tasks
TASKS = [
    {
        "id": "task-142",
        "task_code": "TASK-142",
        "name": "Install & Mount UPS-2",
        "phase": "construction",
        "category": "electrical",
        "planned_start": "2026-08-01",
        "planned_end": "2026-08-10",
        "status": "blocked",
        "progress_pct": 0.0,
        "is_critical_path": True,
        "equipment_id": "eq-ups-2",
        "risk_score": 0.8,
        "delay_days": 10,
        "recovery_plans": [
            {
                "plan": "Plan A",
                "description": "Invoke warranty swap under Eaton agreement Clause 4.2.1. Expected delivery of replacement within 6 days.",
                "time_saved": 6,
                "cost": 0
            },
            {
                "plan": "Plan B",
                "description": "Procure compatible Vertiv Liebert unit on priority. Lead time: 4 days.",
                "time_saved": 8,
                "cost": 12400
            },
            {
                "plan": "Plan C",
                "description": "Proceed with mechanical plant install and delay electrical power testing sequence.",
                "time_saved": 3,
                "cost": 0
            }
        ]
    },
    {
        "id": "task-143",
        "task_code": "TASK-143",
        "name": "UPS-2 Load Bank Testing",
        "phase": "commissioning",
        "category": "electrical",
        "planned_start": "2026-08-11",
        "planned_end": "2026-08-15",
        "status": "not_started",
        "progress_pct": 0.0,
        "is_critical_path": True,
        "equipment_id": "eq-ups-2"
    },
    {
        "id": "task-144",
        "task_code": "TASK-144",
        "name": "Integrated Systems Testing - Power (IST-L3)",
        "phase": "commissioning",
        "category": "electrical",
        "planned_start": "2026-08-16",
        "planned_end": "2026-08-20",
        "status": "not_started",
        "progress_pct": 0.0,
        "is_critical_path": True
    }
]

# Task Dependencies (TASK-142 -> TASK-143 -> TASK-144)
DEPENDENCIES = [
    {
        "predecessor_id": "task-142",
        "successor_id": "task-143"
    },
    {
        "predecessor_id": "task-143",
        "successor_id": "task-144"
    }
]

# Shipments
SHIPMENTS = [
    {
        "id": "ship-001",
        "tracking_id": "TRK-SCH-002",
        "description": "Schneider master breaker cabinets",
        "status": "in_transit",
        "origin_city": "Chennai",
        "origin_country": "India",
        "current_location": "Inland Highway, Pune bypass",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "expected_arrival": "2026-08-05",
        "delay_days": 2,
        "risk_score": 0.45,
        "equipment_id": "eq-swg-2",
        "purchase_order_id": "po-swg2",
        "vendor_id": "vend-schneider"
    },
    {
        "id": "ship-002",
        "tracking_id": "TRK-SPX-101",
        "description": "SPX Marley Cooling Tower headers and cell",
        "status": "delayed",
        "origin_city": "Shanghai",
        "origin_country": "China",
        "current_location": "JNPT Port Customs, Mumbai",
        "latitude": 18.9500,
        "longitude": 72.9500,
        "expected_arrival": "2026-07-25",
        "delay_days": 8,
        "risk_score": 0.8,
        "risk_factors": ["Port customs clearance congestion", "Monsoon sea traffic"],
        "equipment_id": "eq-ct-1",
        "purchase_order_id": None,
        "vendor_id": "vend-spx",
        "ai_alternatives": [
            {
                "option": "Customs priority filing",
                "impact": "Reduces delay to 3 days",
                "cost": 1500
            }
        ],
        "ai_impact_analysis": {
            "critical_path": True,
            "downstream_impact": "Blocks Cooling Plant Commissioning (TASK-180)",
            "mitigation": "Initiate priority customs clearance."
        }
    }
]

# Commissioning Tests
TESTS = [
    {
        "id": "cx-044",
        "test_code": "CX-044",
        "name": "UPS-2 Load Bank Test",
        "category": "electrical",
        "standard_reference": "TIA-942 Section 5.3",
        "tier_requirement": "III",
        "result": "not_started",
        "is_blocked": True,
        "blocked_by": "UPS-2 NCR open (voltage deviation)",
        "blocking_tests": ["CX-045", "CX-046", "IST-L3-Power"],
        "ist_level": 3,
        "equipment_id": "eq-ups-2",
        "schedule_task_id": "task-143",
        "procedure_steps": [
            {"step": 1, "action": "Verify load bank connections and cable sizing.", "criteria": "Proper connections."},
            {"step": 2, "action": "Apply 100% capacity step load (400 kVA).", "criteria": "UPS runs stable for 4 hours without overheat."},
            {"step": 3, "action": "Verify transfer time to bypass during utility failure.", "criteria": "Transfer time < 10 milliseconds."}
        ],
        "acceptance_criteria": {
            "load_kva": 400,
            "transfer_time_max_ms": 10,
            "output_voltage": "400V ±5%"
        }
    },
    {
        "id": "cx-047",
        "test_code": "CX-047",
        "name": "CRAH-2 Precision Airflow",
        "category": "mechanical",
        "standard_reference": "ASHRAE TC 9.9",
        "tier_requirement": "III",
        "result": "fail",
        "is_blocked": False,
        "blocking_tests": ["IST-L3-Cooling"],
        "ist_level": 3,
        "equipment_id": "eq-crah-2",
        "procedure_steps": [
            {"step": 1, "action": "Power on CRAH-2 and verify variable fan controllers.", "criteria": "VFD responds to control signal."},
            {"step": 2, "action": "Apply thermal load and measure hot aisle containment outflow.", "criteria": "Containment temperature < 25°C."}
        ],
        "measured_values": {
            "temperature_c": 28.3,
            "airflow_cfm": 8500
        },
        "acceptance_criteria": {
            "temperature_c": {"max": 25.0},
            "airflow_cfm": {"min": 12000}
        },
        "ai_diagnosis": "Containment outflow temperature exceeded the 25.0°C maximum limit by 3.3°C, and airflow capacity measured 8,500 CFM against a required 12,000 CFM threshold.",
        "ai_fix_suggestion": "The combination of high temperature and low airflow points directly to Valve V17 actuator drift, restricting chilled water supply by approximately 30%. Action: Recalibrate Valve V17 actuator limit switches per manufacturer manual Section 6.3.2, page 34. Check hot aisle seals at Rack B-7.",
        "ai_root_cause": [
            "Chilled water valve V17 limit switch drift",
            "Aisle containment gasket displacement"
        ]
    }
]

# RFIs
RFIS = [
    {
        "id": "rfi-047",
        "rfi_number": "RFI-047",
        "subject": "UPS-1 Voltage Swap Request",
        "question": "The factory submittal of Eaton for UPS-1 showed 380V configuration. The design spec demands 400V. Can the client accept 380V with bypass config or should we request Eaton to adjust transformer taps?",
        "answer": "Client rejects 380V as it violates standard 400V utility setup. Eaton was instructed to adjust taps to 400V at no additional cost. Eaton complied under contract warranty clause 4.2.1, saving a procurement re-order cycle.",
        "status": "closed",
        "priority": "high",
        "category": "electrical",
        "discipline": "Electrical Engineering",
        "raised_by": "J. Roy (Lead Electrical Engineer)",
        "assigned_to": "S. Varma (Project Manager)",
        "resolution_time_hours": 120.0,
        "similar_rfis": [],
        "equipment_id": "eq-ups-1"
    }
]

# Project Documents (RAG corpus)
DOCUMENTS = [
    {
        "id": "doc-001",
        "doc_code": "DC-ALPHA-SPEC-ELEC",
        "title": "Low Voltage Power Distribution & UPS Specification",
        "doc_type": "specification",
        "category": "electrical",
        "file_name": "DC-Alpha-Electrical-Spec-v3.pdf",
        "chunk_count": 48,
        "is_indexed": True,
        "content_summary": "Design standard for the data center low voltage system. Requires 400V output UPS, N+1 topology, redundant feeder paths, and dual-bus switchgear configurations."
    },
    {
        "id": "doc-002",
        "doc_code": "DC-ALPHA-PO-UPS2",
        "title": "Purchase Order PO-UPS-2026-002 and Submittal Pack",
        "doc_type": "submittal",
        "category": "electrical",
        "file_name": "PO-UPS-2026-002-Submittal.pdf",
        "chunk_count": 14,
        "is_indexed": True,
        "content_summary": "Vendor submittal documents from Eaton Power Solutions details a 400 kVA system with double conversion and 380V rated voltage output."
    }
]


# ── Seed Execution ────────────────────────────────────────────────────

def get_in_memory_data():
    """Returns the seed data as a dictionary of lists."""
    return {
        "zones": ZONES,
        "vendors": VENDORS,
        "equipment": EQUIPMENT,
        "specifications": SPECIFICATIONS,
        "purchase_orders": PURCHASE_ORDERS,
        "ncrs": NCRS,
        "tasks": TASKS,
        "dependencies": DEPENDENCIES,
        "shipments": SHIPMENTS,
        "tests": TESTS,
        "rfis": RFIS,
        "documents": DOCUMENTS
    }


def write_local_graph_json():
    """Generates and writes nodes and edges to a local JSON file for the fallback graph client."""
    nodes = []
    edges = []

    # Map zones
    for z in ZONES:
        nodes.append({
            "id": z["id"],
            "label": "Zone",
            "properties": z
        })

    # Map vendors
    for v in VENDORS:
        nodes.append({
            "id": v["id"],
            "label": "Vendor",
            "properties": v
        })

    # Map equipment
    for eq in EQUIPMENT:
        nodes.append({
            "id": eq["id"],
            "label": "Equipment",
            "properties": eq
        })
        # Relationships
        edges.append({
            "source": eq["id"],
            "target": eq["zone_id"],
            "type": "INSTALLED_IN"
        })
        edges.append({
            "source": eq["id"],
            "target": eq["vendor_id"],
            "type": "SUPPLIED_BY"
        })

    # Map specs
    for s in SPECIFICATIONS:
        nodes.append({
            "id": s["id"],
            "label": "Specification",
            "properties": s
        })

    # Link equipment to specs
    for eq in EQUIPMENT:
        if eq["category"] == "ups":
            edges.append({
                "source": eq["id"],
                "target": "spec-elec-001",
                "type": "SPECIFIED_IN"
            })
        elif eq["category"] == "crah":
            edges.append({
                "source": eq["id"],
                "target": "spec-mech-001",
                "type": "SPECIFIED_IN"
            })

    # Map POs
    for po in PURCHASE_ORDERS:
        nodes.append({
            "id": po["id"],
            "label": "PurchaseOrder",
            "properties": po
        })
        edges.append({
            "source": po["id"],
            "target": po["equipment_id"],
            "type": "REFERENCES"
        })
        edges.append({
            "source": po["id"],
            "target": po["vendor_id"],
            "type": "PLACED_WITH"
        })
        edges.append({
            "source": po["equipment_id"],
            "target": po["id"],
            "type": "ORDERED_VIA"
        })

    # Map NCRs
    for ncr in NCRS:
        nodes.append({
            "id": ncr["id"],
            "label": "NCR",
            "properties": ncr
        })
        edges.append({
            "source": ncr["id"],
            "target": ncr["equipment_id"],
            "type": "RAISED_AGAINST"
        })
        edges.append({
            "source": ncr["id"],
            "target": ncr["specification_id"],
            "type": "DEVIATES_FROM"
        })
        edges.append({
            "source": ncr["id"],
            "target": ncr["purchase_order_id"],
            "type": "AFFECTS_PO"
        })
        edges.append({
            "source": ncr["id"],
            "target": "task-142",
            "type": "IMPACTS_TASK"
        })

    # Map tasks
    for t in TASKS:
        nodes.append({
            "id": t["id"],
            "label": "ScheduleTask",
            "properties": t
        })
        if t.get("equipment_id"):
            edges.append({
                "source": t["id"],
                "target": t["equipment_id"],
                "type": "REQUIRES"
            })

    # Task dependencies
    for dep in DEPENDENCIES:
        edges.append({
            "source": dep["successor_id"],
            "target": dep["predecessor_id"],
            "type": "DEPENDS_ON"
        })

    # Map shipments
    for s in SHIPMENTS:
        nodes.append({
            "id": s["id"],
            "label": "Shipment",
            "properties": s
        })
        if s.get("equipment_id"):
            edges.append({
                "source": s["id"],
                "target": s["equipment_id"],
                "type": "DELIVERS"
            })

    # Map tests
    for cx in TESTS:
        nodes.append({
            "id": cx["id"],
            "label": "CommissioningTest",
            "properties": cx
        })
        if cx.get("equipment_id"):
            edges.append({
                "source": cx["id"],
                "target": cx["equipment_id"],
                "type": "TESTS"
            })
            edges.append({
                "source": cx["equipment_id"],
                "target": cx["id"],
                "type": "TESTED_BY"
            })
        if cx.get("is_blocked"):
            edges.append({
                "source": cx["id"],
                "target": "ncr-023",
                "type": "BLOCKED_BY"
            })

    # Map RFIs
    for r in RFIS:
        nodes.append({
            "id": r["id"],
            "label": "RFI",
            "properties": r
        })
        if r.get("equipment_id"):
            edges.append({
                "source": r["id"],
                "target": r["equipment_id"],
                "type": "RELATES_TO"
            })

    # Map documents
    for d in DOCUMENTS:
        nodes.append({
            "id": d["id"],
            "label": "Document",
            "properties": d
        })

    os.makedirs("./backend/data", exist_ok=True)
    with open("./backend/data/graph_store.json", "w") as f:
        json.dump({"nodes": nodes, "edges": edges}, f, indent=2)

    print("✅ Fallback in-memory graph written to backend/data/graph_store.json")


async def seed_neo4j(driver):
    """Seed the Neo4j database if running."""
    # Write fallback JSON first
    write_local_graph_json()

    print("🔗 Connecting to Neo4j to seed data...")
    # Read the local JSON and push to Neo4j
    with open("./backend/data/graph_store.json") as f:
        graph = json.load(f)

    async with driver.session() as session:
        # Clear existing data
        await session.run("MATCH (n) DETACH DELETE n")
        print("  Cleared old Neo4j graph nodes and edges")

        # Create nodes
        for node in graph["nodes"]:
            # Sanitize labels and format properties
            label = node["label"]
            props = node["properties"]

            # Convert nested objects/dates to Cypher compatible types
            sanitized_props = {}
            for k, v in props.items():
                if isinstance(v, (dict, list)):
                    sanitized_props[k] = json.dumps(v)
                elif isinstance(v, (date, datetime)):
                    sanitized_props[k] = v.isoformat()
                else:
                    sanitized_props[k] = v

            query = f"CREATE (n:{label} $props)"
            await session.run(query, {"props": sanitized_props})

        print(f"  Created {len(graph['nodes'])} nodes in Neo4j")

        # Create edges
        for edge in graph["edges"]:
            source_id = edge["source"]
            target_id = edge["target"]
            rel_type = edge["type"]

            # Find by matching id properties
            query = f"""
            MATCH (a) WHERE a.id = $source_id
            MATCH (b) WHERE b.id = $target_id
            CREATE (a)-[r:{rel_type}]->(b)
            """
            await session.run(query, {"source_id": source_id, "target_id": target_id})

        print(f"  Created {len(graph['edges'])} relationships in Neo4j")
    print("✅ Neo4j seeding complete")
