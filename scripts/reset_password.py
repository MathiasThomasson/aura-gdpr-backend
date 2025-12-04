import asyncio
import sys

from dotenv import load_dotenv
from sqlalchemy import select

load_dotenv()

from app.core.security import hash_password  # noqa: E402
from app.db.database import AsyncSessionLocal  # noqa: E402
from app.db.models.user import User  # noqa: E402


async def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python scripts/reset_password.py <email> <new_password>")
        return
    email = sys.argv[1].strip()
    new_password = sys.argv[2]

    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.email == email))
        user = res.scalars().first()
        if not user:
            print(f"User not found: {email}")
            return
        user.hashed_password = hash_password(new_password)
        session.add(user)
        await session.commit()
        print(f"Password reset for {email}")


if __name__ == "__main__":
    asyncio.run(main())
