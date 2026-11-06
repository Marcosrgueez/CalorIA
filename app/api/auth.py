import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.diet import UserORM

router = APIRouter(prefix="/auth", tags=["auth"])

SECRET_KEY = os.environ.get("CALORIA_SECRET_KEY", "caloria-dev-secret-key-change-in-prod")
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 30
FREE_DAILY_LIMIT = 3

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


# ─── Pydantic schemas ───────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    plan: str
    diets_today: int


class UserMeResponse(BaseModel):
    user_id: int
    email: str
    username: str
    plan: str
    diets_today: int
    created_at: datetime


# ─── Helpers ────────────────────────────────────────────────────────────────

def _create_token(user: UserORM) -> str:
    payload = {
        "user_id": user.id,
        "username": user.username,
        "plan": user.plan,
        "exp": datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _today_str() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


def get_optional_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[UserORM]:
    if not creds:
        return None
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            return None
        return db.query(UserORM).filter(UserORM.id == user_id).first()
    except JWTError:
        return None


def get_required_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> UserORM:
    user = get_optional_user(creds, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Autenticación requerida.")
    return user


# ─── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    if db.query(UserORM).filter(UserORM.email == req.email).first():
        raise HTTPException(status_code=409, detail="Email ya registrado.")
    if db.query(UserORM).filter(UserORM.username == req.username).first():
        raise HTTPException(status_code=409, detail="Nombre de usuario ya existe.")
    user = UserORM(
        email=req.email,
        username=req.username,
        password_hash=pwd_ctx.hash(req.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(
        access_token=_create_token(user),
        username=user.username,
        plan=user.plan,
        diets_today=user.diets_today,
    )


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(UserORM).filter(UserORM.email == req.email).first()
    if not user or not pwd_ctx.verify(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos.")
    # Sync diets_today in case date changed
    today = _today_str()
    if user.last_diet_date != today:
        user.diets_today = 0
        user.last_diet_date = today
        db.commit()
    return TokenResponse(
        access_token=_create_token(user),
        username=user.username,
        plan=user.plan,
        diets_today=user.diets_today,
    )


@router.get("/me", response_model=UserMeResponse)
def me(user: UserORM = Depends(get_required_user)) -> UserMeResponse:
    today = _today_str()
    diets_today = user.diets_today if user.last_diet_date == today else 0
    return UserMeResponse(
        user_id=user.id,
        email=user.email,
        username=user.username,
        plan=user.plan,
        diets_today=diets_today,
        created_at=user.created_at,
    )
