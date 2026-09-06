"""
Seed or Upsert Super Admin account in the active database (PostgreSQL / SQLite).
"""

import asyncio
import os
import sys
from sqlalchemy import select

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal, engine, Base
from app.models import User
from app.auth import get_password_hash
from app.config import settings

async def seed_super_admin():
    db_target = settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL
    print(f"Connecting to database: {db_target}")
    
    # Ensure tables exist first
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with SessionLocal() as db:
        stmt = select(User).where(User.username == "rajiv_sharma")
        res = await db.execute(stmt)
        super_admin = res.scalar_one_or_none()
        
        default_password = "password123"
        hashed = get_password_hash(default_password)
        
        if super_admin:
            print("Updating existing 'rajiv_sharma' account...")
            super_admin.role = "SUPER_ADMIN"
            super_admin.slug = "rajiv-sharma"
            super_admin.hashed_password = hashed
            super_admin.is_active = True
            if not super_admin.email:
                super_admin.email = "superadmin@therepublicbulletin.com"
        else:
            print("Creating new 'rajiv_sharma' account...")
            super_admin = User(
                username="rajiv_sharma",
                slug="rajiv-sharma",
                email="superadmin@therepublicbulletin.com",
                hashed_password=hashed,
                role="SUPER_ADMIN",
                bio="Chief Executive Publisher & System Administrator.",
                is_active=True
            )
            db.add(super_admin)
            
        await db.commit()
        await db.refresh(super_admin)
        
        print("\n" + "=" * 50)
        print(" SUPER ADMIN ACCOUNT READY!")
        print("=" * 50)
        print(f"  Username : rajiv_sharma")
        print(f"  Email    : superadmin@therepublicbulletin.com")
        print(f"  Password : {default_password}")
        print(f"  Role     : SUPER_ADMIN")
        print("=" * 50 + "\n")

if __name__ == "__main__":
    try:
        asyncio.run(seed_super_admin())
    except Exception as e:
        print(f"Error seeding rajiv_sharma: {e}")
        sys.exit(1)
