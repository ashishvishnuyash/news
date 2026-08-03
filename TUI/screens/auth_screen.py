from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from ui_components import print_masthead, print_error, print_success, format_menu_options

console = Console()

def render_login_screen(api):
    print_masthead(title="THE REPUBLIC BULLETIN", motto="PRESS CREDENTIALS SIGN IN")
    
    console.print("[bold yellow]SELECT QUICK DEMO ROLE OR ENTER CUSTOM CREDENTIALS:[/bold yellow]\n")
    
    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("OPTION", style="bold yellow", width=8)
    table.add_column("ROLE DESK", style="bold white", width=18)
    table.add_column("USERNAME", style="cyan", width=15)
    table.add_column("DESCRIPTION", style="dim white")
    
    table.add_row("[1]", "SUPER ADMIN", "superadmin", "Full central publication & settings control")
    table.add_row("[2]", "CHIEF ADMIN", "admin", "Operations desk, user registry & metrics")
    table.add_row("[3]", "EDITOR", "editor", "Editorial review board & publishing queue")
    table.add_row("[4]", "JOURNALIST", "journalist", "Press correspondent workspace & draft room")
    table.add_row("[5]", "READER / USER", "reader", "Subscriber reading & public comments desk")
    table.add_row("[C]", "CUSTOM LOGIN", "Custom User", "Enter custom username & password")
    table.add_row("[R]", "REGISTER NEW", "New Account", "Create new subscriber / staff credentials")
    table.add_row("[B]", "BACK TO READ", "Guest", "Return to front page as guest reader")
    
    console.print(table)
    
    choice = Prompt.ask("\nSelect authentication option", choices=["1", "2", "3", "4", "5", "c", "C", "r", "R", "b", "B"], default="1")
    choice = choice.lower()
    
    if choice == "1":
        ok, msg = api.login("superadmin", "password123")
        if ok:
            print_success(f"Authenticated as SUPER_ADMIN: {api.current_user['username']}")
            return True
        else:
            print_error(msg)
    elif choice == "2":
        ok, msg = api.login("admin", "password123")
        if ok:
            print_success(f"Authenticated as ADMIN: {api.current_user['username']}")
            return True
        else:
            print_error(msg)
    elif choice == "3":
        ok, msg = api.login("editor", "password123")
        if ok:
            print_success(f"Authenticated as EDITOR: {api.current_user['username']}")
            return True
        else:
            print_error(msg)
    elif choice == "4":
        ok, msg = api.login("journalist", "password123")
        if ok:
            print_success(f"Authenticated as JOURNALIST: {api.current_user['username']}")
            return True
        else:
            print_error(msg)
    elif choice == "5":
        ok, msg = api.login("reader", "password123")
        if ok:
            print_success(f"Authenticated as READER: {api.current_user['username']}")
            return True
        else:
            print_error(msg)
    elif choice == "c":
        username = Prompt.ask("Enter username")
        password = Prompt.ask("Enter password", password=True)
        ok, msg = api.login(username, password)
        if ok:
            print_success(f"Authenticated as {api.current_user['role']}: {api.current_user['username']}")
            return True
        else:
            print_error(msg)
    elif choice == "r":
        return render_register_screen(api)
    elif choice == "b":
        return False
        
    return False

def render_register_screen(api):
    console.print("\n[bold gold1]═" * 60 + "[/bold gold1]")
    console.print("[bold yellow center]PRESS CREDENTIALS REGISTRATION FORM[/bold yellow center]")
    console.print("[bold gold1]═" * 60 + "[/bold gold1]\n")
    
    username = Prompt.ask("Desired Username (Pen Name)")
    email = Prompt.ask("Email Address")
    password = Prompt.ask("Password (min 6 chars)", password=True)
    
    console.print("\n[bold cyan]Select Account Role / Desk:[/bold cyan]")
    console.print("1. READER / USER (Subscriber)")
    console.print("2. JOURNALIST (Press Correspondent)")
    console.print("3. EDITOR (Editorial Review Board)")
    role_choice = Prompt.ask("Choose Role", choices=["1", "2", "3"], default="1")
    
    role_map = {"1": "USER", "2": "JOURNALIST", "3": "EDITOR"}
    role = role_map[role_choice]
    
    bio = Prompt.ask("Biographical / Staff Note", default="Journalist and avid reader of The Republic Bulletin.")
    
    ok, data = api.register(username, email, password, role=role, bio=bio)
    if ok:
        print_success("Registration successful! Logging into your new account...")
        ok_login, msg = api.login(username, password)
        return ok_login
    else:
        print_error(data)
        return False
