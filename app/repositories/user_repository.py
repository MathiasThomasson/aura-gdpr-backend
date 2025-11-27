from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User


async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    return await db.get(User, user_id)


async def get_user_in_tenant(db: AsyncSession, tenant_id: int, user_id: int) -> Optional[User]:
    res = await db.execute(select(User).where(User.id == user_id, User.tenant_id == tenant_id))
    return res.scalars().first()


async def list_users_in_tenant(db: AsyncSession, tenant_id: int) -> List[User]:
    res = await db.execute(select(User).where(User.tenant_id == tenant_id))
    return res.scalars().all()


async def create_user(db: AsyncSession, email: str, hashed_password: str, tenant_id: int, role: str) -> User:
    user = User(email=email, hashed_password=hashed_password, tenant_id=tenant_id, role=role)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def save_user(db: AsyncSession, user: User) -> User:
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
