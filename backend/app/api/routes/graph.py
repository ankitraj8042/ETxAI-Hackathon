"""
DCBrain API — Knowledge Graph Visualization
Serves subgraph data for D3.js force-directed graph explorer.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.graph.neo4j_client import graph_client

router = APIRouter()


@router.get("/subgraph/{entity_tag}")
async def get_subgraph(entity_tag: str):
    """Get 2-degree subgraph around an entity for D3.js visualization."""
    data = await graph_client.get_subgraph(entity_tag)
    return data


@router.get("/critical-path")
async def get_critical_path():
    """Get all critical path tasks with dependencies."""
    tasks = await graph_client.get_critical_path()
    return tasks


@router.get("/impact/{equipment_tag}")
async def get_equipment_impact(equipment_tag: str):
    """Get downstream impact chain for equipment."""
    impact = await graph_client.get_equipment_impact_chain(equipment_tag)
    return impact


@router.get("/vendor/{vendor_code}")
async def get_vendor_profile(vendor_code: str):
    """Get vendor profile with equipment and NCR history."""
    profile = await graph_client.get_vendor_profile(vendor_code)
    return profile
