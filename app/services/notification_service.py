from typing import List

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.notification import Notification


async def list_notifications(
    db: AsyncSession, tenant_id: int, user_id: int, role: str, only_unread: bool
) -> tuple[List[Notification], int]:
    filters = [Notification.tenant_id == tenant_id]
    if role not in ("owner", "admin"):
        filters.append(or_(Notification.user_id == user_id, Notification.user_id.is_(None)))
    if only_unread:
        filters.append(Notification.read.is_(False))

    res = await db.execute(
        select(Notification).where(and_(*filters)).order_by(Notification.created_at.desc())
    )
    items = res.scalars().all()

    total = (await db.execute(select(func.count()).select_from(select(Notification.id).where(and_(*filters)).subquery()))).scalar_one()
    return items, total


async def mark_notification_read(
    db: AsyncSession, tenant_id: int, user_id: int, role: str, notification_id: int
) -> Notification:
    stmt = select(Notification).where(Notification.id == notification_id, Notification.tenant_id == tenant_id)
    if role not in ("owner", "admin"):
        stmt = stmt.where(or_(Notification.user_id == user_id, Notification.user_id.is_(None)))
    notif = (await db.execute(stmt)).scalars().first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.read = True
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    return notif


async def mark_all_read(db: AsyncSession, tenant_id: int, user_id: int, role: str) -> int:
    filter_cond = [Notification.tenant_id == tenant_id]
    if role not in ("owner", "admin"):
        filter_cond.append(or_(Notification.user_id == user_id, Notification.user_id.is_(None)))
    stmt = (
        update(Notification)
        .where(and_(*filter_cond))
        .values(read=True)
    )
    res = await db.execute(stmt)
    await db.commit()
    return res.rowcount or 0
