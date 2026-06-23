from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.user import User
from app.models.document import Document, SourceType, DocumentStatus
from app.middleware.auth_middleware import get_current_user
from app.celery.tasks import process_document
from app.config import settings
from supabase import create_client
import uuid

router = APIRouter(prefix="/documents", tags=["documents"])

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

@router.post("/upload/pdf")
def upload_pdf(
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    file_bytes = file.file.read()
    file_name = f"{uuid.uuid4()}_{file.filename}"

    supabase.storage.from_(settings.SUPABASE_BUCKET).upload(
        path=file_name,
        file=file_bytes,
        file_options={"content-type": "application/pdf"}
    )

    storage_path = file_name

    doc = Document(
        org_id=current_user.org_id,
        uploaded_by=current_user.id,
        title=title,
        source_type=SourceType.pdf,
        storage_path=storage_path,
        status=DocumentStatus.pending
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    process_document.delay(str(doc.id), str(current_user.org_id))

    return {"document_id": str(doc.id), "status": "processing"}


class URLRequest(BaseModel):
    title: str
    url: str
    source_type: str

@router.post("/upload/url")
def upload_url(
    req: URLRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    source_type = SourceType.youtube if "youtube" in req.url or "youtu.be" in req.url else SourceType.url

    doc = Document(
        org_id=current_user.org_id,
        uploaded_by=current_user.id,
        title=req.title,
        source_type=source_type,
        source_url=req.url,
        status=DocumentStatus.pending
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    process_document.delay(str(doc.id), str(current_user.org_id))

    return {"document_id": str(doc.id), "status": "processing"}


class TextRequest(BaseModel):
    title: str
    content: str

@router.post("/upload/text")
def upload_text(
    req: TextRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = Document(
        org_id=current_user.org_id,
        uploaded_by=current_user.id,
        title=req.title,
        source_type=SourceType.text,
        source_url=req.content,
        status=DocumentStatus.pending
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    process_document.delay(str(doc.id), str(current_user.org_id))

    return {"document_id": str(doc.id), "status": "processing"}


@router.get("/")
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    docs = db.query(Document).filter(Document.org_id == current_user.org_id).all()
    return [
        {
            "id": str(d.id),
            "title": d.title,
            "source_type": d.source_type,
            "status": d.status,
            "created_at": d.created_at
        }
        for d in docs
    ]

@router.get("/{document_id}")
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.org_id == current_user.org_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "id": str(doc.id),
        "title": doc.title,
        "source_type": doc.source_type,
        "status": doc.status,
        "created_at": doc.created_at
    }