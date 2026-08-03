from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from ui_components import (
    print_masthead, print_header_strip, format_menu_options,
    print_error, print_success, print_info, render_badge,
    safe_str, safe_upper
)

console = Console()

def render_admin_screen(api, state):
    print_masthead(title="ADMINISTRATIVE CONTROL CENTRE", motto="OPERATIONS DESK & METRICS REGISTRY")
    print_header_strip(api.current_user, current_screen="ADMIN DESK")

    # Fetch stats
    ok_st, stats = api.get_admin_stats()
    if ok_st and stats and isinstance(stats, dict):
        console.print("\n[bold yellow]NETWORK PLATFORM METRICS & STATS:[/bold yellow]\n")
        table_s = Table(show_header=True, header_style="bold gold1", expand=True)
        table_s.add_column("METRIC ITEM", style="bold white")
        table_s.add_column("COUNT / TOTAL", style="bold cyan", justify="right")
        
        table_s.add_row("Total Registered Users", str(stats.get("total_users", 0)))
        table_s.add_row("Total Dispatches in System", str(stats.get("total_articles", 0)))
        table_s.add_row("  └─ Published on Front Page", f"[bold green]{stats.get('published_articles', 0)}[/bold green]")
        table_s.add_row("  └─ Submitted in Review Queue", f"[bold yellow]{stats.get('queue_articles', 0)}[/bold yellow]")
        table_s.add_row("  └─ Drafts in Workrooms", f"[bold cyan]{stats.get('draft_articles', 0)}[/bold cyan]")
        table_s.add_row("  └─ Rejected Dispatches", f"[bold red]{stats.get('rejected_articles', 0)}[/bold red]")
        table_s.add_row("Total Reader Comments Filed", str(stats.get("total_comments", 0)))
        
        roles_break = stats.get("role_counts") or {}
        table_s.add_row("Staff Roles Breakdown", f"SuperAdmins: {roles_break.get('SUPER_ADMIN', 0)} | Admins: {roles_break.get('ADMIN', 0)} | Editors: {roles_break.get('EDITOR', 0)} | Journalists: {roles_break.get('JOURNALIST', 0)} | Readers: {roles_break.get('USER', 0)}")
        
        console.print(table_s)
    else:
        print_error("Failed to load platform statistics.")

    menu_options = [
        ("U", "USER REGISTRY & ROLES", "View all users and promote/demote staff credentials"),
        ("A", "ARTICLES ARCHIVE", "Inspect all dispatches and remove inappropriate content"),
        ("S", "SUPER ADMIN DESK", "Open Central Publication Control & Site Settings (SuperAdmin only)"),
        ("B", "BACK TO BROADSHEET", "Return to public front page view"),
        ("Q", "QUIT TERMINAL", "Exit application")
    ]
    format_menu_options(menu_options)

    cmd = Prompt.ask("Command Input", choices=["u", "U", "a", "A", "s", "S", "b", "B", "q", "Q"]).lower()

    if cmd == "u":
        render_user_management(api)
    elif cmd == "a":
        render_article_management(api)
    elif cmd == "s":
        if api.current_user and safe_str(api.current_user.get("role")) == "SUPER_ADMIN":
            return "SUPERADMIN"
        else:
            print_error("Only SUPER_ADMIN credential holders can access central settings.")
    elif cmd == "b":
        return "BROADSHEET"
    elif cmd == "q":
        return "QUIT"

    return "ADMIN"


