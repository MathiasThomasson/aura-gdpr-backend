#!/bin/bash

BASE="/root/aura-gdpr-backend"

echo "📄 Skapar API routes..."

cat > $BASE/app/api/routes/auth.py <<EOF
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.database import get_db
from app.db.models.user import User
from app.models.user import UserCreate
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["Auth"])

@router.post("/register")
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    user = User(email=user_data.email, hashed_password=hash_password(user_data.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"id": user.id, "email": user.email}

@router.post("/login")
async def login(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalars().first()
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}
EOF

cat > $BASE/app/api/routes/users.py <<EOF
from fastapi import APIRouter, Depends
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/users", tags=["Users"])

@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    return current_user
EOF

cat > $BASE/app/api/routes/documents.py <<EOF
from fastapi import APIRouter

router = APIRouter(prefix="/api/documents", tags=["Documents"])

@router.get("/")
def get_docs():
    return {"msg": "Documents placeholder"}
EOF

echo "🔐 Skapar core-moduler..."

cat > $BASE/app/core/security.py <<EOF
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from config.settings import SECRET_KEY, ALGORITHM

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
EOF

cat > $BASE/app/core/auth.py <<EOF
from fastapi import Depends, HTTPException
from jose import JWTError, jwt
from config.settings import SECRET_KEY, ALGORITHM
from app.db.database import get_db
from app.db.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await db.get(User, int(user_id))
    if user is None:
        raise credentials_exception
    return {"id": user.id, "email": user.email}
EOF

echo "👤 Skapar User-modell och schema..."

cat > $BASE/app/db/models/user.py <<EOF
from sqlalchemy import Column, Integer, String
from app.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
EOF

cat > $BASE/app/models/user.py <<EOF
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr

    class Config:
        orm_mode = True
EOF

echo "💾 Skapar database.py..."

cat > $BASE/app/db/database.py <<EOF
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from config.settings import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with async_session() as session:
        yield session
EOF

echo "⚙️ Skapar settings.py..."

cat > $BASE/config/settings.py <<EOF
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

DATABASE_URL = os.getenv("DATABASE_URL")
EOF

echo "✅ Allt klart! Du kan nu köra API:t."
