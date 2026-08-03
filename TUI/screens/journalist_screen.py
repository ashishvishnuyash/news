from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from ui_components import (
    print_masthead, print_header_strip, format_menu_options,
    print_error, print_success, print_info, render_status_badge,
    safe_str, safe_upper
)

console = Console()

def render_journalist_screen(api, state):
    print_masthead(title="PRESS CORRESPONDENT WORKSPACE", motto="CORRESPONDENCE & DRAFTING DESK")
    print_header_strip(api.current_user, current_screen="JOURNALIST DESK")

    ok, my_articles = api.get_my_articles()
    if not ok or not isinstance(my_articles, list):
        if not ok:
            print_error(my_articles)
        my_articles = []

    console.print(f"\n[bold yellow]MY FILED DISPATCHES & DRAFTS ({len(my_articles)}):[/bold yellow]\n")

    if not my_articles:
        console.print(Panel("[italic white center]No dispatches authored yet. Use 'NEW' command to draft a new broadside chronicle.[/italic white center]", style="dim white"))
    else:
        table = Table(show_header=True, header_style="bold cyan", expand=True)
        table.add_column("ID", style="bold yellow", width=4)
        table.add_column("STATUS", width=14)
        table.add_column("SECTION", style="bold red", width=12)
        table.add_column("HEADLINE & SUMMARY", style="bold white")
        table.add_column("CREATED", style="dim white", width=12)

        for art in my_articles:
            art_cat = safe_upper(art.get("category"), "TECH")
            art_title = safe_str(art.get("title"), "Untitled")
            art_summary = safe_str(art.get("summary"))
            art_created = safe_str(art.get("created_at"))
            
            table.add_row(
                str(art.get("id", "")),
                render_status_badge(art.get("status")),
                art_cat,
                f"[bold white]{art_title}[/bold white]\n[italic dim]{art_summary[:80]}[/italic dim]",
                art_created[:10]
            )
        console.print(table)

    menu_options = [
        ("N", "NEW DISPATCH", "Draft & compose a new chronicle dispatch"),
        ("E", "EDIT DRAFT", "Modify title, summary, or content of a draft dispatch"),
        ("S", "SUBMIT FOR REVIEW", "Submit draft dispatch to Editorial Review Board"),
        ("R", "VIEW REVIEWS", "Check editor notes & decision history for a dispatch"),
        ("B", "BACK TO BROADSHEET", "Return to public front page view"),
        ("Q", "QUIT TERMINAL", "Exit application")
    ]
    format_menu_options(menu_options)

    cmd = Prompt.ask("Command Input", choices=["n", "N", "e", "E", "s", "S", "r", "R", "b", "B", "q", "Q"]).lower()

    if cmd == "n":
        console.print("\n[bold gold1]═" * 60 + "[/bold gold1]")
        console.print("[bold yellow center]COMPOSE NEW BROADSIDE DISPATCH[/bold yellow center]")
        console.print("[bold gold1]═" * 60 + "[/bold gold1]\n")
        
        title = Prompt.ask("Headline Title")
        summary = Prompt.ask("Abstract Summary")
        
        ok_set, settings = api.get_settings()
        cats = settings.get("categories", ["Politics", "World", "Economy", "Tech", "Culture", "Opinion"]) if ok_set and settings else ["Tech", "Politics"]
        console.print(f"Categories: {', '.join(cats)}")
        category = Prompt.ask("Select Section", default=cats[0])
        
        console.print("\n[bold cyan]Enter Article Content (multi-line supported, type 'END' on a new line when done):[/bold cyan]")
        lines = []
        while True:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)
        content = "\n".join(lines)
        
        image_url = Prompt.ask("Photograph Image URL (optional)", default="")
        tags = Prompt.ask("Tags (comma separated, optional)", default="")
        
        if not title or not content:
            print_error("Headline and Content cannot be empty!")
        else:
            ok_cr, res = api.create_article(title, summary, category, content, image_url, tags)
            if ok_cr and isinstance(res, dict):
                print_success(f"Dispatch created successfully! ID: {res.get('id')} (Status: {res.get('status')})")
                sub = Prompt.ask("Submit immediately for editorial review?", choices=["y", "n"], default="y")
                if sub.lower() == "y":
                    ok_sub, sub_msg = api.submit_article(res['id'])
                    if ok_sub:
                        print_success("Dispatch submitted to Editorial Board!")
                    else:
                        print_error(sub_msg)
            else:
                print_error(res)

    elif cmd == "e":
        art_id = Prompt.ask("Enter Dispatch ID to Edit")
        if not art_id.isdigit():
            print_error("Invalid ID.")
        else:
            target_art = next((a for a in my_articles if str(a.get("id")) == art_id), None)
            if not target_art:
                print_error("Article not found in your filed list.")
            elif target_art.get("status") not in ("DRAFT", "REJECTED"):
                print_error("Only DRAFT or REJECTED articles can be edited.")
            else:
                console.print(f"\nEditing Dispatch #{art_id}: {target_art.get('title')}")
                new_title = Prompt.ask("Headline Title", default=safe_str(target_art.get("title")))
                new_summary = Prompt.ask("Abstract Summary", default=safe_str(target_art.get("summary")))
                new_cat = Prompt.ask("Category", default=safe_str(target_art.get("category"), "Tech"))
                console.print("\n[bold cyan]Update Content (type 'END' on new line to keep existing or finish):[/bold cyan]")
                lines = []
                while True:
                    line = input()
                    if line.strip() == "END":
                        break
                    lines.append(line)
                new_content = "\n".join(lines) if lines else safe_str(target_art.get("content"))
                
                payload = {
                    "title": new_title,
                    "summary": new_summary,
                    "category": new_cat,
                    "content": new_content
                }
                ok_up, up_msg = api.update_article(target_art["id"], payload)
                if ok_up:
                    print_success("Dispatch updated successfully.")
                else:
                    print_error(up_msg)

    elif cmd == "s":
        art_id = Prompt.ask("Enter Dispatch ID to Submit for Review")
        if art_id.isdigit():
            ok_sub, sub_msg = api.submit_article(int(art_id))
            if ok_sub:
                print_success("Dispatch submitted to Editorial Review Board!")
            else:
                print_error(sub_msg)
        else:
            print_error("Invalid ID.")

    elif cmd == "r":
        art_id = Prompt.ask("Enter Dispatch ID to view editor reviews")
        if art_id.isdigit():
            ok_rev, reviews = api.get_article_reviews(int(art_id))
            if ok_rev and reviews and isinstance(reviews, list):
                console.print(f"\n[bold yellow]REVIEW HISTORY FOR DISPATCH #{art_id}:[/bold yellow]")
                for r in reviews:
                    editor_u = safe_upper((r.get("editor") or {}).get("username"), "EDITOR")
                    r_status = safe_str(r.get("status"))
                    r_created = safe_str(r.get("created_at"))
                    r_notes = safe_str(r.get("editorial_notes"), "No notes provided.")
                    console.print(f"[bold cyan]• {editor_u}[/bold cyan] ({r_status}) on [dim]{r_created[:16]}[/dim]:")
                    console.print(f"  [italic white]\"{r_notes}\"[/italic white]\n")
            else:
                print_info("No review logs found for this dispatch.")
        else:
            print_error("Invalid ID.")

    elif cmd == "b":
        return "BROADSHEET"
    elif cmd == "q":
        return "QUIT"

    return "JOURNALIST"
