# DOCm

**Ask questions. Get answers. From your own documents.**

DOCm is a multi-tenant SaaS platform where companies upload their documents and employees ask questions in plain English — and get accurate answers with exact source citations. No hallucinations. No guessing. Every answer is grounded in your actual content.

 **Live demo:** [docm-frontend.vercel.app](https://docm-frontend.vercel.app)

---

## What It Does

Upload any document — PDF, URL, YouTube video, or plain text. Then ask anything about it.

DOCm finds the most relevant passages, re-ranks them for accuracy, and generates a cited answer in real time. Sources are shown so you always know exactly where the answer came from.

---

## Features

- **Multi-format ingestion** — PDF, web URLs, YouTube transcripts, plain text
- **Semantic + keyword search** — finds answers even when the exact words don't match
- **AI reranking** — Cohere rerank model scores every result for true relevance before generating
- **Query expansion** — your question is automatically rephrased 3 ways to maximize retrieval coverage
- **Streaming answers** — responses appear word by word in real time
- **Source citations** — every answer references the exact chunk and page number it came from
- **Conversation memory** — the assistant remembers your last 6 messages for follow-up questions
- **Multi-tenant isolation** — each organization's data is completely separate
- **JWT auth** — access tokens + refresh tokens, no sessions

---

## How It Works

```
You ask a question
        ↓
Question is rephrased 3 ways (query expansion)
        ↓
Semantic search + keyword search run on your documents
        ↓
Top results re-ranked by Cohere for true relevance
        ↓
Groq LLM generates a cited answer from the best chunks
        ↓
Answer streams to you in real time
```

Document ingestion runs in the background via a Celery worker — upload a PDF, get a response immediately, and it's ready to query within seconds.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python + FastAPI |
| Database | PostgreSQL + pgvector (Supabase) |
| LLM | Groq — Llama 3.3 70B |
| Embeddings | Cohere Embed v3.0 (1024-dim vectors) |
| Reranking | Cohere Rerank API |
| Background jobs | Celery + Upstash Redis |
| Auth | JWT (access + refresh tokens) |
| Frontend | React + Vite + Tailwind CSS |
| Deployment | Render (backend + worker) + Vercel (frontend) |

---

## Running Locally

### 1. Clone the repos

```bash
git clone https://github.com/ahsasnagar11/docm-backend
git clone https://github.com/ahsasnagar11/docm-frontend
```

### 2. Backend

```bash
cd docm-backend
python -m venv venv
venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

Create `backend/.env`:

```
DATABASE_URL=your_supabase_session_pooler_url
JWT_SECRET=your_secret
GROQ_API_KEY=your_key
COHERE_API_KEY=your_key
REDIS_URL=rediss://your_upstash_url
```

```bash
uvicorn main:app --reload
```

### 3. Celery Worker (separate terminal)

```bash
cd docm-backend
venv\Scripts\activate
celery -A app.celery.tasks worker --loglevel=info -P solo
```

### 4. Frontend (separate terminal)

```bash
cd docm-frontend
npm install
npm run dev
```
