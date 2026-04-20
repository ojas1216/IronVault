"""
Seed script: create default admin user and initial configuration.
Usage: python scripts/seed.py --admin-email admin@ironvault.com --password Admin123!
"""

import argparse
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal, engine, Base
from app.models.user import User
from app.utils.security import hash_password
from app.models.user import UserRole


async def seed_admin(email: str, password: str, name: str = "IronVault Admin") -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()
        if existing:
            print(f"Admin user already exists: {email}")
            return

        admin = User(
            email=email,
            full_name=name,
            hashed_password=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        print(f"✅ Admin user created: {email} (id={admin.id})")


def main():
    parser = argparse.ArgumentParser(description="Seed IronVault MDM database")
    parser.add_argument("--admin-email", default="admin@ironvault.com")
    parser.add_argument("--password", default="Admin123!")
    parser.add_argument("--name", default="IronVault Admin")
    args = parser.parse_args()

    asyncio.run(seed_admin(args.admin_email, args.password, args.name))


if __name__ == "__main__":
    main()
