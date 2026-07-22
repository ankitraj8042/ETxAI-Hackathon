"""
DCBrain Graph RAG Pipeline
Combines Neo4j relationship reasoning with ChromaDB semantic vector search.
"""

from typing import Dict, Any, List, Optional
import json

from app.core.llm import gemini_client
from app.graph.neo4j_client import graph_client
from app.core.dependencies import get_chroma_client

from pydantic import BaseModel, Field


class Citation(BaseModel):
    doc_code: str = Field(description="Document code/identifier, e.g., DC-ALPHA-SPEC-ELEC")
    file_name: str = Field(description="File name of the document, e.g., DC-Alpha-Electrical-Spec-v3.pdf")
    page: int = Field(description="Page number of the reference")
    section: str = Field(description="Section of the reference, e.g., 4.3.2")
    quote: str = Field(description="Exact quote or summary from the document chunk")


class GraphRAGResponseSchema(BaseModel):
    answer: str = Field(description="Detailed narrative answer addressing the query")
    citations: List[Citation] = Field(default=[], description="List of document citations supporting the answer")
    graph_path: List[str] = Field(default=[], description="Relationship path traversed, e.g., ['UPS-2', 'RAISED_AGAINST', 'NCR-023']")
    time_saved_hours: float = Field(default=0.5, description="Estimated time saved in hours compared to manual research")


SYSTEM_INSTRUCTION = """
You are the DCBrain Project Knowledge Agent. You answer technical and contractual queries about data centre EPC projects.
You are provided with:
1. GRAPH CONTEXT: Structured relationships retrieved from the Project Knowledge Graph.
2. DOCUMENT CHUNKS: Semantic text snippets retrieved from project specifications, submittals, and RFIs.

Use BOTH sources to form your answer.
In your response, provide:
- A detailed, clear answer based on the facts provided.
- Accurately map citations to the provided document chunks.
- Format the graph path as a list of strings representing nodes and relationship names in sequence, showing how the entities relate.
"""


class GraphRAGPipeline:
    """Graph-enhanced Retrieval-Augmented Generation pipeline."""

    async def query(self, user_query: str) -> Dict[str, Any]:
        """
        Runs Graph RAG:
        1. Query Knowledge Graph for structured relationships.
        2. Query ChromaDB for semantic document chunks.
        3. Merge contexts and invoke Gemini.
        """
        print(f"🔍 GraphRAG: Processing query: '{user_query}'")

        # ── Step 1: Query Knowledge Graph ─────────────────────────────
        graph_context = ""
        graph_paths = []
        
        # Simple entity matching: scan query for tags/codes in our database
        matched_entity = None
        for tag in ["UPS-2", "UPS-1", "GEN-1", "GEN-2", "SWG-1", "SWG-2", "CT-1", "CRAH-2", "NCR-023", "RFI-047"]:
            if tag.lower() in user_query.lower():
                matched_entity = tag
                break

        if matched_entity:
            print(f"  GraphRAG: Matched entity '{matched_entity}' in query")
            # Fetch subgraph or context
            ctx = await graph_client.get_equipment_context(matched_entity)
            if ctx:
                eq = ctx.get("e", {})
                zone = ctx.get("z", {})
                vendor = ctx.get("v", {})
                ncrs = ctx.get("ncrs", [])
                tests = ctx.get("tests", [])
                
                graph_context += f"Equipment: {eq.get('tag')} ({eq.get('name')}) is status '{eq.get('status')}'. "
                if zone:
                    graph_context += f"Located in Zone '{zone.get('name')}' (Tier {zone.get('tier_level')}). "
                if vendor:
                    graph_context += f"Supplied by Vendor '{vendor.get('name')}' (reliability: {vendor.get('reliability_score')}). "
                if ncrs:
                    graph_context += f"Open NCRs: {', '.join([n.get('ncr_number') for n in ncrs if n])}. "
                if tests:
                    graph_context += f"Commissioning tests associated: {', '.join([t.get('test_code') for t in tests if t])}. "
                
                # Format a default display path
                graph_paths = [eq.get("tag"), "INSTALLED_IN", zone.get("name") or "Power Room"]
                if ncrs:
                    graph_paths.extend(["←", ncrs[0].get("ncr_number"), "RAISED_AGAINST", eq.get("tag")])

        # ── Step 2: Query ChromaDB Vector Store ────────────────────────
        document_context = []
        
        try:
            chroma = get_chroma_client()
            collection = chroma.get_collection("dcbrain_documents")
            
            # Perform similarity search
            results = collection.query(
                query_texts=[user_query],
                n_results=3,
                where={"project": "dcbrain"}
            )
            
            if results and results.get("documents") and len(results["documents"][0]) > 0:
                docs = results["documents"][0]
                metas = results["metadatas"][0]
                
                for doc, meta in zip(docs, metas):
                    document_context.append({
                        "doc_code": meta.get("doc_code"),
                        "file_name": meta.get("file_name"),
                        "page": meta.get("page"),
                        "section": meta.get("section"),
                        "text": doc
                    })
        except Exception as e:
            print(f"⚠️ GraphRAG: ChromaDB query skipped or failed ({e})")

        # If ChromaDB was empty/failed, add a default fallback mock chunk for demo
        if not document_context and matched_entity == "UPS-2":
            document_context.append({
                "doc_code": "DC-ALPHA-SPEC-ELEC",
                "file_name": "DC-Alpha-Electrical-Spec-v3.pdf",
                "page": 47,
                "section": "4.3.2",
                "text": "SPEC-ELEC-001 Section 4.3.2: The uninterruptible power supply (UPS) systems shall supply a nominal output voltage of 400V AC, three-phase, 50Hz configuration. Output regulation must be within ±5%."
            })

        # ── Step 3: Construct Prompt and Invoke LLM ───────────────────
        
        # Build prompt string
        prompt = f"Query: {user_query}\n\n"
        prompt += f"=== GRAPH CONTEXT ===\n{graph_context or 'No structured graph relationships matched.'}\n\n"
        prompt += "=== DOCUMENT CHUNKS ===\n"
        if document_context:
            for idx, doc in enumerate(document_context):
                prompt += f"Chunk [{idx+1}]:\n"
                prompt += f"Source: {doc['file_name']} (Doc Code: {doc['doc_code']}) Page {doc['page']} Section {doc['section']}\n"
                prompt += f"Text: {doc['text']}\n\n"
        else:
            prompt += "No document context chunks retrieved.\n"

        prompt += "\nFormat output strictly matching the schema."

        # Trigger Gemini structured call
        result = await gemini_client.generate_structured(
            prompt=prompt,
            schema=GraphRAGResponseSchema,
            system_instruction=SYSTEM_INSTRUCTION
        )

        # Build clean dict output
        response_dict = {
            "answer": result.answer or "AI could not generate an answer due to mock fallback.",
            "citations": [
                {
                    "doc_code": c.doc_code,
                    "file_name": c.file_name,
                    "page": c.page,
                    "section": c.section,
                    "quote": c.quote
                }
                for c in result.citations
            ] if result.citations else [],
            "graph_path": result.graph_path or graph_paths,
            "time_saved_hours": result.time_saved_hours or 0.8
        }

        # If no citations were returned by mock model fallback, generate a clean default
        if not response_dict["citations"] and document_context:
            first_doc = document_context[0]
            response_dict["citations"].append({
                "doc_code": first_doc["doc_code"],
                "file_name": first_doc["file_name"],
                "page": first_doc["page"],
                "section": first_doc["section"],
                "quote": first_doc["text"]
            })

        return response_dict


# Singleton pipeline
graph_rag = GraphRAGPipeline()
