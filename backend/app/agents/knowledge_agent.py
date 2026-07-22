"""
DCBrain Knowledge Agent — Cascade Event Handler
Reacts to NCR events by finding similar precedent RFIs in the knowledge graph,
and to test failures by searching for relevant reference documentation.
"""

import asyncio
from datetime import datetime

from app.core.llm import gemini_client
from app.graph.neo4j_client import graph_client
from app.core.dependencies import get_chroma_client
from app.agents.cascade_bus import cascade_bus, CascadeEventPayload
from pydantic import BaseModel, Field
from typing import List, Optional


class PrecedentAnalysisSchema(BaseModel):
    has_precedent: bool = Field(description="True if a relevant precedent was found")
    precedent_summary: str = Field(description="Summary of the identified precedent and its resolution")
    applicable_resolution: str = Field(description="How the past resolution can be applied to the current situation")
    confidence: float = Field(description="Confidence score 0.0-1.0 that this precedent is applicable")
    time_saved_hours: float = Field(description="Estimated time saved by applying this precedent vs. researching from scratch")


SYSTEM_PROMPT_NCR = """
You are the DCBrain Knowledge Agent. When an NCR is raised, you search the project knowledge base
for historical precedents — similar RFIs, past resolutions, and applicable lessons learned.

Your job is to:
1. Identify if a similar issue has been resolved before (same equipment type, same deviation type).
2. Summarize the precedent resolution in actionable terms.
3. Estimate the confidence that this resolution applies to the current NCR.
4. Estimate time saved by reusing this knowledge vs. starting from scratch.
"""

SYSTEM_PROMPT_TEST = """
You are the DCBrain Knowledge Agent. When a commissioning test fails, you search the project
knowledge base for relevant technical references, standards, and past diagnoses.

Your job is to:
1. Find relevant specification sections, standards, or past test results.
2. Summarize the applicable reference material.
3. Highlight any lessons learned from similar test failures.
"""


class KnowledgeAgent:
    """Cascade handler for the Knowledge Agent — finds precedents and references."""

    async def handle_ncr_raised(self, event: CascadeEventPayload):
        """Called when an NCR is raised. Searches for similar precedent RFIs."""
        ncr_number = event.entity_id
        equipment_tag = event.details.get("equipment_tag", "Unknown")
        print(f"💬 KnowledgeAgent: Searching knowledge base for precedents to {ncr_number}...")

        # 1. Search graph for similar RFIs
        similar_rfis = await graph_client.find_similar_rfis("RFI-047")

        # 2. Search ChromaDB for related document chunks
        doc_context = []
        try:
            chroma = get_chroma_client()
            collection = chroma.get_collection("dcbrain_documents")
            spec_text = event.details.get("expected_voltage", "") or event.details.get("specification", "")
            search_query = f"voltage mismatch {equipment_tag} {spec_text}"

            results = collection.query(
                query_texts=[search_query],
                n_results=3,
            )
            if results and results.get("documents") and len(results["documents"][0]) > 0:
                for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
                    doc_context.append({
                        "doc_code": meta.get("doc_code"),
                        "file_name": meta.get("file_name"),
                        "section": meta.get("section"),
                        "text": doc[:200]
                    })
        except Exception as e:
            print(f"⚠️ KnowledgeAgent: ChromaDB search failed: {e}")

        # 3. Invoke Gemini to analyze precedent applicability
        rfi_context = "\n".join([
            f"- {r.get('rfi_number')}: {r.get('subject')} → Resolution: {r.get('answer', 'N/A')}"
            for r in similar_rfis
        ]) if similar_rfis else "No similar RFIs found in graph."

        doc_text = "\n".join([
            f"- [{d['doc_code']}] Section {d['section']}: {d['text']}"
            for d in doc_context
        ]) if doc_context else "No relevant document chunks found."

        prompt = f"""
        === CURRENT NCR ===
        NCR: {ncr_number}
        Equipment: {equipment_tag}
        Deviation: {event.details.get('actual_voltage', 'Unknown')} vs expected {event.details.get('expected_voltage', 'Unknown')}
        Specification: {event.details.get('specification', 'Unknown')}

        === SIMILAR RFIs FROM KNOWLEDGE GRAPH ===
        {rfi_context}

        === RELEVANT DOCUMENT CHUNKS ===
        {doc_text}

        Analyze whether any precedent resolution applies to this NCR.
        """

        result: PrecedentAnalysisSchema = await gemini_client.generate_structured(
            prompt=prompt,
            schema=PrecedentAnalysisSchema,
            system_instruction=SYSTEM_PROMPT_NCR
        )

        # Publish precedent event
        evt = CascadeEventPayload(
            source_agent="knowledge",
            event_type="precedent_found" if result.has_precedent else "no_precedent_found",
            entity_type="rfi",
            entity_id="RFI-047" if result.has_precedent else ncr_number,
            summary=f"Knowledge Agent: {'Found applicable precedent — ' + result.precedent_summary[:80] if result.has_precedent else 'No direct precedent found. Manual investigation recommended.'}",
            details={
                "ncr_number": ncr_number,
                "equipment_tag": equipment_tag,
                "has_precedent": result.has_precedent,
                "precedent_summary": result.precedent_summary,
                "applicable_resolution": result.applicable_resolution,
                "confidence": result.confidence,
                "time_saved_hours": result.time_saved_hours,
                "similar_rfis": [r.get("rfi_number") for r in similar_rfis] if similar_rfis else [],
                "document_references": [d["doc_code"] for d in doc_context],
            },
            explainability={
                "precedent_analysis": result.precedent_summary,
                "resolution_applicability": result.applicable_resolution,
                "confidence": result.confidence,
                "sources_consulted": len(similar_rfis) + len(doc_context),
            },
            trace_id=event.trace_id,
            severity="info"
        )
        await cascade_bus.publish(evt)

    async def handle_test_failed(self, event: CascadeEventPayload):
        """Called when a commissioning test fails. Searches for relevant references."""
        test_code = event.entity_id
        print(f"💬 KnowledgeAgent: Searching references for failed test {test_code}...")

        # Search ChromaDB for relevant standard references
        doc_references = []
        try:
            chroma = get_chroma_client()
            collection = chroma.get_collection("dcbrain_documents")
            diagnosis = event.explainability.get("diagnosis", "")
            search_query = f"{test_code} commissioning test failure {diagnosis}"

            results = collection.query(
                query_texts=[search_query],
                n_results=2,
            )
            if results and results.get("documents") and len(results["documents"][0]) > 0:
                for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
                    doc_references.append({
                        "doc_code": meta.get("doc_code"),
                        "file_name": meta.get("file_name"),
                        "section": meta.get("section"),
                        "text": doc[:150],
                    })
        except Exception as e:
            print(f"⚠️ KnowledgeAgent: ChromaDB search failed: {e}")

        # Publish reference found event
        evt = CascadeEventPayload(
            source_agent="knowledge",
            event_type="knowledge_reference_found",
            entity_type="commissioning_test",
            entity_id=test_code,
            summary=f"Knowledge Agent: Found {len(doc_references)} reference document(s) for test {test_code} failure analysis.",
            details={
                "test_code": test_code,
                "references_found": len(doc_references),
                "documents": doc_references,
            },
            explainability={
                "search_query": f"Searched for: {test_code} commissioning failure",
                "sources_found": len(doc_references),
            },
            trace_id=event.trace_id,
            severity="info"
        )
        await cascade_bus.publish(evt)


# Singleton agent
knowledge_agent = KnowledgeAgent()
