from fastapi import APIRouter, Depends, HTTPException, Response, Cookie, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from app.database import get_db
from app.models.user import User, Organization, UserRole
from app.utils.jwt_utils import create_access_token, create_refresh_token, verify_token
from app.utils.password_utils import hash_password, verify_password
import uuid

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    org_name: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# RefreshRequest class hata do — ab cookie se aayega

def set_refresh_cookie(response: Response, token: str):
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=False,      # production mein True
        samesite="lax",
        max_age=7 * 24 * 60 * 60
    )

@router.post("/register")
def register(req: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    slug = req.org_name.lower().replace(" ", "-") + "-" + str(uuid.uuid4())[:8]
    org = Organization(name=req.org_name, slug=slug)
    db.add(org)
    db.flush()

    user = User(
        org_id=org.id,
        email=req.email,
        password_hash=hash_password(req.password),
        role=UserRole.admin
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token({"sub": str(user.id), "org_id": str(org.id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id), "org_id": str(org.id), "role": user.role})
    set_refresh_cookie(response, refresh_token)  # cookie mein set

    return {
        "access_token": access_token,
        # refresh_token response mein nahi — cookie mein hai
        "user": {"id": str(user.id), "email": user.email, "role": user.role, "org_id": str(org.id)}
    }

@router.post("/login")
def login(req: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token({"sub": str(user.id), "org_id": str(user.org_id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id), "org_id": str(user.org_id), "role": user.role})
    set_refresh_cookie(response, refresh_token)  # cookie mein set

    return {
        "access_token": access_token,
        # refresh_token response mein nahi — cookie mein hai
        "user": {"id": str(user.id), "email": user.email, "role": user.role, "org_id": str(user.org_id)}
    }

@router.post("/refresh")
def refresh(refresh_token: str = Cookie(None)):  # body se nahi, cookie se
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    payload = verify_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    access_token = create_access_token({
        "sub": payload["sub"],
        "org_id": payload["org_id"],
        "role": payload["role"]
    })
    return {"access_token": access_token}

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}