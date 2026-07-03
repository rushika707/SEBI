import logging
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.services.vector_service import vector_service
from app.services.graph_service import graph_service
from app.models.models import Clause
from app.schemas.schemas import RAGQueryResponse, RAGCitation
from app.core.config import settings

logger = logging.getLogger("sebi_copilot.rag_service")

class RAGService:
    def keyword_search(self, db: Session, query: str, limit: int = 5) -> List[Clause]:
        # Simple SQL case-insensitive substring search for clauses
        words = query.split()
        if not words:
            return []
        
        # Build keyword filter
        clauses = db.query(Clause)
        for word in words[:3]:  # Filter by first few keywords
            clauses = clauses.filter(Clause.content.ilike(f"%{word}%"))
        
        return clauses.limit(limit).all()

    def query(self, db: Session, query_text: str, top_k: int = 5) -> RAGQueryResponse:
        logger.info(f"RAG query received: '{query_text}'")

        # 1. Semantic Search
        semantic_hits = vector_service.search_similar_clauses(query_text, top_k=top_k)
        
        # 2. Keyword Search
        keyword_hits = self.keyword_search(db, query_text, limit=top_k)

        # Merge results, prioritizing semantic hits but filling in unique keyword hits
        seen_clause_ids = set()
        citations: List[RAGCitation] = []
        context_texts = []

        # Process vector matches
        for hit in semantic_hits:
            payload = hit["payload"]
            cid = payload["clause_id"]
            seen_clause_ids.add(cid)
            
            # Fetch relational metadata from graph service for this clause
            graph_context = ""
            try:
                graph_data = graph_service.get_downstream_impact(f"clause_{cid}")
                if graph_data:
                    depts = [n["properties"].get("name") for n in graph_data if n["label"] == "Department"]
                    if depts:
                        graph_context = f" (Responsible departments: {', '.join(depts)})"
            except Exception:
                pass

            citations.append(RAGCitation(
                document_id=payload["document_id"],
                document_title=payload.get("title", "SEBI Circular"),
                clause_number=payload["clause_number"],
                content=payload["content"],
                confidence=float(hit["score"]),
                reasoning=f"Identified via vector semantic search with cosine score {hit['score']:.4f}{graph_context}."
            ))
            context_texts.append(f"Document: {payload.get('title')} | Clause: {payload['clause_number']}\nContent: {payload['content']}{graph_context}")

        # Process keyword matches that weren't captured by vector search
        for c in keyword_hits:
            if c.id not in seen_clause_ids:
                seen_clause_ids.add(c.id)
                citations.append(RAGCitation(
                    document_id=c.document_id,
                    document_title=c.document.title if c.document else "SEBI Document",
                    clause_number=c.clause_number,
                    content=c.content,
                    confidence=0.65,
                    reasoning="Identified via keyword match in relational database."
                ))
                context_texts.append(f"Document: {c.document.title if c.document else 'SEBI'} | Clause: {c.clause_number}\nContent: {c.content}")

        # 3. Formulate prompt for LLM
        context_block = "\n\n---\n\n".join(context_texts)
        system_prompt = (
            "You are SEBI CoPilot, an Agentic AI Compliance Operating System. Your goal is to answer compliance queries based on the provided SEBI clauses.\n"
            "Provide a precise, comprehensive, and audit-ready response. DO NOT hallucinate. Quote details directly.\n"
            "If the information is not in the context, clearly state that there is insufficient data in the ingested SEBI circulars.\n\n"
            "Context from SEBI circulars:\n"
            f"{context_block}"
        )

        answer = ""
        confidence_score = 0.85

        # 4. Generate LLM Output
        if settings.OPENAI_API_KEY:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                completion = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query_text}
                    ]
                )
                answer = completion.choices[0].message.content
                confidence_score = 0.95
            except Exception as e:
                logger.error(f"OpenAI completion failed: {e}")

        if not answer and settings.GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model = genai.GenerativeModel("gemini-1.5-flash")
                resp = model.generate_content(
                    contents=f"{system_prompt}\n\nUser Query: {query_text}"
                )
                answer = resp.text
                confidence_score = 0.95
            except Exception as e:
                logger.error(f"Gemini generation failed: {e}")

        if not answer:
            # Simple offline procedural generator if no LLM key is configured
            if citations:
                answer = "### Ingested SEBI Regulation Summary\n\nBased on your query, here are the direct regulatory matches extracted from SEBI documents:\n\n"
                for cite in citations:
                    answer += f"**{cite.document_title} (Clause {cite.clause_number}):**\n> {cite.content[:200]}...\n\n"
                answer += "\n*(Configure GEMINI_API_KEY or OPENAI_API_KEY in .env to enable detailed generative explainability and advice.)*"
                confidence_score = 0.70
            else:
                answer = "No matching regulatory clauses were found in the database. Please upload the relevant SEBI Circular first."
                confidence_score = 0.0

        return RAGQueryResponse(
            answer=answer,
            citations=citations,
            confidence_score=confidence_score
        )

rag_service = RAGService()
