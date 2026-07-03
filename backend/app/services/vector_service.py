import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from app.core.config import settings

logger = logging.getLogger("sebi_copilot.vector_service")

class VectorService:
    def __init__(self):
        self.collection_name = "sebi_clauses"
        self.client = None
        self.fallback_mode = False
        self.in_memory_db = []  # Fallback in-memory database
        
        try:
            # Try connecting to Qdrant
            logger.info(f"Attempting to connect to Qdrant at {settings.QDRANT_URL}")
            self.client = QdrantClient(url=settings.QDRANT_URL, timeout=3.0)
            # Query collections to check connectivity
            self.client.get_collections()
            self.init_collection()
            logger.info("Successfully connected to Qdrant.")
        except Exception as e:
            logger.warning(f"Qdrant connection failed: {e}. Switching to IN-MEMORY fallback.")
            self.client = None
            self.fallback_mode = True

    def init_collection(self):
        try:
            # We'll use 768 dimensions for Gemini embeddings, or 1536 for OpenAI.
            # Defaulting to 1536 since it's the standard for OpenAI, but we can configure.
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            
            if not exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error initializing Qdrant collection: {e}")
            self.fallback_mode = True

    def _get_mock_embedding(self, text: str) -> List[float]:
        # Simple deterministic hashing to create a mock vector of size 1536
        # for local offline testing if no LLM API key is configured.
        import hashlib
        vector = []
        for i in range(1536):
            h = hashlib.md5(f"{text}_{i}".encode('utf-8')).hexdigest()
            # Convert hash to float between -1 and 1
            val = (int(h[:8], 16) / 4294967295.0) * 2 - 1
            vector.append(val)
        return vector

    def get_embedding(self, text: str) -> List[float]:
        # Generate embedding using OpenAI or Gemini if keys are available, otherwise mock
        if settings.OPENAI_API_KEY:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                resp = client.embeddings.create(input=[text], model="text-embedding-3-small")
                return resp.data[0].embedding
            except Exception as e:
                logger.error(f"OpenAI embedding error: {e}")
        
        if settings.GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                resp = genai.embed_content(
                    model="models/text-embedding-004",
                    contents=text,
                    task_type="retrieval_document"
                )
                # Gemini text-embedding-004 is 768 dimensions by default.
                # Pad to 1536 if needed or use as is.
                emb = resp['embedding']
                if len(emb) < 1536:
                    emb = emb + [0.0] * (1536 - len(emb))
                return emb[:1536]
            except Exception as e:
                logger.error(f"Gemini embedding error: {e}")

        # Fallback to mock embedding
        return self._get_mock_embedding(text)

    def upsert_clause(self, clause_id: int, document_id: int, clause_number: str, text: str, title: Optional[str] = None):
        vector = self.get_embedding(text)
        payload = {
            "clause_id": clause_id,
            "document_id": document_id,
            "clause_number": clause_number,
            "title": title or "",
            "content": text
        }
        
        if self.fallback_mode or not self.client:
            self.in_memory_db.append({
                "id": clause_id,
                "vector": vector,
                "payload": payload
            })
            logger.info(f"Upserted clause {clause_id} to in-memory store.")
            return

        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=clause_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
            logger.info(f"Upserted clause {clause_id} to Qdrant.")
        except Exception as e:
            logger.error(f"Qdrant upsert failed: {e}. Saving to in-memory store.")
            self.in_memory_db.append({
                "id": clause_id,
                "vector": vector,
                "payload": payload
            })

    def search_similar_clauses(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        query_vector = self.get_embedding(query)
        
        if self.fallback_mode or not self.client:
            # Local cosine similarity search
            import math
            results = []
            for item in self.in_memory_db:
                v1 = item["vector"]
                v2 = query_vector
                
                # Cosine similarity
                dot_product = sum(a * b for a, b in zip(v1, v2))
                norm_a = math.sqrt(sum(a * a for a in v1))
                norm_b = math.sqrt(sum(b * b for b in v2))
                
                if norm_a == 0 or norm_b == 0:
                    similarity = 0
                else:
                    similarity = dot_product / (norm_a * norm_b)
                
                results.append({
                    "score": similarity,
                    "payload": item["payload"]
                })
            
            # Sort by score desc
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:top_k]

        try:
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k
            )
            return [{"score": hit.score, "payload": hit.payload} for hit in search_result]
        except Exception as e:
            logger.error(f"Qdrant search failed: {e}. Falling back to keyword-based search on in-memory store.")
            # Basic term-matching fallback if Qdrant search crashes
            results = []
            query_words = set(query.lower().split())
            for item in self.in_memory_db:
                content = item["payload"]["content"].lower()
                matches = sum(1 for w in query_words if w in content)
                score = matches / max(1, len(query_words))
                results.append({
                    "score": score,
                    "payload": item["payload"]
                })
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:top_k]

# Global instance
vector_service = VectorService()
