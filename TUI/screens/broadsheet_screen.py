from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.markdown import Markdown
from ui_components import (
    print_masthead, print_header_strip, print_ticker,
    format_menu_options, print_error, print_success, print_info,
    safe_str, safe_upper
)

console = Console()

def render_broadsheet_screen(api, state):
    ok_set, settings = api.get_settings()
    if not ok_set or not settings:
        settings = {"title": "The Republic Bulletin", "motto": "The Voice of Truth", "categories": ["Politics", "World", "Economy", "Tech", "Culture", "Opinion"]}
        
    print_masthead(settings.get("title"), settings.get("motto"))
    print_header_strip(api.current_user, current_screen="PUBLIC BROADSHEET FRONT PAGE")
    print_ticker(settings)

    # Category Bar
    cats = settings.get("categories") or ["Politics", "World", "Economy", "Tech", "Culture", "Opinion"]
    cat_str = " | ".join([f"[bold yellow]{safe_upper(c)}[/bold yellow]" for c in cats])
    console.print(f"\n[bold white center]SECTIONS: [ [bold gold1]ALL[/bold gold1] | {cat_str} ][/bold white center]\n")

    # Fetch published articles
    category_filter = state.get("category_filter")
    search_query = state.get("search_query")
    
    ok_art, articles = api.get_articles(category=category_filter, search=search_query)
    if not ok_art or not articles:
        console.print(Panel("[italic white center]No broadside dispatches filed matching the query criteria.[/italic white center]", style="dim white"))
    else:
        # Render Lead Article and Secondary Articles
        lead = articles[0]
        lead_summary = safe_str(lead.get("summary"))
        lead_author = safe_upper((lead.get("author") or {}).get("username"), "STAFF")
        lead_date = safe_str(lead.get("published_at") or lead.get("created_at"))
        lead_cat = safe_upper(lead.get("category"), "GENERAL")
        lead_title = safe_upper(lead.get("title"), "UNTITLED DISPATCH")
        
        console.print(Panel(
            f"[bold red]★ FRONT PAGE LEAD DISPATCH [{lead_cat}][/bold red]\n\n"
            f"[bold white font=serif font_size=18]{lead_title}[/bold white font=serif font_size=18]\n"
            f"[italic gold1]{lead_summary}[/italic gold1]\n\n"
            f"[dim white]SCRIBE: {lead_author}  •  PRINTED: {lead_date[:10]}  •  VIEWS: {lead.get('view_count', 0)}  •  SLUG: {lead.get('slug', '')}[/dim white]",
            border_style="bold gold1",
            expand=True
        ))

        # Secondary Grid Table
        if len(articles) > 1:
            console.print("\n[bold gold1]LATEST EDITION DISPATCHES:[/bold gold1]")
            table = Table(show_header=True, header_style="bold cyan", expand=True)
            table.add_column("#", style="bold yellow", width=4)
            table.add_column("SECTION", style="bold red", width=12)
            table.add_column("HEADLINE & SUMMARY", style="bold white")
            table.add_column("SCRIBE", style="cyan", width=14)
            table.add_column("READS", style="bold green", width=8)
            table.add_column("SLUG / ID", style="dim white", width=25)

            for idx, art in enumerate(articles[1:], start=2):
                art_cat = safe_upper(art.get("category"), "TECH")
                art_title = safe_str(art.get("title"), "Untitled")
                art_summary = safe_str(art.get("summary"))
                art_author = safe_upper((art.get("author") or {}).get("username"), "STAFF")
                art_slug = safe_str(art.get("slug"))
                
                table.add_row(
                    str(idx),
                    art_cat,
                    f"[bold white]{art_title}[/bold white]\n[italic dim]{art_summary[:80]}...[/italic dim]",
                    art_author,
                    str(art.get("view_count", 0)),
                    art_slug
                )
            console.print(table)

    # Menu commands
    menu_options = [
        ("R", "READ DISPATCH", "Open & read full article broadside by index # or slug"),
        ("C", "CATEGORY FILTER", "Filter front page by category section"),
        ("S", "SEARCH ARCHIVES", "Search dispatches by key phrase"),
        ("L", "PRESS LOGIN", "Sign in with staff credentials / role selection"),
        ("P", "STAFF DOSSIER", "View & edit subscriber / staff profile"),
        ("D", "SWITCH DESK", "Open role control panel (Super Admin, Admin, Editor, Journalist)"),
        ("Q", "QUIT TERMINAL", "Exit The Republic Bulletin TUI application")
    ]
    format_menu_options(menu_options)

    cmd = Prompt.ask("Command Input", choices=["r", "R", "c", "C", "s", "S", "l", "L", "p", "P", "d", "D", "q", "Q"]).lower()

    if cmd == "r":
        target = Prompt.ask("Enter article number (1, 2...) or slug")
        slug_to_open = None
        if target.isdigit() and ok_art and articles:
            idx = int(target) - 1
            if 0 <= idx < len(articles):
                slug_to_open = articles[idx].get("slug")
        else:
            slug_to_open = target
            
        if slug_to_open:
            render_article_detail(api, slug_to_open)
        else:
            print_error("Invalid dispatch index or slug.")
            
    elif cmd == "c":
        cats_list = ["ALL"] + (settings.get("categories") or ["Politics", "World", "Economy", "Tech", "Culture", "Opinion"])
        console.print(f"Available sections: {', '.join(cats_list)}")
        selected = Prompt.ask("Select Section", default="ALL")
        state["category_filter"] = None if selected.upper() == "ALL" else selected
        
    elif cmd == "s":
        q = Prompt.ask("Search term (leave empty to clear)", default="")
        state["search_query"] = q if q.strip() else None

    elif cmd == "l":
        return "AUTH"

    elif cmd == "p":
        if not api.current_user:
            print_error("You must log in to view your dossier.")
        else:
            return "PROFILE"

    elif cmd == "d":
        if not api.current_user:
            print_error("Log in first to switch to a staff desk.")
        else:
            role = safe_str(api.current_user.get("role"))
            if role == "SUPER_ADMIN":
                return "SUPERADMIN"
            elif role == "ADMIN":
                return "ADMIN"
            elif role == "EDITOR":
                return "EDITOR"
            elif role == "JOURNALIST":
                return "JOURNALIST"
            else:
                print_info("Your account has READER credentials. You are currently on the Front Page desk.")

    elif cmd == "q":
        return "QUIT"

    return "BROADSHEET"


