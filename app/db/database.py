import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Always expose Base so models can import it.
Base = declarative_base()

# When running under Alembic autogenerate, skip creating an Async engine
# because Alembic will import models to inspect metadata and we don't want
# to require an async DB driver for that import.
if os.getenv("ALEMBIC") != "1":
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def get_db():
        async with async_session() as session:
            yield session
else:
    engine = None
    async_session = None

    async def get_db():
        # placeholder generator for alembic import-time; shouldn't be used during autogenerate
        if False:
            yield None
