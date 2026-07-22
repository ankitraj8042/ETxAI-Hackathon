"""
DCBrain API — Digital Twin
Serves floor plan data, equipment states, and entity detail panels.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import Equipment, Zone, NCR, NCRStatus, CommissioningTest, TestResult

router = APIRouter()


@router.get("/zones")
async def get_zones(db: AsyncSession = Depends(get_db)):
    """Get all zones with their equipment for the floor plan."""
    result = await db.execute(
        select(Zone).options(selectinload(Zone.equipment))
    )
    zones = result.scalars().all()

    return [
        {
            "id": str(z.id),
            "name": z.name,
            "zone_type": z.zone_type,
            "floor": z.floor,
            "tier_level": z.tier_level,
            "position": {"x": z.x_position, "y": z.y_position},
            "size": {"width": z.width, "height": z.height},
            "equipment": [
                {
                    "id": str(eq.id),
                    "tag": eq.tag,
                    "name": eq.name,
                    "category": eq.category.value if eq.category else "other",
                    "status": eq.status.value if eq.status else "specified",
                    "make": eq.make,
                    "model": eq.model,
                    "risk_score": eq.risk_score,
                    "is_critical_path": eq.is_critical_path,
                    "position": {"x": eq.x_position, "y": eq.y_position},
                }
                for eq in z.equipment
            ],
        }
        for z in zones
    ]


@router.get("/equipment/{equipment_tag}")
async def get_equipment_detail(equipment_tag: str, db: AsyncSession = Depends(get_db)):
    """
    Get full intelligence panel for a single equipment entity.
    This is the 'click on Digital Twin' endpoint — aggregates data from all agents.
    """
    result = await db.execute(
        select(Equipment)
        .options(
            selectinload(Equipment.vendor),
            selectinload(Equipment.ncrs),
            selectinload(Equipment.commissioning_tests),
            selectinload(Equipment.purchase_orders),
        )
        .where(Equipment.tag == equipment_tag)
    )
    eq = result.scalar_one_or_none()
    if not eq:
        raise HTTPException(status_code=404, detail=f"Equipment {equipment_tag} not found")

    # Compliance intelligence
    open_ncrs = [
        {
            "ncr_number": ncr.ncr_number,
            "title": ncr.title,
            "severity": ncr.severity.value,
            "status": ncr.status.value,
            "spec_requirement": ncr.spec_requirement,
            "actual_value": ncr.actual_value,
            "spec_reference": ncr.spec_reference,
            "schedule_impact_days": ncr.schedule_impact_days,
        }
        for ncr in eq.ncrs
    ]

    # Commissioning intelligence
    tests = [
        {
            "test_code": t.test_code,
            "name": t.name,
            "result": t.result.value,
            "is_blocked": t.is_blocked,
            "blocked_by": t.blocked_by,
            "ai_diagnosis": t.ai_diagnosis,
            "ai_fix_suggestion": t.ai_fix_suggestion,
        }
        for t in eq.commissioning_tests
    ]

    # Supply chain intelligence
    pos = [
        {
            "po_number": po.po_number,
            "status": po.status,
            "expected_delivery": po.expected_delivery.isoformat() if po.expected_delivery else None,
            "actual_delivery": po.actual_delivery.isoformat() if po.actual_delivery else None,
        }
        for po in eq.purchase_orders
    ]

    return {
        "equipment": {
            "id": str(eq.id),
            "tag": eq.tag,
            "name": eq.name,
            "category": eq.category.value,
            "status": eq.status.value,
            "make": eq.make,
            "model": eq.model,
            "rated_capacity": eq.rated_capacity,
            "voltage_rating": eq.voltage_rating,
            "redundancy": eq.redundancy,
            "specifications": eq.specifications,
            "risk_score": eq.risk_score,
            "is_critical_path": eq.is_critical_path,
        },
        "vendor": {
            "name": eq.vendor.name if eq.vendor else None,
            "code": eq.vendor.code if eq.vendor else None,
            "reliability_score": eq.vendor.reliability_score if eq.vendor else None,
            "on_time_delivery_rate": eq.vendor.on_time_delivery_rate if eq.vendor else None,
        },
        "compliance": {
            "ncrs": open_ncrs,
            "total_ncrs": len(open_ncrs),
            "has_critical": any(n["severity"] == "critical" for n in open_ncrs),
        },
        "commissioning": {
            "tests": tests,
            "total_tests": len(tests),
            "passed": sum(1 for t in tests if t["result"] == "pass"),
            "failed": sum(1 for t in tests if t["result"] == "fail"),
            "blocked": sum(1 for t in tests if t["is_blocked"]),
        },
        "supply_chain": {
            "purchase_orders": pos,
        },
    }
