from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.markdown import Markdown
from ui_components import (
    print_masthead, print_header_strip, format_menu_options,
    print_error, print_success, print_info, render_status_badge,
    safe_str, safe_upper
)

console = Console()

def render_editor_screen(api, state):
    print_masthead(title="EDITORIAL REVIEW BOARD", motto="SUBMISSION QUEUE & PROOFING DESK")
    print_header_strip(api.current_user, current_screen="EDITORIAL DESK")

    status_filter = state.get("editor_status_filter", "SUBMITTED")
    
    console.print(f"\n[bold yellow]EDITORIAL REVIEW QUEUE [ Filter: [bold gold1]{status_filter}[/bold gold1] ]:[/bold yellow]\n")

    ok, queue = api.get_editor_queue(status_filter=None if status_filter == "ALL" else status_filter)
    if not ok or not isinstance(queue, list):
        if not ok:
            print_error(queue)
        queue = []

    if not queue:
        console.print(Panel(f"[italic white center]No dispatches found in the queue matching status filter '{status_filter}'.[/italic white center]", style="dim white"))
    else:
        table = Table(show_header=True, header_style="bold cyan", expand=True)
        table.add_column("ID", style="bold yellow", width=4)
        table.add_column("STATUS", width=14)
        table.add_column("SECTION", style="bold red", width=12)
        table.add_column("HEADLINE & ABSTRACT", style="bold white")
        table.add_column("SCRIBE", style="cyan", width=14)
        table.add_column("SUBMITTED ON", style="dim white", width=12)

        for art in queue:
            author_u = safe_upper((art.get("author") or {}).get("username"), "STAFF")
            art_cat = safe_upper(art.get("category"), "TECH")
            art_title = safe_str(art.get("title"), "Untitled")
            art_summary = safe_str(art.get("summary"))
            art_created = safe_str(art.get("created_at"))
            
            table.add_row(
                str(art.get("id", "")),
                render_status_badge(art.get("status")),
                art_cat,
                f"[bold white]{art_title}[/bold white]\n[italic dim]{art_summary[:80]}[/italic dim]",
                author_u,
                art_created[:10]
            )
        console.print(table)

    menu_options = [
        ("V", "VIEW PROOF & REVIEW", "Open proofing view to approve/publish or reject dispatch"),
        ("F", "FILTER QUEUE", "Filter queue by status (SUBMITTED, DRAFT, PUBLISHED, REJECTED, ALL)"),
        ("H", "REVIEW HISTORY", "Check past editorial notes & review decisions"),
        ("B", "BACK TO BROADSHEET", "Return to public front page view"),
        ("Q", "QUIT TERMINAL", "Exit application")
    ]
    format_menu_options(menu_options)

    cmd = Prompt.ask("Command Input", choices=["v", "V", "f", "F", "h", "H", "b", "B", "q", "Q"]).lower()

    if cmd == "v":
        art_id = Prompt.ask("Enter Dispatch ID to Review")
        if not art_id.isdigit():
            print_error("Invalid ID.")
        else:
            target_art = next((a for a in queue if str(a.get("id")) == art_id), None)
            if not target_art:
                ok_all, all_q = api.get_editor_queue(status_filter=None)
                if ok_all and isinstance(all_q, list):
                    target_art = next((a for a in all_q if str(a.get("id")) == art_id), None)

            if not target_art:
                print_error("Dispatch not found in review queue.")
            else:
                render_editorial_proof(api, target_art)

    elif cmd == "f":
        console.print("\n[bold cyan]Select Status Filter:[/bold cyan]")
        console.print("1. SUBMITTED (Awaiting Review)")
        console.print("2. DRAFT (Work in progress)")
        console.print("3. PUBLISHED (Live on Front Page)")
        console.print("4. REJECTED (Sent back to scribe)")
        console.print("5. ALL DISPATCHES")
        choice = Prompt.ask("Choose Status", choices=["1", "2", "3", "4", "5"], default="1")
        st_map = {"1": "SUBMITTED", "2": "DRAFT", "3": "PUBLISHED", "4": "REJECTED", "5": "ALL"}
        state["editor_status_filter"] = st_map[choice]

    elif cmd == "h":
        art_id = Prompt.ask("Enter Dispatch ID to view review audit log")
        if art_id.isdigit():
            ok_rev, reviews = api.get_article_reviews(int(art_id))
            if ok_rev and reviews and isinstance(reviews, list):
                console.print(f"\n[bold yellow]EDITORIAL AUDIT LOG FOR DISPATCH #{art_id}:[/bold yellow]")
                for r in reviews:
                    editor_u = safe_upper((r.get("editor") or {}).get("username"), "EDITOR")
                    r_status = safe_str(r.get("status"))
                    r_created = safe_str(r.get("created_at"))
                    r_notes = safe_str(r.get("editorial_notes"), "No notes entered.")
                    console.print(f"[bold cyan]• {editor_u}[/bold cyan] -> [{r_status}] on [dim]{r_created[:16]}[/dim]:")
                    console.print(f"  [italic white]\"{r_notes}\"[/italic white]\n")
            else:
                print_info("No review audit logs found.")
        else:
            print_error("Invalid ID.")

    elif cmd == "b":
        return "BROADSHEET"
    elif cmd == "q":
        return "QUIT"

    return "EDITOR"


