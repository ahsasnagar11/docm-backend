import ssl
from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")

celery_app = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    broker_use_ssl={"ssl_cert_reqs": ssl.CERT_NONE},
    redis_backend_use_ssl={"ssl_cert_reqs": ssl.CERT_NONE},
)

@celery_app.task(name="process_document")
def process_document(document_id: str, org_id: str):
    from app.database import SessionLocal
    from app.models.document import Document, DocumentStatus, SourceType
    from app.models.chunk import Chunk
    from app.services.ingestion.pdf_service import extract_pdf
    from app.services.ingestion.url_service import extract_url
    from app.services.ingestion.youtube_service import extract_youtube
    from app.services.ingestion.chunking_service import recursive_chunk
    from app.services.rag.embed_service import embed_texts
    from app.config import settings
    from supabase import create_client
    import tempfile

    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return

        doc.status = DocumentStatus.processing
        db.commit()

        pages = []

        if doc.source_type == SourceType.pdf:
            # Supabase se PDF bytes download karo
            supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            file_bytes = supabase.storage.from_(settings.SUPABASE_BUCKET).download(doc.storage_path)

            # Temp file mein likho taaki pdfplumber kaam kar sake
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name

            pages = extract_pdf(tmp_path)

            # Temp file clean up karo
            os.remove(tmp_path)

        elif doc.source_type == SourceType.url:
            text = extract_url(doc.source_url)
            pages = [(text, None)]
        elif doc.source_type == SourceType.youtube:
            text = extract_youtube(doc.source_url)
            pages = [(text, None)]
        elif doc.source_type == SourceType.text:
            pages = [(doc.source_url, None)]

        all_chunks = []
        for text, page_num in pages:
            chunks = recursive_chunk(text)
            for chunk in chunks:
                all_chunks.append((chunk, page_num))

        texts = [c[0] for c in all_chunks]
        embeddings = embed_texts(texts)

        for idx, ((chunk_text, page_num), embedding) in enumerate(zip(all_chunks, embeddings)):
            chunk = Chunk(
                document_id=doc.id,
                org_id=org_id,
                content=chunk_text,
                embedding=embedding,
                chunk_index=idx,
                page_number=page_num,
                token_count=len(chunk_text.split())
            )
            db.add(chunk)

        doc.status = DocumentStatus.ready
        db.commit()

    except Exception as e:
        doc.status = DocumentStatus.failed
        db.commit()
        raise e
    finally:
        db.close()