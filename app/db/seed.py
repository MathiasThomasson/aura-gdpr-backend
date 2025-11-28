import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password as get_password_hash
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.db.models.user_tenant import UserTenant, UserTenantRole

# Async engine/session factory driven by settings.DATABASE_URL
engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_or_create_tenant(session: AsyncSession) -> Tenant:
    result = await session.execute(select(Tenant).where(Tenant.slug == "aura-gdpr"))
    tenant = result.scalars().first()
    if tenant:
        print(f"Tenant already exists: id={tenant.id}, slug={tenant.slug}")
        return tenant

    tenant = Tenant(name="AURA-GDPR", slug="aura-gdpr", is_active=True)
    session.add(tenant)
    await session.flush()
    print(f"Created tenant: id={tenant.id}, slug={tenant.slug}")
    return tenant


async def get_or_create_admin_user(session: AsyncSession, tenant: Tenant) -> User:
    result = await session.execute(select(User).where(User.email == "admin@aura-gdpr.se"))
    user = result.scalars().first()
    if user:
        print(f"Admin user already exists: id={user.id}, email={user.email}")
        return user

    user = User(
        email="admin@aura-gdpr.se",
        full_name="AURA Admin",
        is_active=True,
        is_superadmin=True,
        hashed_password=get_password_hash("AuraGdpr123!"),
        tenant_id=tenant.id,
        role="owner",
    )
    session.add(user)
    await session.flush()
    print(f"Created admin user: id={user.id}, email={user.email}")
    return user


async def ensure_user_tenant_membership(session: AsyncSession, user: User, tenant: Tenant) -> None:
    result = await session.execute(
        select(UserTenant).where(UserTenant.user_id == user.id, UserTenant.tenant_id == tenant.id)
    )
    membership = result.scalars().first()
    if membership:
        print(f"UserTenant membership already exists: user_id={user.id}, tenant_id={tenant.id}, role={membership.role}")
        return

    membership = UserTenant(
        user_id=user.id,
        tenant_id=tenant.id,
        role=UserTenantRole.owner,
        is_active=True,
    )
    session.add(membership)
    await session.flush()
    print(f"Created UserTenant membership: user_id={user.id}, tenant_id={tenant.id}, role={membership.role}")


async def run_seed_async() -> None:
    async with AsyncSessionLocal() as session:
        try:
            tenant = await get_or_create_tenant(session)
            user = await get_or_create_admin_user(session, tenant)
            await ensure_user_tenant_membership(session, user, tenant)
            await session.commit()
            print("\nSeed completed successfully.")
            print(f"Tenant: id={tenant.id}, slug={tenant.slug}")
            print(f"Admin: email=admin@aura-gdpr.se password=AuraGdpr123!")
        except Exception as exc:  # pragma: no cover - seed helper
            await session.rollback()
            print(f"Seed failed, rolled back: {exc}")
            raise


def run_seed() -> None:
    asyncio.run(run_seed_async())


if __name__ == "__main__":
    run_seed()
