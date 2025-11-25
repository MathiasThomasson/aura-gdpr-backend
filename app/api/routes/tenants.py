from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.database import get_db
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.models.user import UserCreate
from app.core.security import hash_password
from app.core.auth import require_role

router = APIRouter(prefix="/api/tenants", tags=["Tenants"])


class TenantRegisterPayload(UserCreate):
    name: str


@router.post("/register")
async def register_tenant(payload: TenantRegisterPayload, db: AsyncSession = Depends(get_db)):
    # check tenant name
    result = await db.execute(select(Tenant).where(Tenant.name == payload.name))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Tenant name already exists")

    tenant = Tenant(name=payload.name)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)

    # create owner user for tenant
    owner = User(email=payload.email, hashed_password=hash_password(payload.password), tenant_id=tenant.id, role="owner")
    db.add(owner)
    await db.commit()
    await db.refresh(owner)

    return {"tenant": {"id": tenant.id, "name": tenant.name}, "owner": {"id": owner.id, "email": owner.email}}


@router.put("/{tenant_id}")
async def update_tenant(tenant_id: int, payload: TenantRegisterPayload, db: AsyncSession = Depends(get_db), current_user=Depends(require_role("owner", "admin"))):
    # only owner/admin of the tenant may update
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Insufficient privileges for this tenant")
    result = await db.get(Tenant, tenant_id)
    if not result:
        raise HTTPException(status_code=404, detail="Tenant not found")
    result.name = payload.name
    db.add(result)
    await db.commit()
    await db.refresh(result)
    return {"id": result.id, "name": result.name}
