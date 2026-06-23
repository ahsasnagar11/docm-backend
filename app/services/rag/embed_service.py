import cohere
import os
from typing import List

co = cohere.Client(os.getenv("COHERE_API_KEY"))

def embed_texts(texts: List[str]) -> List[List[float]]:
    response = co.embed(
        texts=texts,
        model="embed-english-v3.0",
        input_type="search_document"
    )
    return response.embeddings

def embed_query(text: str) -> List[float]:
    response = co.embed(
        texts=[text],
        model="embed-english-v3.0",
        input_type="search_query"
    )
    return response.embeddings[0]