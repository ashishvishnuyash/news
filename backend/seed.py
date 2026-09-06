import asyncio
import json
from datetime import datetime, timedelta
from app.database import engine, Base, SessionLocal
from app.models import User, Article, Comment, ReviewComment, SiteSetting
from app.auth import get_password_hash

async def seed_data():
    print("Seeding database for The Republic Bulletin...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        
    async with SessionLocal() as db:
        # 1. Create users for all 5 roles
        superadmin = User(
            username="rajiv_sharma",
            slug="rajiv-sharma",
            email="superadmin@therepublicbulletin.com",
            hashed_password=get_password_hash("password123"),
            role="SUPER_ADMIN",
            bio="Chief Executive Publisher & System Administrator."
        )
        admin = User(
            username="priya_mehta",
            slug="priya-mehta",
            email="admin@therepublicbulletin.com",
            hashed_password=get_password_hash("password123"),
            role="ADMIN",
            bio="Operations Manager & Staff Coordinator."
        )
        editor = User(
            username="ananya_rao",
            slug="ananya-rao",
            email="editor@therepublicbulletin.com",
            hashed_password=get_password_hash("password123"),
            role="EDITOR",
            bio="Managing Editor - Chief of Editorial Review Desk."
        )
        journalist = User(
            username="arjun_verma",
            slug="arjun-verma",
            email="journalist@therepublicbulletin.com",
            hashed_password=get_password_hash("password123"),
            role="JOURNALIST",
            bio="Senior Foreign & Political Correspondent."
        )
        reader = User(
            username="reader",
            email="reader@therepublicbulletin.com",
            hashed_password=get_password_hash("password123"),
            role="READER",
            bio="Avid Reader & Lifetime Patron Subscriber."
        )
        
        db.add_all([superadmin, admin, editor, journalist, reader])
        await db.commit()
        
        await db.refresh(superadmin)
        await db.refresh(admin)
        await db.refresh(editor)
        await db.refresh(journalist)
        await db.refresh(reader)

        # 2. Create Site Settings
        settings_data = [
            SiteSetting(key="site_name", value="The Republic Bulletin", description="Publication Header Title"),
            SiteSetting(key="site_motto", value="The Voice of Truth, Unfiltered & Uncompromised", description="Masthead Tagline"),
            SiteSetting(key="breaking_news", value="BREAKING: Republic Senate Passes Landmark Clean Energy Infrastructure Act with Bi-Partisan Support", description="Live Broadcast Ticker Text"),
            SiteSetting(key="breaking_active", value="true", description="Broadcast Ticker Toggle State"),
            SiteSetting(key="categories", value=json.dumps(["Politics", "World", "Economy", "Tech", "Culture", "Opinion"]), description="Publication Categories"),
            SiteSetting(key="features", value=json.dumps({"comments_enabled": True, "registration_open": True, "maintenance_mode": False}), description="System Feature Flags"),
        ]

        db.add_all(settings_data)
        await db.commit()
        
        # 3. Create Articles
        a1 = Article(
            title="Republic Senate Passes Landmark Clean Energy Infrastructure Act",
            slug="republic-senate-passes-landmark-clean-energy-infrastructure-act",
            content="""WASHINGTON D.C. — In a historic late-night session, the Republic Senate voted 72 to 28 to approve the Clean Energy & Public Infrastructure Act of 2026. The sweeping legislation allocates $450 billion over the next decade to overhaul national power grids, expand high-speed transit networks, and subsidize municipal solar installations.

The bill's passage follows months of intense debates between industrial leaders and environmental advocates. 'This legislation marks a decisive turning point,' declared Senior Senator Eleanor Vance during her post-vote address. 'We are equipping our nation with resilient infrastructure while safeguarding our atmospheric future.'

Key provisions of the bill include strict carbon caps for heavy industrial manufacturing, tax incentives for rural electrification, and a $30 billion grant program for university-led fusion research. Implementation is scheduled to begin early next quarter.""",
            summary="A comprehensive overview of the newly passed Clean Energy Infrastructure Act and its multi-billion dollar allocation for grid modernization.",
            category="Politics",
            status="PUBLISHED",
            is_pinned=True,
            is_breaking=True,
            image_url="https://images.unsplash.com/photo-1541872703-74c5e44368f9?auto=format&fit=crop&w=1200&q=80",
            tags="Politics, Energy, Senate, Infrastructure",
            view_count=1420,
            author_id=journalist.id,
            editor_id=editor.id,
            published_at=datetime.utcnow() - timedelta(hours=1)
        )

        a2 = Article(
            title="Global Markets Surge as Supply Chain Bottlenecks Dissolve",
            slug="global-markets-surge-as-supply-chain-bottlenecks-dissolve",
            content="""LONDON / NEW YORK — Financial indices across the globe reached multi-year highs today as central banks reported a significant easing of international freight delays and raw material shortages.

The Dow Jones Industrial Average rose 410 points in early trading, propelled by strong quarterly earnings reports from manufacturing and shipping conglomerates. Analysts attribute the stabilization to restored port efficiency and lowered maritime insurance premiums.

'We are witnessing a return to predictable trade velocity,' commented Chief Economist Marcus Sterling of the International Trade Bureau. 'With freight rates normalizing, inflationary pressures on essential commodities are subsiding faster than forecasted.'""",
            summary="Global financial markets respond positively to restored trade shipping routes and reduced commodity prices.",
            category="Economy",
            status="PUBLISHED",
            is_pinned=False,
            is_breaking=False,
            image_url="https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1200&q=80",
            tags="Economy, Markets, Finance, Global Trade",
            view_count=890,
            author_id=journalist.id,
            editor_id=editor.id,
            published_at=datetime.utcnow() - timedelta(hours=4)
        )

        a3 = Article(
            title="Editorial: The Lost Art of Slow Reading in a High-Speed Age",
            slug="editorial-the-lost-art-of-slow-reading-in-a-high-speed-age",
            content="""We live in an era characterized by relentless notifications, infinite scrolling, and truncated attention spans. The morning newspaper, once consumed with deliberate focus over a quiet cup of black coffee, has been widely supplanted by algorithmic streams designed for friction-less consumption.

Yet, what profound depth do we forfeit when we exchange thoughtful reflection for rapid skimming?

This column makes a passionate case for the resurgence of long-form journalism, carefully typeset columns, and the patient contemplation of complex ideas. In the dark ink and off-white pages of traditional newsprint, one finds a clarity and permanence that flashing digital screens so often obscure. Let us turn the page deliberately and savor the craftsmanship of prose.""",
            summary="A reflective essay on the cognitive benefits of deep, patient reading in an era dominated by micro-content.",
            category="Opinion",
            status="PUBLISHED",
            is_pinned=False,
            is_breaking=False,
            image_url="https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1200&q=80",
            tags="Opinion, Culture, Reading, Society",
            view_count=650,
            author_id=journalist.id,
            editor_id=editor.id,
            published_at=datetime.utcnow() - timedelta(days=1)
        )

        a4 = Article(
            title="Breakthrough in Quantum Computing Architecture Revealed",
            slug="breakthrough-in-quantum-computing-architecture-revealed",
            content="""CAMBRIDGE — Physicists at the National Technology Institute have unveiled a novel topological qubit architecture capable of operating at near-ambient temperatures.

The breakthrough overcomes decades-old thermal decoherence barriers, bringing commercial fault-tolerant quantum processing significantly closer to reality. Initial benchmark tests demonstrated a 1,000x acceleration in complex molecular simulation algorithms.""",
            summary="Scientists introduce a room-temperature quantum processor architecture that promises revolutionary computing gains.",
            category="Tech",
            status="SUBMITTED",
            is_pinned=False,
            is_breaking=False,
            image_url="https://images.unsplash.com/photo-1635070041078-e363dbe005cb?auto=format&fit=crop&w=1200&q=80",
            tags="Tech, Quantum, Science, Innovation",
            view_count=120,
            author_id=journalist.id
        )

        a5 = Article(
            title="Draft: Deep Sea Mineral Mining Debates Intensify",
            slug="draft-deep-sea-mineral-mining-debates-intensify",
            content="""GENEVA — International maritime authorities met this week to evaluate proposed regulations for polymetallic nodule harvesting on the abyssal plain. Environmental scientists caution against irreversible benthic ecosystem disruption.""",
            summary="Draft article examining environmental and economic arguments regarding seabed mineral extraction.",
            category="World",
            status="DRAFT",
            is_pinned=False,
            is_breaking=False,
            image_url="https://images.unsplash.com/photo-1518837695005-2083093ee35b?auto=format&fit=crop&w=1200&q=80",
            tags="World, Oceans, Environment",
            view_count=15,
            author_id=journalist.id
        )

        a6 = Article(
            title="Returned for Revisions: Regional Agricultural Yield Analysis",
            slug="returned-for-revisions-regional-agricultural-yield-analysis",
            content="""Precipitation variations across Midwestern agricultural belts have affected corn and soybean harvests. 

[Editor Note: Needs verified USDA statistics and interviews with regional farm co-op representatives before resubmission.]""",
            summary="Analysis of crop yields across the Midwestern agricultural belt.",
            category="Economy",
            status="REJECTED",
            is_pinned=False,
            is_breaking=False,
            tags="Agriculture, Economy, Crop Yields",
            view_count=45,
            author_id=journalist.id,
            editor_id=editor.id
        )

        db.add_all([a1, a2, a3, a4, a5, a6])
        await db.commit()

        # 4. Create comments
        c1 = Comment(
            content="A monumental legislative achievement. The funding allocated for power grid modernization is long overdue.",
            article_id=a1.id,
            author_id=reader.id
        )
        c2 = Comment(
            content="This editorial resonated deeply. Holding a physical paper or reading in a clean broadsheet format is infinitely more rewarding.",
            article_id=a3.id,
            author_id=reader.id
        )
        db.add_all([c1, c2])

        # 5. Create review logs
        r1 = ReviewComment(
            content="Please obtain official USDA harvest numbers for Iowa and Illinois and integrate them into the second paragraph.",
            article_id=a6.id,
            author_id=editor.id
        )
        db.add_all([r1])

        await db.commit()
        print("Successfully seeded The Republic Bulletin database with all 5 role accounts and sample broadsheet articles!")

if __name__ == "__main__":
    asyncio.run(seed_data())
