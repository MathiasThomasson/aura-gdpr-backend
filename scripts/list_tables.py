import os
import sys
import sqlite3
from typing import Optional

try:
    from sqlalchemy import create_engine, inspect
except ImportError:
    create_engine = None
    inspect = None


def list_sqlite_tables(db_path: str) -> None:
    if not os.path.exists(db_path):
        print(f"[SQLite] Database file not found: {db_path}")
        return

    print(f"[SQLite] Listing tables in: {db_path}")
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cur.fetchall()
        if not tables:
            print("  (no tables found)")
            return
        for (name,) in tables:
            print(f"  - {name}")
    finally:
        conn.close()


def list_sqlalchemy_tables(db_url: str) -> None:
    if create_engine is None or inspect is None:
        print("[SQLAlchemy] sqlalchemy is not installed in this environment.")
        return

    print(f"[SQLAlchemy] Connecting to: {db_url}")
    engine = create_engine(db_url)
    try:
        insp = inspect(engine)
        tables = insp.get_table_names()
        if not tables:
            print("  (no tables found)")
            return
        for name in tables:
            print(f"  - {name}")
    finally:
        engine.dispose()


def main() -> None:
    """
    Lists tables in:
    1) dev.db (SQLite) if it exists in the project root
    2) DATABASE_URL (Postgres/other) if set in environment
    """

    project_root = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(project_root)  # go one level up from scripts/
    sqlite_path = os.path.join(project_root, "dev.db")

    print("=== AURA table lister ===\n")

    # 1) Check SQLite dev.db
    if os.path.exists(sqlite_path):
        list_sqlite_tables(sqlite_path)
    else:
        print(f"[SQLite] No dev.db found at: {sqlite_path}")

    print("\n----------------------------\n")

    # 2) Check DATABASE_URL
    db_url: Optional[str] = os.getenv("DATABASE_URL")
    if db_url:
        list_sqlalchemy_tables(db_url)
    else:
        print("[SQLAlchemy] No DATABASE_URL set in environment.")

    print("\nDone.")


if __name__ == "__main__":
    main()
