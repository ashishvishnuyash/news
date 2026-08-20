from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests

from config import Settings
from publisher import PublicationLedger, SiteClient
from rewriter import OpenRouterRewriter, build_source_fallback
from sources import IndiaPublisherRSSSource


BASE_DIR = Path(__file__).resolve().parent
STATUS_CHOICES = ("DRAFT", "SUBMITTED", "PUBLISHED")


def configure_console() -> None:
    # Windows may default to a legacy code page that crashes on Indian currency
    # symbols or names. Replacement is preferable to aborting a publication run.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")


def parse_local_datetime(value: str, zone: ZoneInfo) -> datetime:
    value = value.strip()
    for pattern in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, pattern).replace(tzinfo=zone)
        except ValueError:
            pass
    raise ValueError("Use YYYY-MM-DD HH:MM (or YYYY-MM-DD)")


def prompt_datetime(label: str, default: datetime, zone: ZoneInfo) -> datetime:
    rendered = default.strftime("%Y-%m-%d %H:%M")
    while True:
        value = input(f"{label} [{rendered}]: ").strip() or rendered
        try:
            return parse_local_datetime(value, zone)
        except ValueError as exc:
            print(f"  {exc}")


def prompt_choice(label: str, choices: tuple[str, ...], default: str) -> str:
    options = "/".join(choices)
    while True:
        value = (input(f"{label} ({options}) [{default}]: ").strip() or default).upper()
        if value in choices:
            return value
        print(f"  Choose one of: {options}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Discover India-focused news, rewrite it, and post it to the site.")
    parser.add_argument("--date", help="One complete local date, e.g. 2026-08-05")
    parser.add_argument("--start", help='Start in local time, e.g. "2026-08-04 09:00"')
    parser.add_argument("--end", help='End in local time, e.g. "2026-08-05 09:00"')
    parser.add_argument("--max-articles", type=int, help="Maximum number of source stories")
    parser.add_argument("--status", choices=[item.lower() for item in STATUS_CHOICES], help="Final site status")
    parser.add_argument("--yes", action="store_true", help="Post each result without a per-article confirmation")
    parser.add_argument("--non-interactive", action="store_true", help="Require all range options; never prompt")
    return parser


def choose_options(args: argparse.Namespace, settings: Settings) -> tuple[datetime, datetime, int, str]:
    try:
        zone = ZoneInfo(settings.timezone)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown DEFAULT_TIMEZONE: {settings.timezone}") from exc
    now = datetime.now(zone).replace(second=0, microsecond=0)

    if args.date and (args.start or args.end):
        raise ValueError("Use either --date or --start/--end, not both")
    has_range = bool(args.start and args.end)
    if args.non_interactive and (not args.date and not has_range or not args.status):
        raise ValueError("--non-interactive requires --date or --start/--end, plus --status")

    if args.date:
        try:
            start = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=zone)
        except ValueError as exc:
            raise ValueError("--date must use YYYY-MM-DD") from exc
        end = start + timedelta(days=1) - timedelta(microseconds=1)
    elif args.start or args.end:
        if not has_range:
            raise ValueError("--start and --end must be supplied together")
        start = parse_local_datetime(args.start, zone)
        end = parse_local_datetime(args.end, zone)
    else:
        mode = prompt_choice("Range type", ("DATE", "INTERVAL"), "INTERVAL")
        if mode == "DATE":
            while True:
                value = input(f"Date [{now:%Y-%m-%d}]: ").strip() or now.strftime("%Y-%m-%d")
                try:
                    start = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=zone)
                    end = start + timedelta(days=1) - timedelta(microseconds=1)
                    break
                except ValueError:
                    print("  Use YYYY-MM-DD")
        else:
            start = prompt_datetime("Start date/time", now - timedelta(days=1), zone)
            end = prompt_datetime("End date/time", now, zone)
    if start >= end:
        raise ValueError("Start date/time must be before end date/time")

    maximum = args.max_articles
    if maximum is None:
        if args.non_interactive:
            maximum = settings.max_articles
        else:
            raw = input(f"Maximum articles [{settings.max_articles}]: ").strip()
            maximum = int(raw or settings.max_articles)
    if not 1 <= maximum <= 50:
        raise ValueError("Maximum articles must be between 1 and 50")
    status = args.status.upper() if args.status else prompt_choice("Post as", STATUS_CHOICES, "DRAFT")
    return start, end, maximum, status


