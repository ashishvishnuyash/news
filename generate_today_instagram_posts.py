import sys
sys.path.insert(0, r"d:\NeWS\backend")
from dotenv import load_dotenv
load_dotenv(r"d:\NeWS\backend\.env")

import os
import io
import re
import json
import base64
import html
import subprocess
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from app.database import SessionLocal
from app.models import Article
from sqlalchemy import select

# Ensure utf-8 standard output
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

OUTPUT_DIR = r"d:\NeWS\instagram_posts\today_2026_08_30"
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
HTML_DIR = os.path.join(OUTPUT_DIR, "html")
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(HTML_DIR, exist_ok=True)

# Load base64 masthead
MASTHEAD_PATH = r"d:\NeWS\scratch\masthead_extracted.png"
with open(MASTHEAD_PATH, "rb") as f:
    MASTHEAD_B64 = base64.b64encode(f.read()).decode("utf-8")

CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME_EXE):
    CHROME_EXE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

CARD_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{safe_title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@600;700;800;900&family=Newsreader:ital,opsz,wght@1,6..72,400;1,6..72,600&display=swap" rel="stylesheet">
<style>
  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    -webkit-font-smoothing: antialiased;
  }}

  body {{
    width: 1080px;
    height: 1350px;
    background-color: #FBF8F2;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    color: #0A0A0A;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    align-items: stretch;
    overflow: hidden;
  }}

  /* Top Masthead Container */
  .masthead-section {{
    width: 100%;
    padding: 18px 24px 10px 24px;
    background-color: #FBF8F2;
    display: flex;
    flex-direction: column;
    align-items: center;
    border-bottom: 2px solid #111111;
  }}

  .masthead-img {{
    width: 100%;
    max-height: 240px;
    object-fit: contain;
    display: block;
  }}

  /* Headline Section */
  .headline-section {{
    padding: 18px 26px 20px 26px;
    flex-shrink: 0;
    background-color: #FBF8F2;
  }}

  .headline-text {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    font-size: {font_size}px;
    font-weight: 700;
    line-height: 1.25;
    color: #050505;
    letter-spacing: -0.4px;
    word-break: break-word;
  }}

  /* Image Section */
  .image-wrapper {{
    flex: 1;
    width: 100%;
    position: relative;
    overflow: hidden;
    background-color: #E2DBD0;
    display: flex;
    align-items: center;
    justify-content: center;
  }}

  .news-image {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: center top;
    display: block;
  }}

  .fallback-graphic {{
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    padding: 40px;
    background: linear-gradient(135deg, #24201B 0%, #151310 100%);
    color: #F8F5EE;
    text-align: center;
  }}

  .fallback-icon {{
    font-size: 80px;
    margin-bottom: 20px;
    opacity: 0.85;
  }}

  .fallback-tag {{
    font-family: 'Inter', sans-serif;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #C5A059;
    margin-bottom: 12px;
  }}

  .fallback-subtext {{
    font-family: 'Newsreader', Georgia, serif;
    font-style: italic;
    font-size: 26px;
    color: #DDD4C5;
    max-width: 800px;
    line-height: 1.4;
  }}

  /* Watermark / Link Pill */
  .link-pill {{
    position: absolute;
    bottom: 18px;
    right: 18px;
    background: #FFFFFF;
    color: #111111;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 21px;
    font-weight: 500;
    padding: 6px 14px;
    border-radius: 6px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    letter-spacing: -0.1px;
    z-index: 10;
  }}
</style>
</head>
<body>
  <div class="masthead-section">
    <img class="masthead-img" src="data:image/png;base64,{masthead_b64}" alt="THE REPUBLIC BULLETIN">
  </div>

  <div class="headline-section">
    <h1 class="headline-text">{title}</h1>
  </div>

  <div class="image-wrapper">
    {image_element}
    <div class="link-pill">https://therepublicbulletin.com</div>
  </div>
</body>
</html>
"""

def generate_caption(article, index, total):
    date_str = "Sunday, Aug 30, 2026"
    category = (article.category or "General").upper()
    title = article.title.strip()
    
    # Split summary into bullet points
    summary_text = article.summary or article.content or ""
    # Clean HTML tags if any
    summary_text = re.sub(r'<[^>]+>', '', summary_text).strip()
    
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', summary_text) if len(s.strip()) > 15]
    if not sentences:
        bullet_points = [f"• Full story and ongoing coverage available on The Republic Bulletin."]
    else:
        bullet_points = [f"• {s}" for s in sentences[:3]]
    
    bullets_formatted = "\n".join(bullet_points)
    
    # Category hashtags
    cat_tag = re.sub(r'[^a-zA-Z0-9]', '', article.category or 'News')
    
    caption = (
        f"🗞️ THE REPUBLIC BULLETIN · {category} DISPATCH\n"
        f"📅 {date_str} | Post {index}/{total}\n\n"
        f"📌 {title}\n\n"
        f"Key Highlights:\n"
        f"{bullets_formatted}\n\n"
        f"🌐 Read the full broadsheet dispatch & analysis at therepublicbulletin.com (Link in bio)\n\n"
        f"💬 What is your view on this development? Share your thoughts in the comments below! 👇\n\n"
        f"#TheRepublicBulletin #NewsToday #DailyDispatch #BreakingNews #{cat_tag}News #IndiaNews #WorldNews #CurrentAffairs #JournalismMatters #VintageJournalism #TheRepublic"
    )
    return caption

def render_html_to_png(html_path, png_path):
    cmd = [
        CHROME_EXE,
        "--headless=new",
        f"--screenshot={png_path}",
        "--window-size=1080,1350",
        "--hide-scrollbars",
        f"file:///{html_path.replace(os.sep, '/')}"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode == 0 and os.path.exists(png_path)

def slugify(text):
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    return re.sub(r'[-\s]+', '_', text)[:40]

async def main():
    async with SessionLocal() as session:
        result = await session.execute(
            select(Article)
            .where(Article.created_at >= datetime(2026, 8, 30, 0, 0, 0))
            .order_by(Article.created_at.desc())
        )
        articles = result.scalars().all()
        total_articles = len(articles)
        print(f"🚀 Found {total_articles} articles for today (2026-08-30). Starting generation...")

        manifest = []
        tasks_to_render = []

        for idx, article in enumerate(articles, 1):
            title = article.title.strip()
            title_len = len(title)
            
            # Dynamic typography scaling
            if title_len < 55:
                font_size = 52
            elif title_len < 85:
                font_size = 46
            elif title_len < 115:
                font_size = 42
            elif title_len < 145:
                font_size = 38
            else:
                font_size = 34

            slug = slugify(title)
            file_id = f"post_{idx:02d}_id_{article.id}_{slug}"
            html_filename = f"{file_id}.html"
            png_filename = f"{file_id}.png"
            
            html_path = os.path.join(HTML_DIR, html_filename)
            png_path = os.path.join(IMAGES_DIR, png_filename)

            if article.image_url:
                image_element = f'<img class="news-image" src="{html.escape(article.image_url)}" alt="News Image">'
            else:
                category_name = (article.category or "EDITORIAL REPORT").upper()
                image_element = f"""
                <div class="fallback-graphic">
                    <div class="fallback-icon">🗞️</div>
                    <div class="fallback-tag">{category_name} SPECIAL DISPATCH</div>
                    <div class="fallback-subtext">The Republic Bulletin Special Wire Coverage &amp; Editorial Analysis</div>
                </div>
                """

            html_content = CARD_HTML_TEMPLATE.format(
                safe_title=html.escape(title),
                title=title,
                image_element=image_element,
                font_size=font_size,
                masthead_b64=MASTHEAD_B64
            )

            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            caption = generate_caption(article, idx, total_articles)

            manifest_item = {
                "index": idx,
                "id": file_id,
                "article_id": article.id,
                "title": title,
                "category": article.category,
                "created_at": str(article.created_at),
                "published_at": str(article.published_at) if article.published_at else None,
                "original_image_url": article.image_url,
                "image_filename": png_filename,
                "image_relative_path": f"images/{png_filename}",
                "image_absolute_path": png_path,
                "html_relative_path": f"html/{html_filename}",
                "caption": caption
            }
            manifest.append(manifest_item)
            tasks_to_render.append((html_path, png_path, idx, title))

        print(f"📄 Generated {len(tasks_to_render)} HTML templates. Rendering PNG screenshots with Headless Chrome...")

        # Render concurrently using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(render_html_to_png, item[0], item[1]) for item in tasks_to_render]
            for idx, (future, task) in enumerate(zip(futures, tasks_to_render), 1):
                success = future.result()
                if success:
                    print(f"  [{idx:02d}/{total_articles}] ✅ Rendered: {task[3][:50]}...")
                else:
                    print(f"  [{idx:02d}/{total_articles}] ❌ Failed: {task[3][:50]}...")

        # Save manifest.json
        manifest_path = os.path.join(OUTPUT_DIR, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved manifest to {manifest_path}")

        # Build Interactive Web Viewer
        gallery_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>The Republic Bulletin - Today's Instagram Posts (Aug 30, 2026)</title>
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@700;800;900&family=Inter:wght@400;500;600;700;800&family=Playfair+Display:ital,wght@0,700;1,400&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #121110;
    color: #F5EFE6;
    font-family: 'Inter', sans-serif;
    padding: 30px 20px 80px;
  }}
  .container {{
    max-width: 1400px;
    margin: 0 auto;
  }}
  header {{
    text-align: center;
    margin-bottom: 40px;
    padding-bottom: 25px;
    border-bottom: 2px solid #3A3226;
  }}
  h1 {{
    font-family: 'Cinzel', serif;
    font-size: 38px;
    color: #E6C587;
    letter-spacing: 2px;
    margin-bottom: 8px;
  }}
  .subtitle {{
    font-family: 'Playfair Display', serif;
    font-style: italic;
    color: #C0B4A0;
    font-size: 20px;
  }}
  .stats-bar {{
    margin-top: 15px;
    display: inline-flex;
    gap: 20px;
    background: #1E1B17;
    padding: 8px 20px;
    border-radius: 30px;
    border: 1px solid #3E372B;
    font-size: 14px;
    font-weight: 600;
  }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
    gap: 30px;
  }}
  .post-card {{
    background: #1A1713;
    border: 1px solid #332B22;
    border-radius: 12px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    box-shadow: 0 10px 30px rgba(0,0,0,0.4);
    transition: transform 0.2s, border-color 0.2s;
  }}
  .post-card:hover {{
    transform: translateY(-4px);
    border-color: #C5A059;
  }}
  .img-preview-box {{
    width: 100%;
    position: relative;
    background: #000;
    aspect-ratio: 4 / 5;
  }}
  .post-img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }}
  .card-meta {{
    padding: 20px;
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }}
  .badge-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
  }}
  .category-tag {{
    background: #8B1E0F;
    color: #FFF;
    font-size: 11px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    padding: 4px 10px;
    border-radius: 4px;
  }}
  .post-num {{
    color: #8C806D;
    font-size: 12px;
    font-weight: 600;
  }}
  .post-title {{
    font-family: 'Playfair Display', serif;
    font-size: 18px;
    line-height: 1.35;
    margin-bottom: 15px;
    color: #F8F5EE;
  }}
  .caption-preview {{
    background: #100E0C;
    border: 1px solid #2B241C;
    border-radius: 6px;
    padding: 12px;
    font-size: 12px;
    line-height: 1.45;
    color: #B5AB9B;
    max-height: 110px;
    overflow-y: auto;
    white-space: pre-wrap;
    margin-bottom: 15px;
    font-family: monospace;
  }}
  .actions-row {{
    display: flex;
    gap: 10px;
  }}
  .btn {{
    flex: 1;
    padding: 10px;
    border-radius: 6px;
    border: none;
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    text-align: center;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    transition: background 0.2s, opacity 0.2s;
  }}
  .btn-copy {{
    background: #C5A059;
    color: #12100E;
  }}
  .btn-copy:hover {{
    background: #DEC282;
  }}
  .btn-download {{
    background: #2D2720;
    color: #F8F5EE;
    border: 1px solid #443B30;
  }}
  .btn-download:hover {{
    background: #3D352B;
  }}
  .btn-copied {{
    background: #27AE60 !important;
    color: #FFF !important;
  }}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>THE REPUBLIC BULLETIN</h1>
    <p class="subtitle">Official Instagram Post Dispatch · Sunday, August 30, 2026</p>
    <div class="stats-bar">
      <span>📸 Total Posts: {total_articles}</span>
      <span>📐 Aspect Ratio: 4:5 (1080×1350)</span>
      <span>📰 Status: Ready for Publishing</span>
    </div>
  </header>
  
  <div class="grid">
"""
        for item in manifest:
            safe_caption = html.escape(item["caption"])
            safe_title = html.escape(item["title"])
            category = html.escape(item["category"] or "General")
            
            gallery_html += f"""
    <div class="post-card">
      <div class="img-preview-box">
        <img class="post-img" src="{item['image_relative_path']}" alt="{safe_title}" loading="lazy">
      </div>
      <div class="card-meta">
        <div>
          <div class="badge-row">
            <span class="category-tag">{category}</span>
            <span class="post-num">Post #{item['index']:02d} (ID: {item['article_id']})</span>
          </div>
          <h2 class="post-title">{safe_title}</h2>
          <div class="caption-preview" id="caption-{item['index']}">{safe_caption}</div>
        </div>
        <div class="actions-row">
          <button class="btn btn-copy" onclick="copyCaption({item['index']}, this)">📋 Copy Caption</button>
          <a class="btn btn-download" href="{item['image_relative_path']}" download="{item['image_filename']}">⬇️ Download</a>
        </div>
      </div>
    </div>
"""

        gallery_html += """
  </div>
</div>

<script>
function copyCaption(idx, btn) {
  const text = document.getElementById('caption-' + idx).innerText;
  navigator.clipboard.writeText(text).then(() => {
    const orig = btn.innerHTML;
    btn.innerHTML = '✅ Copied!';
    btn.classList.add('btn-copied');
    setTimeout(() => {
      btn.innerHTML = orig;
      btn.classList.remove('btn-copied');
    }, 2000);
  });
}
</script>
</body>
</html>
"""
        gallery_path = os.path.join(OUTPUT_DIR, "index.html")
        with open(gallery_path, "w", encoding="utf-8") as f:
            f.write(gallery_html)
        print(f"✨ Interactive Post Gallery created at: {gallery_path}")

if __name__ == "__main__":
    asyncio.run(main())
