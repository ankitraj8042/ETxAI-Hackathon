"""
DCBrain API — Compliance & Quality
Document upload, spec checking, NCR management.
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models import NCR, NCRStatus, Specification, PurchaseOrder, Equipment

router = APIRouter()


@router.get("/ncrs")
async def list_ncrs(
    status: str = None,
    severity: str = None,
    db: AsyncSession = Depends(get_db),
):
    """List all NCRs with optional filtering."""
    query = select(NCR).order_by(NCR.created_at.desc())
    if status:
        query = query.where(NCR.status == status)
    if severity:
        query = query.where(NCR.severity == severity)

    result = await db.execute(query)
    ncrs = result.scalars().all()

    return [
        {
            "id": str(n.id),
            "ncr_number": n.ncr_number,
            "title": n.title,
            "description": n.description,
            "severity": n.severity.value,
            "status": n.status.value,
            "spec_requirement": n.spec_requirement,
            "actual_value": n.actual_value,
            "spec_reference": n.spec_reference,
            "schedule_impact_days": n.schedule_impact_days,
            "cost_impact": n.cost_impact,
            "critical_path_affected": n.critical_path_affected,
            "ai_reasoning": n.ai_reasoning,
            "created_at": n.created_at.isoformat(),
        }
        for n in ncrs
    ]


@router.get("/ncrs/{ncr_number}")
async def get_ncr_detail(ncr_number: str, db: AsyncSession = Depends(get_db)):
    """Get detailed NCR with full explainability."""
    result = await db.execute(
        select(NCR).where(NCR.ncr_number == ncr_number)
    )
    ncr = result.scalar_one_or_none()
    if not ncr:
        raise HTTPException(status_code=404, detail=f"NCR {ncr_number} not found")

    return {
        "id": str(ncr.id),
        "ncr_number": ncr.ncr_number,
        "title": ncr.title,
        "description": ncr.description,
        "severity": ncr.severity.value,
        "status": ncr.status.value,
        "spec_requirement": ncr.spec_requirement,
        "actual_value": ncr.actual_value,
        "spec_reference": ncr.spec_reference,
        "deviation_details": ncr.deviation_details,
        "schedule_impact_days": ncr.schedule_impact_days,
        "cost_impact": ncr.cost_impact,
        "critical_path_affected": ncr.critical_path_affected,
        "resolution": ncr.resolution,
        "ai_reasoning": ncr.ai_reasoning,
        "created_at": ncr.created_at.isoformat(),
    }


@router.get("/specifications")
async def list_specifications(db: AsyncSession = Depends(get_db)):
    """List all project specifications."""
    result = await db.execute(
        select(Specification).order_by(Specification.doc_code)
    )
    specs = result.scalars().all()

    return [
        {
            "id": str(s.id),
            "doc_code": s.doc_code,
            "title": s.title,
            "category": s.category,
            "version": s.version,
            "requirements_count": len(s.requirements) if s.requirements else 0,
        }
        for s in specs
    ]


@router.post("/check-submittal")
async def check_submittal(
    equipment_tag: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger the Compliance Agent to check a vendor submittal against specifications.
    This starts the multi-agent reasoning cascade.
    """
    from app.services.compliance_service import compliance_service
    res = await compliance_service.check_submittal(equipment_tag, db)
    if "status" in res and res["status"] == "error":
        raise HTTPException(status_code=404, detail=res["message"])
    return res
