from logging.config import fileConfig
import os
import sys

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# add project path so alembic can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# signal to app code that we're running in alembic/autogenerate context
os.environ.setdefault("ALEMBIC", "1")

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# import the app's metadata
from app.db.base import Base
from app.core.config import settings

# import model modules so that Table objects are registered on Base.metadata
import app.db.models  # noqa: F401

# target_metadata for 'autogenerate' support
target_metadata = Base.metadata

# Ensure sqlalchemy.url is set from settings (convert async driver to sync where needed)
db_url = settings.DATABASE_URL
if db_url is None:
    # fallback to value in alembic.ini
    db_url = config.get_main_option("sqlalchemy.url")
# Normalize async driver URLs to a sync form alembic can use.
if "+aiosqlite" in db_url:
    # preserve the file path form (sqlite:///...)
    sync_db_url = db_url.replace("+aiosqlite", "")
elif "+" in db_url:
    # generic conversion: remove the async driver part (e.g. postgresql+asyncpg -> postgresql)
    parts = db_url.split(":", 1)
    sync_db_url = db_url.split("+", 1)[0] + ":" + parts[1]
else:
    sync_db_url = db_url

config.set_main_option("sqlalchemy.url", sync_db_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
