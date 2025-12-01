import os
import pytest
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Set up test database before anything else imports the app
ROOT = Path(__file__).resolve().parents[1]
DB_FILE = ROOT / "dev.db"

# Ensure ALEMBIC env var is not set during tests so `get_db` uses real engine
os.environ.pop("ALEMBIC", None)

# Remove any previous test DB to ensure clean state
if DB_FILE.exists():
    try:
        DB_FILE.unlink()
    except Exception:
        pass

# Point app configuration to the test DB (async URL form)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{DB_FILE.as_posix()}"

# Create async engine and session factory for tests
test_engine = create_async_engine(
    os.environ["DATABASE_URL"],
    echo=False,
    connect_args={"timeout": 10}
)
TestAsyncSession = sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Run alembic migrations against the fresh DB so that schema exists for tests.
try:
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config(str(ROOT / "alembic.ini"))
    # run migrations to head
    command.upgrade(alembic_cfg, "head")
    # Unset ALEMBIC env var that may be set during alembic import; this prevents
    # the app code from thinking it's in an alembic autogenerate context
    os.environ.pop("ALEMBIC", None)
    # Ensure any tables not covered by migrations are created for tests
    from app.db.base import Base  # noqa: WPS433
    import app.db.models  # noqa: F401,WPS433  # register models
    from sqlalchemy import create_engine  # noqa: WPS433

    sync_url = os.environ["DATABASE_URL"].replace("+aiosqlite", "")
    sync_engine = create_engine(sync_url)
    Base.metadata.create_all(bind=sync_engine)
except Exception as e:
    # If alembic isn't available, fallback to creating tables using SQLAlchemy metadata.
    try:
        from app.db.base import Base
        import app.db.models  # noqa: F401  # register models
        from sqlalchemy import create_engine

        # Use sync engine for metadata.create_all
        sync_url = os.environ["DATABASE_URL"].replace("+aiosqlite", "")
        sync_engine = create_engine(sync_url)
        Base.metadata.create_all(bind=sync_engine)
    except Exception:
        pass


@pytest.fixture
async def get_test_db():
    """Async DB session generator for tests."""
    async with TestAsyncSession() as session:
        yield session


# Override FastAPI's get_db dependency to use the test engine
# This happens at fixture setup time (module import), so the app's dependency
# overrides will use the test session.
@pytest.fixture(scope="function", autouse=True)
def setup_test_db_override():
    """Override get_db dependency in the FastAPI app before tests run."""
    from main import app
    from app.db.database import get_db

    async def test_get_db():
        async with TestAsyncSession() as session:
            yield session

    # Always (re-)apply the test override before each test to avoid tests clearing overrides
    app.dependency_overrides[get_db] = test_get_db
    yield
    app.dependency_overrides.clear()


def pytest_sessionfinish(session, exitstatus):
    """Clean up the temporary database file after the test session."""
    try:
        if DB_FILE.exists():
            DB_FILE.unlink()
    except Exception:
        pass