def render_editorial_proof(api, article):
    console.print("\n[bold gold1]" + "=" * 90 + "[/bold gold1]")
    console.print("[bold yellow center]EDITORIAL PROOF & BROADCAST AUDIT[/bold yellow center]")
    console.print("[bold gold1]" + "=" * 90 + "[/bold gold1]\n")

    art_cat = safe_upper(article.get("category"), "GENERAL")
    art_status = safe_str(article.get("status"))
    art_title = safe_upper(article.get("title"), "UNTITLED DISPATCH")
    art_summary = safe_str(article.get("summary"))
    author_str = safe_upper((article.get("author") or {}).get("username"), "STAFF")
    art_created = safe_str(article.get("created_at"))

    console.print(f"[bold red]SECTION: {art_cat}[/bold red]  •  [bold white]STATUS: {art_status}[/bold white]")
    console.print(f"[bold white font=serif font_size=20]{art_title}[/bold white font=serif font_size=20]")
    if art_summary:
        console.print(f"[italic gold1]{art_summary}[/italic gold1]")
    
    console.print(f"[dim white]SCRIBE: {author_str}  |  CREATED: {art_created[:16]}[/dim white]\n")

    content = safe_str(article.get("content"))
    console.print(Panel(Markdown(content), title="[bold white]FULL ARTICLE CONTENT PROOF[/bold white]", border_style="bold cyan"))

    console.print("\n[bold yellow]EDITORIAL DECISION MENU:[/bold yellow]")
    console.print("1. [bold green]✓ APPROVE & PUBLISH TO FRONT PAGE[/bold green]")
    console.print("2. [bold red]X REJECT WITH EDITORIAL FEEDBACK[/bold red]")
    console.print("3. CANCEL & RETURN TO QUEUE")

    choice = Prompt.ask("Action Choice", choices=["1", "2", "3"], default="1")

    if choice == "1":
        notes = Prompt.ask("Approval / Publication Note (optional)", default="Approved for immediate front page publication.")
        ok, msg = api.review_article(article["id"], "PUBLISHED", notes)
        if ok:
            print_success(f"Dispatch #{article['id']} APPROVED and PUBLISHED to Front Page!")
        else:
            print_error(msg)
    elif choice == "2":
        notes = Prompt.ask("Rejection Feedback & Required Revisions")
        if not notes.strip():
            notes = "Revision required. Please review facts and summary."
        ok, msg = api.review_article(article["id"], "REJECTED", notes)
        if ok:
            print_success(f"Dispatch #{article['id']} REJECTED and returned to scribe with feedback.")
        else:
            print_error(msg)
