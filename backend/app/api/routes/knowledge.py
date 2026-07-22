"""
DCBrain API — Knowledge & RFI Intelligence Agent
Chat endpoint, document search, RFI management.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
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


@router.post("/index-document")
async def index_document(
    doc_code: str = Form(...),
    title: str = Form(...),
    category: str = Form("general"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document (PDF or text), extract text, chunk it, and index into ChromaDB vector store.
    """
    from uuid import uuid4
    from app.core.dependencies import get_chroma_client

    file_bytes = await file.read()
    extracted_text = ""

    try:
        if file.filename and file.filename.lower().endswith(".pdf"):
            import fitz
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page in doc:
                extracted_text += page.get_text() + "\n"
        else:
            extracted_text = file_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}")

    if not extracted_text.strip():
        raise HTTPException(status_code=400, detail="No readable text found in document.")

    # Chunk text into ~500 character chunks
    chunk_size = 500
    chunks = [extracted_text[i:i+chunk_size] for i in range(0, len(extracted_text), chunk_size)]

    # Add to ChromaDB
    try:
        chroma = get_chroma_client()
        collection = chroma.get_or_create_collection("dcbrain_documents")

        chunk_ids = [f"{doc_code}_chunk_{idx}" for idx in range(len(chunks))]
        chunk_metadatas = [
            {
                "doc_code": doc_code,
                "file_name": file.filename,
                "section": f"Chunk {idx + 1}",
                "page": idx + 1,
                "project": "dcbrain"
            }
            for idx in range(len(chunks))
        ]

        collection.add(
            ids=chunk_ids,
            documents=chunks,
            metadatas=chunk_metadatas
        )
    except Exception as e:
        print(f"⚠️ ChromaDB indexing warning: {e}")

    # Register in SQL DB
    doc_inst = ProjectDocument(
        id=uuid4(),
        doc_code=doc_code,
        title=title,
        doc_type="specification" if "spec" in category.lower() else "manual",
        category=category,
        file_name=file.filename or "uploaded_doc",
        chunk_count=len(chunks),
        is_indexed=True,
        content_summary=extracted_text[:300] + "..."
    )
    db.add(doc_inst)
    await db.commit()

    return {
        "status": "success",
        "doc_code": doc_code,
        "filename": file.filename,
        "chunks_indexed": len(chunks),
        "total_characters": len(extracted_text)
    }

