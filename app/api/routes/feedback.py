from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.feedback import Feedback
import uuid

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackCreate(BaseModel):
    message_id: str
    rating: int        # 1 = thumbs up, -1 = thumbs down
    comment: str = ""


@router.post("/")
def submit_feedback(
    body: FeedbackCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if body.rating not in [1, -1]:
        raise HTTPException(status_code=400, detail="Rating must be 1 or -1")

    feedback = Feedback(
        id=uuid.uuid4(),
        org_id=current_user.org_id,
        user_id=current_user.id,
        message_id=body.message_id,
        rating=body.rating,
        comment=body.comment
    )
    db.add(feedback)
    db.commit()
    return {"status": "ok"}


@router.get("/")
def get_feedback(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    feedbacks = db.query(Feedback).filter(
        Feedback.org_id == current_user.org_id
    ).order_by(Feedback.created_at.desc()).limit(100).all()

    return [
        {
            "id": str(f.id),
            "message_id": str(f.message_id),
            "rating": f.rating,
            "comment": f.comment,
            "created_at": str(f.created_at)
        }
        for f in feedbacks
    ]
