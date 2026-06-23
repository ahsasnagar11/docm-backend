from groq import Groq
from app.config import settings
from typing import List

client = Groq(api_key=settings.GROQ_API_KEY)

def expand_query(question: str) -> List[str]:
    prompt = f"""You are a query expansion assistant. Given a user question, generate 3 different ways to phrase the same question to improve search results. Return ONLY the 3 rephrased questions, one per line, no numbering, no extra text.

Question: {question}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=200
    )

    content = response.choices[0].message.content.strip()
    variations = [line.strip() for line in content.split("\n") if line.strip()]
    all_queries = [question] + variations[:3]
    return all_queries
