import cohere
from app.config import settings
from typing import List

co = cohere.Client(settings.COHERE_API_KEY)

def rerank(query: str, chunks: List[dict], top_n: int = 5) -> List[dict]:
    if not chunks:
        return []

    documents = [c["content"] for c in chunks]

    response = co.rerank(
        model="rerank-english-v3.0",
        query=query,
        documents=documents,
        top_n=top_n
    )

    reranked = []
    for result in response.results:
        chunk = chunks[result.index]
        chunk["relevance_score"] = result.relevance_score
        reranked.append(chunk)

    return reranked