def render_user_management(api):
    console.print("\n[bold gold1]═" * 70 + "[/bold gold1]")
    console.print("[bold yellow center]USER REGISTRY & ROLE CREDENTIAL MANAGEMENT[/bold yellow center]")
    console.print("[bold gold1]═" * 70 + "[/bold gold1]\n")

    ok, users = api.get_admin_users()
    if not ok or not users or not isinstance(users, list):
        print_error("Could not fetch user list.")
        return

    table = Table(show_header=True, header_style="bold cyan", expand=True)
    table.add_column("ID", style="bold yellow", width=4)
    table.add_column("USERNAME", style="bold white", width=16)
    table.add_column("EMAIL ADDRESS", style="dim white", width=30)
    table.add_column("CREDENTIAL ROLE", width=18)
    table.add_column("JOINED", style="dim white", width=12)

    for u in users:
        u_id = str(u.get("id", ""))
        u_name = safe_str(u.get("username"), "Anonymous")
        u_email = safe_str(u.get("email"), "N/A")
        u_role = safe_str(u.get("role"), "USER")
        u_created = safe_str(u.get("created_at"))
        
        table.add_row(
            u_id,
            u_name,
            u_email,
            render_badge(u_role),
            u_created[:10]
        )
    console.print(table)

    sub_cmd = Prompt.ask("\nAction: [1] Promote/Update User Role  [2] Return to Admin Desk", choices=["1", "2"], default="2")
    if sub_cmd == "1":
        user_id = Prompt.ask("Enter User ID to update")
        if not user_id.isdigit():
            print_error("Invalid User ID.")
            return
        
        console.print("\nSelect New Role:")
        console.print("1. SUPER_ADMIN (Full System Control)")
        console.print("2. ADMIN (Operations & User Management)")
        console.print("3. EDITOR (Editorial Review Board)")
        console.print("4. JOURNALIST (Press Correspondent)")
        console.print("5. USER (Subscriber / Reader)")
        
        r_choice = Prompt.ask("Choose Role", choices=["1", "2", "3", "4", "5"])
        r_map = {"1": "SUPER_ADMIN", "2": "ADMIN", "3": "EDITOR", "4": "JOURNALIST", "5": "USER"}
        new_role = r_map[r_choice]
        
        ok_up, msg = api.update_user_role(int(user_id), new_role)
        if ok_up:
            print_success(f"User #{user_id} role updated to {new_role}!")
        else:
            print_error(msg)


def render_article_management(api):
    console.print("\n[bold gold1]═" * 70 + "[/bold gold1]")
    console.print("[bold yellow center]SYSTEM ARTICLES ARCHIVE & MODERATION[/bold yellow center]")
    console.print("[bold gold1]═" * 70 + "[/bold gold1]\n")

    ok, articles = api.get_admin_articles()
    if not ok or not articles or not isinstance(articles, list):
        print_error("Could not fetch system articles archive.")
        return

    table = Table(show_header=True, header_style="bold cyan", expand=True)
    table.add_column("ID", style="bold yellow", width=4)
    table.add_column("STATUS", width=12)
    table.add_column("SECTION", style="bold red", width=10)
    table.add_column("HEADLINE", style="bold white")
    table.add_column("SCRIBE", style="cyan", width=12)
    table.add_column("READS", style="bold green", width=6)

    for a in articles:
        a_id = str(a.get("id", ""))
        a_status = safe_str(a.get("status"), "PUBLISHED")
        a_cat = safe_upper(a.get("category"), "TECH")
        a_title = safe_str(a.get("title"), "Untitled")
        a_author = safe_upper((a.get("author") or {}).get("username"), "STAFF")
        a_views = str(a.get("view_count", 0))
        
        table.add_row(
            a_id,
            a_status,
            a_cat,
            a_title[:50],
            a_author,
            a_views
        )
    console.print(table)

    sub_cmd = Prompt.ask("\nAction: [1] Delete Dispatch  [2] Return to Admin Desk", choices=["1", "2"], default="2")
    if sub_cmd == "1":
        art_id = Prompt.ask("Enter Dispatch ID to DELETE permanently")
        if not art_id.isdigit():
            print_error("Invalid Dispatch ID.")
            return
        
        confirm = Prompt.ask(f"Are you sure you want to delete dispatch #{art_id}?", choices=["y", "n"], default="n")
        if confirm.lower() == "y":
            ok_del, msg = api.delete_admin_article(int(art_id))
            if ok_del:
                print_success(msg)
            else:
                print_error(msg)
