"""
DCBrain Supply Chain API Routes
Endpoints for shipment tracking, vendor management, and alternative sourcing.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Shipment, Vendor, Equipment
from app.graph.neo4j_client import graph_client


router = APIRouter()


@router.get("/shipments")
async def list_shipments(
    status: Optional[str] = Query(None, description="Filter by status: in_transit, customs_hold, delivered, delayed"),
    db: AsyncSession = Depends(get_db),
):
    """List all shipments with optional status filter."""
    query = select(Shipment)
    if status:
        query = query.where(Shipment.status == status)
    query = query.order_by(Shipment.expected_arrival)

    result = await db.execute(query)
    shipments = result.scalars().all()

    return [
        {
            "id": str(s.id),
            "tracking_id": s.tracking_id,
            "description": s.description,
            "status": s.status,
            "origin_city": s.origin_city,
            "origin_country": s.origin_country,
            "current_location": s.current_location,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "expected_arrival": s.expected_arrival.isoformat() if s.expected_arrival else None,
            "delay_days": s.delay_days,
            "risk_score": s.risk_score,
            "risk_factors": s.risk_factors or [],
            "equipment_id": str(s.equipment_id) if s.equipment_id else None,
            "purchase_order_id": str(s.purchase_order_id) if s.purchase_order_id else None,
            "vendor_id": str(s.vendor_id) if s.vendor_id else None,
            "ai_alternatives": s.ai_alternatives or [],
            "ai_impact_analysis": s.ai_impact_analysis or {},
        }
        for s in shipments
    ]


@router.get("/shipments/{tracking_id}")
async def get_shipment_detail(tracking_id: str, db: AsyncSession = Depends(get_db)):
    """Get full shipment detail with vendor and equipment links."""
    result = await db.execute(
        select(Shipment).where(Shipment.tracking_id == tracking_id)
    )
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Shipment {tracking_id} not found")

    # Get linked vendor
    vendor_info = None
    if shipment.vendor_id:
        vendor_res = await db.execute(select(Vendor).where(Vendor.id == shipment.vendor_id))
        vendor = vendor_res.scalar_one_or_none()
        if vendor:
            vendor_info = {
                "name": vendor.name,
                "code": vendor.code,
                "reliability_score": vendor.reliability_score,
                "on_time_delivery_rate": vendor.on_time_delivery_rate,
            }

    # Get linked equipment
    equipment_info = None
    if shipment.equipment_id:
        eq_res = await db.execute(select(Equipment).where(Equipment.id == shipment.equipment_id))
        eq = eq_res.scalar_one_or_none()
        if eq:
            equipment_info = {
                "tag": eq.tag,
                "name": eq.name,
                "category": eq.category,
                "status": eq.status.value,
            }

    return {
        "id": str(shipment.id),
        "tracking_id": shipment.tracking_id,
        "description": shipment.description,
        "status": shipment.status,
        "origin_city": shipment.origin_city,
        "origin_country": shipment.origin_country,
        "current_location": shipment.current_location,
        "latitude": shipment.latitude,
        "longitude": shipment.longitude,
        "expected_arrival": shipment.expected_arrival.isoformat() if shipment.expected_arrival else None,
        "delay_days": shipment.delay_days,
        "risk_score": shipment.risk_score,
        "risk_factors": shipment.risk_factors or [],
        "ai_alternatives": shipment.ai_alternatives or [],
        "ai_impact_analysis": shipment.ai_impact_analysis or {},
        "vendor": vendor_info,
        "equipment": equipment_info,
    }


@router.get("/vendors")
async def list_vendors(db: AsyncSession = Depends(get_db)):
    """List all vendors with reliability scores."""
    result = await db.execute(select(Vendor).order_by(Vendor.reliability_score.desc()))
    vendors = result.scalars().all()

    return [
        {
            "id": str(v.id),
            "name": v.name,
            "code": v.code,
            "category": v.category,
            "reliability_score": v.reliability_score,
            "on_time_delivery_rate": v.on_time_delivery_rate,
            "contact_email": v.contact_email,
        }
        for v in vendors
    ]


@router.get("/vendors/{vendor_code}")
async def get_vendor_profile(vendor_code: str, db: AsyncSession = Depends(get_db)):
    """Get vendor profile with equipment history from knowledge graph."""
    # Try graph client first for rich context
    graph_profile = await graph_client.get_vendor_profile(vendor_code)
    if graph_profile:
        return graph_profile

    # Fallback to SQL
    result = await db.execute(
        select(Vendor).where(Vendor.code == vendor_code)
    )
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail=f"Vendor {vendor_code} not found")

    # Get equipment supplied by this vendor
    eq_result = await db.execute(
        select(Equipment).where(Equipment.vendor_id == vendor.id)
    )
    equipment = eq_result.scalars().all()

    return {
        "v": {
            "name": vendor.name,
            "code": vendor.code,
            "category": vendor.category,
            "reliability_score": vendor.reliability_score,
            "on_time_delivery_rate": vendor.on_time_delivery_rate,
            "contact_email": vendor.contact_email,
        },
        "equipment": [
            {"tag": eq.tag, "category": eq.category, "status": eq.status.value}
            for eq in equipment
        ],
    }


@router.get("/alternatives/{equipment_tag}")
async def find_alternative_vendors(equipment_tag: str):
    """Find alternative vendors for equipment replacement using the knowledge graph."""
    alternatives = await graph_client.find_alternative_vendors(equipment_tag)
    return {"equipment_tag": equipment_tag, "alternatives": alternatives}
