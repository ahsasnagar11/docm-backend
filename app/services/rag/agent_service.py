from sqlalchemy.orm import Session
from app.services.rag.search_service import hybrid_search
from app.services.rag.rerank_service import rerank
from app.services.rag.query_expansion_service import expand_query
from typing import List

MIN_RELEVANCE_SCORE = 0.3
MIN_CHUNKS_REQUIRED = 2

def retrieve(question: str, org_id: str, db: Session, max_attempts: int = 2) -> List[dict]:
    all_chunks = []
    seen_ids = set()

    queries = expand_query(question)

    for query in queries:
        results = hybrid_search(query, org_id, db, top_k=20)
        for chunk in results:
            if chunk["id"] not in seen_ids:
                seen_ids.add(chunk["id"])
                all_chunks.append(chunk)

    reranked = rerank(question, all_chunks, top_n=5)

    good_chunks = [c for c in reranked if c.get("relevance_score", 0) >= MIN_RELEVANCE_SCORE]

    if len(good_chunks) < MIN_CHUNKS_REQUIRED and max_attempts > 1:
        fallback_results = hybrid_search(question, org_id, db, top_k=30)
        fallback_chunks = []
        for chunk in fallback_results:
            if chunk["id"] not in seen_ids:
                seen_ids.add(chunk["id"])
                fallback_chunks.append(chunk)

        reranked = rerank(question, fallback_chunks, top_n=5)
        good_chunks = reranked

    return good_chunks if good_chunks else reranked
