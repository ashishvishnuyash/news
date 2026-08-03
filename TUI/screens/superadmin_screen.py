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

def render_superadmin_screen(api, state):
    print_masthead(title="CENTRAL PUBLICATION CONTROL", motto="SUPER ADMIN COMMAND DESK")
    print_header_strip(api.current_user, current_screen="SUPER ADMIN COMMAND DESK")

    ok_st, settings = api.get_settings()
    if not ok_st or not settings or not isinstance(settings, dict):
        print_error("Failed to load settings from API.")
        return "ADMIN"

    console.print("\n[bold yellow]CURRENT PUBLICATION & SYSTEM CONFIGURATION:[/bold yellow]\n")

    table = Table(show_header=True, header_style="bold gold1", expand=True)
    table.add_column("SETTING PARAMETER", style="bold white", width=30)
    table.add_column("VALUE / STATE", style="bold cyan")

    table.add_row("Publication Title", safe_str(settings.get("title"), "The Republic Bulletin"))
    table.add_row("Masthead Motto / Tagline", safe_str(settings.get("motto"), "The Voice of Truth, Unfiltered & Uncompromised"))
    table.add_row("Breaking News Ticker Status", "[bold green]ACTIVE[/bold green]" if settings.get("ticker_active") else "[bold red]INACTIVE[/bold red]")
    table.add_row("Breaking News Alert Text", safe_str(settings.get("ticker_text")))
    table.add_row("Active Category Taxonomy", ", ".join(settings.get("categories") or []))

    ff = settings.get("feature_flags") or {}
    ff_str = ", ".join([f"{k}: {'ON' if v else 'OFF'}" for k, v in ff.items()])
    table.add_row("System Feature Flags", ff_str)

    console.print(table)

    menu_options = [
        ("1", "EDIT TITLE & MOTTO", "Update publication name and masthead tagline"),
        ("2", "TOGGLE NEWS TICKER", "Activate/deactivate front page breaking alert ticker"),
        ("3", "EDIT ALERT TEXT", "Update live breaking news broadcast text"),
        ("4", "TAXONOMY MANAGEMENT", "Add or remove broadside category sections"),
        ("5", "TOGGLE FEATURE FLAGS", "Enable/disable experimental system features"),
        ("6", "ELEVATE STAFF ROLES", "Promote users to Super Admin, Admin, Editor, Journalist"),
        ("B", "BACK TO BROADSHEET", "Return to public front page view"),
        ("Q", "QUIT TERMINAL", "Exit application")
    ]
    format_menu_options(menu_options)

    cmd = Prompt.ask("Command Input", choices=["1", "2", "3", "4", "5", "6", "b", "B", "q", "Q"]).lower()

    if cmd == "1":
        new_title = Prompt.ask("Publication Title", default=safe_str(settings.get("title")))
        new_motto = Prompt.ask("Masthead Motto / Tagline", default=safe_str(settings.get("motto")))
        ok, res = api.update_settings({"title": new_title, "motto": new_motto})
        if ok:
            print_success("Publication branding updated!")
        else:
            print_error(res)

    elif cmd == "2":
        cur_t = settings.get("ticker_active", False)
        ok, res = api.update_settings({"ticker_active": not cur_t})
        if ok:
            print_success(f"Breaking ticker status updated to {'ACTIVE' if not cur_t else 'INACTIVE'}!")
        else:
            print_error(res)

    elif cmd == "3":
        new_alert = Prompt.ask("Enter Breaking News Broadcast Alert Text", default=safe_str(settings.get("ticker_text")))
        ok, res = api.update_settings({"ticker_text": new_alert})
        if ok:
            print_success("Ticker alert text updated!")
        else:
            print_error(res)

    elif cmd == "4":
        cats = list(settings.get("categories") or [])
        console.print(f"\nCurrent Categories: {', '.join(cats)}")
        console.print("1. Add New Category Section")
        console.print("2. Remove Existing Category Section")
        c_act = Prompt.ask("Select taxonomy action", choices=["1", "2"], default="1")
        if c_act == "1":
            new_cat = Prompt.ask("Category Name to Add")
            if new_cat and new_cat not in cats:
                cats.append(new_cat)
                ok, res = api.update_settings({"categories": cats})
                if ok:
                    print_success(f"Category '{new_cat}' added to taxonomy!")
                else:
                    print_error(res)
        elif c_act == "2":
            rem_cat = Prompt.ask("Category Name to Remove")
            if rem_cat in cats:
                cats.remove(rem_cat)
                ok, res = api.update_settings({"categories": cats})
                if ok:
                    print_success(f"Category '{rem_cat}' removed from taxonomy!")
                else:
                    print_error(res)
            else:
                print_error("Category not found.")

    elif cmd == "5":
        ff = dict(settings.get("feature_flags") or {})
        console.print("\nFeature Flags:")
        for idx, (k, v) in enumerate(ff.items(), start=1):
            console.print(f"{idx}. {k}: {'ON' if v else 'OFF'}")
        
        flag_key = Prompt.ask("Enter feature flag name to toggle (e.g. enable_rss, enable_ai_summaries)")
        if flag_key in ff:
            ff[flag_key] = not ff[flag_key]
            ok, res = api.update_settings({"feature_flags": ff})
            if ok:
                print_success(f"Feature flag '{flag_key}' toggled to {'ON' if ff[flag_key] else 'OFF'}!")
            else:
                print_error(res)
        else:
            print_error("Invalid feature flag key.")

    elif cmd == "6":
        from screens.admin_screen import render_user_management
        render_user_management(api)

    elif cmd == "b":
        return "BROADSHEET"
    elif cmd == "q":
        return "QUIT"

    return "SUPERADMIN"
