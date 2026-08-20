# AIJournalist

AIJournalist reads the India RSS feeds published by NDTV and The Times of India, keeps only stories inside the exact date/time interval you select, extracts every matching linked report before rewriting, uses OpenRouter's `openrouter/free` router through the `OpenRouter` Python SDK, and posts selected stories to The Republic Bulletin API.

Every post includes a link and timestamp for the original source. The default status is `DRAFT`, so a human can verify facts before publication.

## Web control desk

Start the local dashboard:

```powershell
cd D:\NeWS\AIJournalist
.\.venv\Scripts\Activate.ps1
python dashboard.py
```

Your browser opens at `http://127.0.0.1:8787`. The dashboard lets you:

- choose one Indian calendar date or an exact time interval;
- watch discovery, extraction, and rewriting progress;
- cancel safely between reports;
- read and select rewritten previews;
- review long-form Markdown and download each story as an `.md` file;
- preview RSS/Open Graph lead images and attach them to site articles;
- send selected stories as drafts, editorial submissions, or direct publications;
- inspect failures and the complete activity log.

The dashboard binds only to the local computer. API keys and site passwords remain in `.env` and are never returned to the browser. Jobs are held in memory, so restarting the dashboard clears previews but keeps the duplicate-publication ledger.

Generated stories target 800-1,200 words with a substantial 60-100 word summary. Markdown is the canonical generated format. When a story is sent to the existing site, it is converted to sanitized HTML so headings, paragraphs, emphasis, and lists render correctly.

`SITE_API_URL` accepts either `http://localhost:8000` or `http://localhost:8000/api`. Restart the dashboard after changing `.env`.

## Setup

Use Python 3.10 or newer. The site backend must already be running. Use a site account with the appropriate role:

- `JOURNALIST`: can create `DRAFT` or `SUBMITTED` articles.
- `ADMIN` or `SUPER_ADMIN`: can also create articles and set `PUBLISHED`.
- `EDITOR`: cannot create a new article with the current site API, so use a journalist/admin account.

From PowerShell:

```powershell
cd D:\NeWS\AIJournalist
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and provide `OPENROUTER_API_KEY`, `SITE_USERNAME`, and `SITE_PASSWORD`. The `.env` file and local publication ledger are ignored by Git.

## Run interactively

The command-line interface remains available:

```powershell
python main.py
```

The script asks for:

1. A complete date or a precise time interval in Indian time
2. Start/end times when interval mode is selected (`YYYY-MM-DD HH:MM`)
3. Maximum number of articles
4. Final status: `DRAFT`, `SUBMITTED`, or `PUBLISHED`
5. Confirmation before each article is posted

For one complete calendar date, choose `DATE` at the first prompt. Choose `INTERVAL` for precise start and end times.

## Run unattended

```powershell
python main.py --start "2026-08-04 09:00" --end "2026-08-05 09:00" --max-articles 5 --status submitted --yes --non-interactive
```

Or process one complete Indian calendar date:

```powershell
python main.py --date 2026-08-05 --max-articles 5 --status draft --yes --non-interactive
```

The SQLite ledger at `publications.sqlite3` prevents the same source URL from being posted twice. Delete a ledger row deliberately if a story needs to be reprocessed; do not delete the whole ledger during normal operation.

## Important editorial limits

- NDTV and Times of India may block or limit direct page extraction. The workflow then uses Jina Reader to recover the article as Markdown, and uses RSS text only if both full-page routes fail.
- If AI rewriting fails, the tool creates a clearly marked, draft-only internal copy containing the extracted article and attribution. It cannot be submitted or published automatically and must be rewritten or cleared by an editor.
- Free OpenRouter model availability can change. Override `OPENROUTER_MODEL` in `.env` if `openrouter/free` is unavailable.
- Rewriting is not fact-checking. Review names, numbers, quotations, image rights, and breaking-news updates before publishing.
- Source-provided lead images are attached by URL with an attribution/rights-review caption. Confirm reuse rights before publication.

## Tests

```powershell
pip install -r requirements-dev.txt
python -m pytest -q
```
