from groq import Groq
from app.config import settings
from typing import List, Generator

client = Groq(api_key=settings.GROQ_API_KEY)

def build_context(chunks: List[dict]) -> str:
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        page_info = f" (Page {chunk['page_number']})" if chunk.get('page_number') else ""
        context_parts.append(f"[Source {i}{page_info}]\n{chunk['content']}")
    return "\n\n".join(context_parts)

def generate_answer(question: str, chunks: List[dict], conversation_history: List[dict] = []) -> Generator:
    if not chunks:
        def no_context():
            yield "I could not find relevant information in the uploaded documents to answer your question."
        return no_context()

    context = build_context(chunks)

    system_prompt = """You are a helpful assistant that answers questions based strictly on the provided document context. 

Rules:
- Only use information from the provided context
- Always cite your sources using [Source N] notation
- If the context doesn't contain enough information, say so clearly
- Be concise and accurate
- Never make up information"""

    messages = [{"role": "system", "content": system_prompt}]
    messages += conversation_history[-6:]
    messages.append({
        "role": "user",
        "content": f"Context:\n{context}\n\nQuestion: {question}"
    })

    stream = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.1,
        max_tokens=1000,
        stream=True
    )

    return stream
