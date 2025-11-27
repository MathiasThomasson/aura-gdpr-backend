from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import declarative_base, declared_attr


Base = declarative_base()


class TenantBoundMixin:
    """Mixin to enforce tenant_id presence on tenant-scoped tables."""

    @declared_attr
    def tenant_id(cls):  # type: ignore[override]
        return Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
