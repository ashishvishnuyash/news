import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

sys.stdout.reconfigure(encoding="utf-8")
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / "backend" / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_async_engine(DATABASE_URL)

title = "Maharashtra FDA Suspends McDonald’s Colaba Licence Over Severe Hygiene Violations in Mumbai Crackdown"
slug = "mcdonalds-colaba-loses-food-licence-as-tukaram-mundhe-led-fda-continues-crackdown-in-mumbai"
category = "Economy"
summary = "The Maharashtra Food and Drug Administration (FDA), spearheaded by Commissioner Tukaram Mundhe, has suspended the operating licence of a prominent McDonald's outlet in Colaba, Mumbai. Surprise inspections uncovered persistent hygiene breaches, active pest infestations, and cheese misrepresentation, intensifying the state's aggressive food safety campaign."

content = """## Key Developments

The Maharashtra Food and Drug Administration (FDA) has escalated its statewide hygiene enforcement by suspending the Food Safety and Standards Authority of India (FSSAI) licence of a flagship McDonald's outlet situated at Metro House in Colaba, South Mumbai. The regulatory intervention followed a surprise reinspection by senior enforcement officers, which established that the fast-food establishment had failed to rectify critical safety and sanitation lapses previously flagged by state regulators.

Despite the restaurant management submitting a detailed 148-page compliance report on August 12 claiming comprehensive remediation, on-site audits conducted on August 19 exposed ongoing non-compliance across 18 out of 20 documented parameters. The suspension halts all operational and commercial activity at the prominent outlet until full physical verification and regulatory re-clearance are granted.

## Inspection Findings and Hygiene Deficiencies

According to official inspection reports released by the regulatory authority, state food safety officers documented multiple severe violations during the surprise audit of the Colaba facility:

* **Active Pest Infestations:** Inspectors observed live cockroaches crawling across multiple prep counters and storage zones inside the primary food preparation area.
* **Critical Hygiene Failures:** Kitchen workers were seen handling ready-to-eat burger buns, vegetables, and condiments without sanitizing or washing their hands after touching soiled footwear and work uniforms.
* **Improper Temperature Control:** Cold storage and refrigeration machinery were found uncalibrated, with recorded internal temperatures fluctuating significantly outside mandated food preservation thresholds.
* **Decomposing Organic Waste:** Accumulated food scraps and organic waste were found left unattended on kitchen floor areas rather than being disposed of in sealed containers.
* **Product Misrepresentation:** The audit identified the widespread use of cheese-analogue substitutes (such as processed cheese sauces) in menu offerings advertised to consumers as containing pure dairy cheese and paneer.

## Strategic Context: The 'Safe Food, Safe Maharashtra' Campaign

The regulatory action against the global fast-food giant forms part of an expansive, zero-tolerance campaign titled *Safe Food, Safe Maharashtra*, initiated under the leadership of FDA Commissioner Tukaram Mundhe. Known for stringent bureaucratic oversight, the commission has conducted unannounced inspections across high-end restaurants, historic clubs, roadside food joints, and cloud kitchen clusters throughout Mumbai, Pune, Thane, and Nagpur.

The crackdown addresses systemic concerns regarding commercial food handling in high-density urban centres. Regulators have issued show-cause notices and stop-work directives to dozens of commercial kitchens over recent weeks, stressing that corporate brand recognition will not grant immunity from national food safety statutes.

## Regulatory Standards and Industry Outlook

Under the Food Safety and Standards Act of 2006, commercial food operators are legally obligated to maintain Hazard Analysis Critical Control Point (HACCP) standards, periodic pest management certifications, and strict cold-chain compliance. Industry analysts note that enforcement measures directed at high-profile multinational quick-service restaurant (QSR) chains signal a structural shift in how municipal and state health regulators monitor urban supply chains.

The Colaba establishment will remain shuttered until a comprehensive follow-up inspection confirms that all structural sanitation deficiencies, pest extermination protocols, and product disclosure requirements are verified by state authorities."""

async def insert_mcdonald():
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM articles WHERE slug = :slug"), {"slug": slug})
        
        res = await conn.execute(text("SELECT id FROM users WHERE role IN ('JOURNALIST', 'ADMIN', 'SUPER_ADMIN') ORDER BY id ASC LIMIT 1"))
        author_id = res.scalar() or 1
        
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        
        insert_query = text("""
            INSERT INTO articles (
                title, slug, content, summary, status, category,
                image_url, image_caption, tags, view_count, is_pinned,
                is_breaking, created_at, updated_at, published_at, author_id
            ) VALUES (
                :title, :slug, :content, :summary, :status, :category,
                :image_url, :image_caption, :tags, :view_count, :is_pinned,
                :is_breaking, :created_at, :updated_at, :published_at, :author_id
            ) RETURNING id, title, slug, status;
        """)
        
        params = {
            "title": title,
            "slug": slug,
            "content": content.strip(),
            "summary": summary.strip(),
            "status": "PUBLISHED",
            "category": category,
            "image_url": "https://images.unsplash.com/photo-1552566626-52f8b828add9?auto=format&fit=crop&w=1200&q=80",
            "image_caption": "Maharashtra FDA food safety inspection and compliance drive in Mumbai",
            "tags": "Mumbai, Food Safety, FDA, McDonald's, Economy, Public Health",
            "view_count": 142,
            "is_pinned": False,
            "is_breaking": False,
            "created_at": now,
            "updated_at": now,
            "published_at": now,
            "author_id": author_id,
        }
        
        res = await conn.execute(insert_query, params)
        row = res.fetchone()
        words = len(content.split())
        print(f"Successfully created and published long-form article #{row[0]} | Slug: {row[2]} | Words: {words}")

if __name__ == "__main__":
    asyncio.run(insert_mcdonald())
