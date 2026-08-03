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

def render_profile_screen(api, state):
    print_masthead(title="SUBSCRIBER & PRESS DOSSIER", motto="MEMBER PROFILE & CREDENTIAL MANAGEMENT")
    print_header_strip(api.current_user, current_screen="MEMBER DOSSIER")

    user = api.current_user
    if not user:
        print_error("You are not logged in.")
        return "AUTH"

    console.print("\n[bold yellow]MY PRESS CREDENTIALS & DOSSIER:[bold yellow]\n")

    table = Table(show_header=True, header_style="bold gold1", expand=True)
    table.add_column("DOSSIER RECORD", style="bold white", width=25)
    table.add_column("DETAILS", style="bold cyan")

    table.add_row("Pen Name / Username", safe_str(user.get("username")))
    table.add_row("Press Credentials Role", render_badge(user.get("role")))
    table.add_row("Email Address", safe_str(user.get("email"), "N/A"))
    table.add_row("Member Registration Date", safe_str(user.get("created_at"))[:10])
    table.add_row("Biographical Staff Note", safe_str(user.get("bio"), "No bio recorded."))

    console.print(table)

    # Check notifications
    ok_n, notifications = api.get_notifications()
    if ok_n and notifications and isinstance(notifications, list):
        console.print(f"\n[bold yellow]UNREAD NOTIFICATIONS ({len(notifications)}):[/bold yellow]")
        for n in notifications:
            n_date = safe_str(n.get("created_at"))[:16]
            n_msg = safe_str(n.get("message"))
            console.print(f"[bold cyan]• [{n_date}][/bold cyan] {n_msg}")

    menu_options = [
        ("E", "EDIT DOSSIER DETAILS", "Update email address and biographical note"),
        ("P", "CHANGE PASSPHRASE", "Update your secret login password"),
        ("L", "LOG OUT", "Sign out of your press account"),
        ("B", "BACK TO BROADSHEET", "Return to public front page view"),
        ("Q", "QUIT TERMINAL", "Exit application")
    ]
    format_menu_options(menu_options)

    cmd = Prompt.ask("Command Input", choices=["e", "E", "p", "P", "l", "L", "b", "B", "q", "Q"]).lower()

    if cmd == "e":
        new_email = Prompt.ask("New Email Address", default=safe_str(user.get("email")))
        new_bio = Prompt.ask("Biographical Staff Note", default=safe_str(user.get("bio")))
        ok, res = api.update_profile(email=new_email, bio=new_bio)
        if ok:
            print_success("Dossier profile updated successfully!")
        else:
            print_error(res)

    elif cmd == "p":
        old_p = Prompt.ask("Current Password", password=True)
        new_p = Prompt.ask("New Password", password=True)
        conf_p = Prompt.ask("Confirm New Password", password=True)
        
        if new_p != conf_p:
            print_error("New password confirmation does not match!")
        else:
            ok, msg = api.update_password(old_p, new_p)
            if ok:
                print_success("Passphrase updated successfully!")
            else:
                print_error(msg)

    elif cmd == "l":
        api.logout()
        print_success("Logged out successfully.")
        return "BROADSHEET"

    elif cmd == "b":
        return "BROADSHEET"

    elif cmd == "q":
        return "QUIT"

    return "PROFILE"
