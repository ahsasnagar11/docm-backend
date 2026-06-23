from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from app.database import get_db
from app.models.user import User
from app.models.conversation import Conversation, Message, MessageRole
from app.middleware.auth_middleware import get_current_user
from app.services.rag.agent_service import retrieve
from app.services.rag.generate_service import generate_answer
import json
import uuid

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None

@router.post("/")
def chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if req.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == req.conversation_id,
            Conversation.org_id == current_user.org_id
        ).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation = Conversation(
            org_id=current_user.org_id,
            user_id=current_user.id,
            title=req.question[:50]
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    history_messages = db.query(Message).filter(
        Message.conversation_id == conversation.id
    ).order_by(Message.created_at.asc()).all()

    conversation_history = [
        {"role": m.role.value, "content": m.content}
        for m in history_messages
    ]

    user_message = Message(
        conversation_id=conversation.id,
        role=MessageRole.user,
        content=req.question
    )
    db.add(user_message)
    db.commit()

    chunks = retrieve(req.question, str(current_user.org_id), db)

    sources = [
        {
            "chunk_id": c["id"],
            "document_id": c["document_id"],
            "page_number": c.get("page_number"),
            "relevance_score": c.get("relevance_score", 0),
            "content_preview": c["content"][:200]
        }
        for c in chunks
    ]

    def stream_response():
        full_response = ""

        conv_id_chunk = json.dumps({"conversation_id": str(conversation.id)}) + "\n"
        yield conv_id_chunk

        stream = generate_answer(req.question, chunks, conversation_history)

        for chunk in stream:
            # No context case — plain string yield hota hai
            if isinstance(chunk, str):
                full_response += chunk
                yield chunk
                continue

            # Normal Groq streaming
            delta = chunk.choices[0].delta.content
            if delta:
                full_response += delta
                yield delta

        assistant_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.assistant,
            content=full_response,
            sources=sources
        )
        db.add(assistant_message)
        db.commit()

    return StreamingResponse(stream_response(), media_type="text/plain")

@router.get("/conversations")
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conversations = db.query(Conversation).filter(
        Conversation.org_id == current_user.org_id,
        Conversation.user_id == current_user.id
    ).order_by(Conversation.created_at.desc()).all()

    return [
        {"id": str(c.id), "title": c.title, "created_at": c.created_at}
        for c in conversations
    ]

@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.org_id == current_user.org_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = db.query(Message).filter(
        Message.conversation_id == conversation.id
    ).order_by(Message.created_at.asc()).all()

    return {
        "id": str(conversation.id),
        "title": conversation.title,
        "messages": [
            {
                "id": str(m.id),
                "role": m.role.value,
                "content": m.content,
                "sources": m.sources,
                "created_at": m.created_at
            }
            for m in messages
        ]
    }