def render_article_detail(api, slug):
    ok, article = api.get_article(slug)
    if not ok or not article:
        print_error("Could not retrieve dispatch proof.")
        return

    art_cat = safe_upper(article.get("category"), "GENERAL")
    art_title = safe_upper(article.get("title"), "UNTITLED DISPATCH")
    art_summary = safe_str(article.get("summary"))
    author_str = safe_upper((article.get("author") or {}).get("username"), "UNKNOWN")
    editor_str = safe_upper((article.get("editor") or {}).get("username"), "N/A")
    date_str = safe_str(article.get("published_at") or article.get("created_at"))

    console.print("\n[bold gold1]" + "=" * 90 + "[/bold gold1]")
    console.print(f"[bold red]SECTION: {art_cat}[/bold red]")
    console.print(f"[bold white font=serif font_size=20]{art_title}[/bold white font=serif font_size=20]")
    if art_summary:
        console.print(f"[italic gold1]{art_summary}[/italic gold1]")
    
    console.print(f"[dim white]SCRIBE: {author_str}  |  EDITOR: {editor_str}  |  PRINTED: {date_str[:16]}  |  READS: {article.get('view_count', 0)}[/dim white]")
    console.print("[bold gold1]" + "=" * 90 + "[/bold gold1]\n")

    # Render body content inside Panel
    content = safe_str(article.get("content"))
    console.print(Panel(Markdown(content), title="[bold white]FULL ARTICLE CONTENT PROOF[/bold white]", border_style="bold white"))

    # Render Comments
    ok_com, comments = api.get_comments(slug)
    comments_list = comments if ok_com and isinstance(comments, list) else []
    console.print(f"\n[bold yellow]READER RESPONSES ({len(comments_list)} FILED):[/bold yellow]")
    
    if not comments_list:
        console.print("[italic dim]No public responses recorded yet.[/italic dim]")
    else:
        for c in comments_list:
            user_info = c.get("author") or {}
            uname = safe_upper(user_info.get("username"), "ANONYMOUS")
            urole = safe_str(user_info.get("role"), "READER")
            cdate = safe_str(c.get("created_at"))[:16]
            console.print(f"[bold cyan]• {uname} ({urole})[/bold cyan] [dim]filed at {cdate}:[/dim]")
            console.print(f"  [white]{safe_str(c.get('content'))}[/white]\n")

    # Comment prompt
    console.print("\n[bold cyan]ACTIONS:[/bold cyan] [1] Post Response  [2] Return to Front Page")
    action = Prompt.ask("Choice", choices=["1", "2"], default="2")
    if action == "1":
        if not api.current_user:
            print_error("You must log in to post a public response.")
        else:
            response_text = Prompt.ask("Enter your response text")
            if response_text.strip():
                ok_post, msg = api.post_comment(slug, response_text.strip())
                if ok_post:
                    print_success("Response recorded to the public record.")
                else:
                    print_error(msg)
