from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.analytics_event import AnalyticsEvent


async def record_event(db: AsyncSession, tenant_id: int, user_id: int, event_name: str) -> AnalyticsEvent:
    event = AnalyticsEvent(tenant_id=tenant_id, user_id=user_id, event_name=event_name)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event
