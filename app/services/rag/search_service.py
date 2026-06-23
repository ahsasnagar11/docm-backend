from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.chunk import Chunk
from app.services.rag.embed_service import embed_texts, embed_query
from typing import List
import uuid

def vector_search(query: str, org_id: str, db: Session, top_k: int = 20) -> List[Chunk]:
    query_embedding = embed_query(query)
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    results = db.execute(text("""
        SELECT id, document_id, org_id, content, chunk_index, page_number, token_count,
               embedding <-> CAST(:embedding AS vector) AS distance
        FROM chunks
        WHERE org_id = CAST(:org_id AS uuid)
        ORDER BY distance ASC
        LIMIT :top_k
    """), {"embedding": embedding_str, "org_id": org_id, "top_k": top_k}).fetchall()

    return results

def keyword_search(query: str, org_id: str, db: Session, top_k: int = 20) -> List:
    results = db.execute(text("""
        SELECT id, document_id, org_id, content, chunk_index, page_number, token_count,
               ts_rank(to_tsvector('english', content), plainto_tsquery('english', :query)) AS rank
        FROM chunks
        WHERE org_id = CAST(:org_id AS uuid)
          AND to_tsvector('english', content) @@ plainto_tsquery('english', :query)
        ORDER BY rank DESC
        LIMIT :top_k
    """), {"query": query, "org_id": org_id, "top_k": top_k}).fetchall()

    return results

def hybrid_search(query: str, org_id: str, db: Session, top_k: int = 20) -> List[dict]:
    vector_results = vector_search(query, org_id, db, top_k)
    keyword_results = keyword_search(query, org_id, db, top_k)

    seen_ids = set()
    combined = []

    for row in vector_results:
        if row.id not in seen_ids:
            seen_ids.add(row.id)
            combined.append({
                "id": str(row.id),
                "document_id": str(row.document_id),
                "content": row.content,
                "chunk_index": row.chunk_index,
                "page_number": row.page_number,
                "token_count": row.token_count
            })

    for row in keyword_results:
        if row.id not in seen_ids:
            seen_ids.add(row.id)
            combined.append({
                "id": str(row.id),
                "document_id": str(row.document_id),
                "content": row.content,
                "chunk_index": row.chunk_index,
                "page_number": row.page_number,
                "token_count": row.token_count
            })

    return combined