def run() -> int:
    configure_console()
    args = build_parser().parse_args()
    try:
        settings = Settings()
        start, end, maximum, status = choose_options(args, settings)
        if not settings.openrouter_api_key:
            raise ValueError("Set OPENROUTER_API_KEY in AIJournalist/.env")

        print(f"\nSearching India-focused news from {start.isoformat()} to {end.isoformat()} ...")
        source = IndiaPublisherRSSSource(timeout=settings.timeout)
        discovered = source.discover(start, end, 200)
        if not discovered:
            print("No matching stories were found in that exact time range.")
            return 0

        site = SiteClient(
            settings.site_api_url,
            settings.site_username,
            settings.site_password,
            settings.timeout,
        )
        user = site.login()
        role = str(user["role"]).upper()
        if role not in {"JOURNALIST", "ADMIN", "SUPER_ADMIN"}:
            raise ValueError(f"Site role {role} cannot create articles; use a journalist or admin account")
        if status == "PUBLISHED" and role not in {"ADMIN", "SUPER_ADMIN"}:
            raise ValueError("Publishing directly requires an ADMIN or SUPER_ADMIN site account")
        categories = site.categories()
        print(f"Authenticated as {user['username']} ({role}); found {len(discovered)} NDTV/TOI RSS articles.")
        rewriter = OpenRouterRewriter(
            settings.openrouter_api_key,
            settings.openrouter_model,
            settings.timeout,
            settings.openrouter_site_url,
            settings.openrouter_app_name,
        )
        ledger = PublicationLedger(BASE_DIR / "publications.sqlite3")
        posted = skipped = failed = 0
        try:
            extracted = []
            for candidate in discovered:
                if ledger.contains(candidate):
                    skipped += 1
                    continue
                print(f"Extracting: {candidate.title}")
                source.enrich(candidate)
                extracted.append(candidate)
            print(f"Extraction complete; {len(extracted)} article(s) are ready for rewriting.")

            for candidate in extracted:
                if posted >= maximum:
                    break
                print(f"\nSource: {candidate.title}\n  {candidate.source_name} · {candidate.published_at.isoformat()}")
                actual_status = status
                try:
                    rewritten = rewriter.rewrite(candidate, categories or None)
                except Exception as exc:
                    failed += 1
                    rewritten = build_source_fallback(candidate, categories or None)
                    actual_status = "DRAFT"
                    print(f"AI rewrite failed; using an attributed source-excerpt draft: {exc}", file=sys.stderr)
                print(f"Rewrite: {rewritten.title}\n  {rewritten.summary}")
                if not args.yes and not args.non_interactive:
                    answer = input(f"Post this as {actual_status}? [y/N]: ").strip().lower()
                    if answer not in {"y", "yes"}:
                        skipped += 1
                        continue
                try:
                    result = site.post(rewritten, candidate, actual_status)
                    ledger.record(candidate, int(result["id"]), str(result["status"]))
                    posted += 1
                    print(f"Posted article #{result['id']} with status {result['status']}.")
                except Exception as exc:
                    failed += 1
                    print(f"Posting failed: {exc}", file=sys.stderr)
        finally:
            ledger.close()

        print(f"\nDone: {posted} posted, {skipped} skipped, {failed} failed.")
        return 0 if failed == 0 or posted > 0 else 1
    except (ValueError, RuntimeError, OSError, requests.RequestException) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nCancelled; no further articles will be posted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(run())
