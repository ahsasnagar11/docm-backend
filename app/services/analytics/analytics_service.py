from sqlalchemy.orm import Session
from sqlalchemy import func, text
from datetime import datetime, timedelta
from app.models.analytics import AnalyticsEvent
from app.models.conversation import Conversation, Message
from app.models.document import Document
from app.models.feedback import Feedback


def log_event(db: Session, org_id: str, user_id: str, event_type: str, metadata: dict = {}):
    event = AnalyticsEvent(
        org_id=org_id,
        user_id=user_id,
        event_type=event_type,
        metadata=metadata
    )
    db.add(event)
    db.commit()


def get_overview(db: Session, org_id: str, days: int = 30) -> dict:
    since = datetime.utcnow() - timedelta(days=days)

    total_queries = db.query(Message).join(Conversation).filter(
        Conversation.org_id == org_id,
        Message.role == "user",
        Message.created_at >= since
    ).count()

    total_documents = db.query(Document).filter(
        Document.org_id == org_id,
        Document.status == "ready"
    ).count()

    total_conversations = db.query(Conversation).filter(
        Conversation.org_id == org_id,
        Conversation.created_at >= since
    ).count()

    positive_feedback = db.query(Feedback).filter(
        Feedback.org_id == org_id,
        Feedback.rating == 1,
        Feedback.created_at >= since
    ).count()

    negative_feedback = db.query(Feedback).filter(
        Feedback.org_id == org_id,
        Feedback.rating == -1,
        Feedback.created_at >= since
    ).count()

    total_feedback = positive_feedback + negative_feedback
    satisfaction_rate = round((positive_feedback / total_feedback) * 100, 1) if total_feedback > 0 else 0

    return {
        "total_queries": total_queries,
        "total_documents": total_documents,
        "total_conversations": total_conversations,
        "satisfaction_rate": satisfaction_rate,
        "positive_feedback": positive_feedback,
        "negative_feedback": negative_feedback,
        "period_days": days
    }


def get_daily_queries(db: Session, org_id: str, days: int = 30) -> list:
    since = datetime.utcnow() - timedelta(days=days)

    results = db.execute(text("""
        SELECT DATE(m.created_at) as day, COUNT(*) as count
        FROM messages m
        JOIN conversations c ON m.conversation_id = c.id
        WHERE c.org_id = :org_id
          AND m.role = 'user'
          AND m.created_at >= :since
        GROUP BY DATE(m.created_at)
        ORDER BY day ASC
    """), {"org_id": org_id, "since": since}).fetchall()

    return [{"date": str(row.day), "queries": row.count} for row in results]


def get_top_documents(db: Session, org_id: str, limit: int = 10) -> list:
    results = db.execute(text("""
        SELECT d.title, d.source_type, COUNT(ms.id) as cite_count
        FROM documents d
        JOIN chunks ch ON ch.document_id = d.id
        JOIN message_sources ms ON ms.chunk_id = ch.id
        JOIN messages m ON ms.message_id = m.id
        JOIN conversations c ON m.conversation_id = c.id
        WHERE c.org_id = :org_id
        GROUP BY d.id, d.title, d.source_type
        ORDER BY cite_count DESC
        LIMIT :limit
    """), {"org_id": org_id, "limit": limit}).fetchall()

    return [{"title": row.title, "source_type": row.source_type, "citations": row.cite_count} for row in results]
