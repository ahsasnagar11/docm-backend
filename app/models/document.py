import uuid
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
import enum

class SourceType(str, enum.Enum):
    pdf = "pdf"
    url = "url"
    youtube = "youtube"
    text = "text"

class DocumentStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    ready = "ready"
    failed = "failed"

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    source_type = Column(Enum(SourceType), nullable=False)
    source_url = Column(String, nullable=True)
    storage_path = Column(String, nullable=True)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.pending)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document")