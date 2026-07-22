"""
DCBrain API — Knowledge & RFI Intelligence Agent
Chat endpoint, document search, RFI management.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models import RFI, RFIStatus, ProjectDocument

router = APIRouter()


class ChatRequest(BaseModel):
    """Chat request payload."""
    message: str
    conversation_id: str = "default"


class ChatResponse(BaseModel):
    """Chat response with citations."""
    answer: str
    citations: list = []
    graph_path: list = []
    time_saved_hours: float = 0.0
    similar_rfis: list = []


@router.post("/chat", response_model=ChatResponse)
async def chat_with_knowledge_agent(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Chat with the Knowledge Agent using Graph RAG.
    Queries Knowledge Graph first, then vector store, merges results.
    """
    from app.rag.graph_rag import graph_rag
    from app.graph.neo4j_client import graph_client
    
    # Run Graph RAG
    rag_result = await graph_rag.query(request.message)
    
    # Sourced similar precedents
    similar_rfis = []
    if "ups" in request.message.lower() or "ncr" in request.message.lower():
        # Sourced RFI-047 as the voltage mismatch swap precedent
        similar_rfis = await graph_client.find_similar_rfis("RFI-047")
        
    return ChatResponse(
        answer=rag_result["answer"],
        citations=rag_result["citations"],
        graph_path=rag_result["graph_path"],
        time_saved_hours=rag_result["time_saved_hours"],
        similar_rfis=[
            {
                "rfi_number": r.get("rfi_number"),
                "subject": r.get("subject"),
                "answer": r.get("answer"),
                "answered_date": r.get("answered_date")
            }
            for r in similar_rfis
        ]
    )


@router.get("/rfis")
async def list_rfis(
    status: str = None,
    db: AsyncSession = Depends(get_db),
):
    """List all RFIs with optional status filtering."""
    query = select(RFI).order_by(RFI.raised_date.desc())
    if status:
        query = query.where(RFI.status == status)

    result = await db.execute(query)
    rfis = result.scalars().all()

    return [
        {
            "id": str(r.id),
            "rfi_number": r.rfi_number,
            "subject": r.subject,
            "question": r.question[:200] + "..." if len(r.question) > 200 else r.question,
            "status": r.status.value,
            "priority": r.priority.value,
            "category": r.category,
            "raised_by": r.raised_by,
            "assigned_to": r.assigned_to,
            "raised_date": r.raised_date.isoformat() if r.raised_date else None,
            "due_date": r.due_date.isoformat() if r.due_date else None,
            "similar_rfis": r.similar_rfis,
        }
        for r in rfis
    ]


@router.get("/rfis/{rfi_number}")
async def get_rfi_detail(rfi_number: str, db: AsyncSession = Depends(get_db)):
    """Get detailed RFI with AI-suggested answer and similar RFIs."""
    result = await db.execute(
        select(RFI).where(RFI.rfi_number == rfi_number)
    )
    rfi = result.scalar_one_or_none()
    if not rfi:
        raise HTTPException(status_code=404, detail=f"RFI {rfi_number} not found")

    return {
        "id": str(rfi.id),
        "rfi_number": rfi.rfi_number,
        "subject": rfi.subject,
        "question": rfi.question,
        "answer": rfi.answer,
        "status": rfi.status.value,
        "priority": rfi.priority.value,
        "category": rfi.category,
        "discipline": rfi.discipline,
        "raised_by": rfi.raised_by,
        "assigned_to": rfi.assigned_to,
        "raised_date": rfi.raised_date.isoformat() if rfi.raised_date else None,
        "due_date": rfi.due_date.isoformat() if rfi.due_date else None,
        "answered_date": rfi.answered_date.isoformat() if rfi.answered_date else None,
        "similar_rfis": rfi.similar_rfis,
        "ai_suggested_answer": rfi.ai_suggested_answer,
        "resolution_time_hours": rfi.resolution_time_hours,
    }


@router.get("/documents")
async def list_documents(
    doc_type: str = None,
    db: AsyncSession = Depends(get_db),
):
    """List all project documents in the knowledge base."""
    query = select(ProjectDocument).order_by(ProjectDocument.doc_code)
    if doc_type:
        query = query.where(ProjectDocument.doc_type == doc_type)

    result = await db.execute(query)
    docs = result.scalars().all()

    return [
        {
            "id": str(d.id),
            "doc_code": d.doc_code,
            "title": d.title,
            "doc_type": d.doc_type,
            "category": d.category,
            "file_name": d.file_name,
            "chunk_count": d.chunk_count,
            "is_indexed": d.is_indexed,
        }
        for d in docs
    ]
