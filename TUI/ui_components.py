from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.layout import Layout
from rich.style import Style

console = Console(force_terminal=True)

MASTHEAD_ASCII = """
[bold gold1]████████╗██╗  ██╗███████╗   ██████╗ ███████╗██████╗ ██╗  ██╗██████╗ ██╗     ██╗██████╗ 
╚══██╔══╝██║  ██║██╔════╝   ██╔══██╗██╔════╝██╔══██╗██║  ██║██╔══██╗██║     ██║██╔══██╗
   ██║   ███████║█████╗     ██████╔╝█████╗  ██████╔╝██║  ██║██████╔╝██║     ██║██║  ██║
   ██║   ██╔══██║██╔══╝     ██╔══██╗██╔══╝  ██╔═══╝ ██║  ██║██╔══██╗██║     ██║██║  ██║
   ██║   ██║  ██║███████╗   ██║  ██║███████╗██║     ╚█████╔╝██████╔╝███████╗██║██████╔╝
   ╚═╝   ╚═╝  ╚═╝╚══════╝   ╚═╝  ╚═╝╚══════╝╚═╝      ╚════╝ ╚═════╝ ╚══════╝╚═╝╚═════╝ [/bold gold1]
             [bold white on black] -- THE VOICE OF TRUTH, UNFILTERED & UNCOMPROMISED -- [/bold white on black]
"""

def safe_str(val, default=""):
    if val is None:
        return default
    return str(val)

def safe_upper(val, default=""):
    if val is None:
        return default.upper()
    return str(val).upper()

def print_masthead(title="THE REPUBLIC BULLETIN", motto="The Voice of Truth, Unfiltered & Uncompromised"):
    title_text = safe_upper(title, "THE REPUBLIC BULLETIN")
    motto_text = safe_str(motto, "The Voice of Truth, Unfiltered & Uncompromised")
    console.print("\n[bold gold1]" + "=" * 90 + "[/bold gold1]")
    console.print(f"[bold yellow center]{title_text}[/bold yellow center]", justify="center")
    console.print(f"[italic cyan center]--  {motto_text}  --[/italic cyan center]", justify="center")
    console.print("[bold gold1]" + "=" * 90 + "[/bold gold1]\n")

def print_header_strip(user=None, current_screen="FRONT PAGE"):
    if user and isinstance(user, dict):
        uname = safe_upper(user.get("username"), "GUEST")
        urole = safe_upper(user.get("role"), "USER")
        user_str = f"USER: {uname} ({urole})"
    else:
        user_str = "GUEST READER"
        
    date_str = "DAILY BROADSHEET TERMINAL EDITION"

    screen_str = safe_upper(current_screen, "FRONT PAGE")
    
    table = Table(show_header=False, expand=True, box=None)
    table.add_column(justify="left", style="bold yellow")
    table.add_column(justify="center", style="bold white")
    table.add_column(justify="right", style="bold magenta")
    table.add_row(f"DESK: {screen_str}", date_str, user_str)
    
    console.print(table)
    console.print("[dim white]" + "-" * 90 + "[/dim white]")

def print_ticker(settings):
    if settings and isinstance(settings, dict) and settings.get("ticker_active"):
        alert_text = safe_str(settings.get("ticker_text"), "BREAKING NEWS ALERT")
        console.print(Panel(f"[bold red blink]! BREAKING NEWS:[/bold red blink] [bold white]{alert_text}[/bold white]", style="bold red on dark_blue", expand=True))

def render_badge(role):
    role_str = safe_upper(role, "USER")
    colors = {
        "SUPER_ADMIN": "bold magenta on black",
        "ADMIN": "bold blue on black",
        "EDITOR": "bold green on black",
        "JOURNALIST": "bold yellow on black",
        "USER": "bold cyan on black"
    }
    style = colors.get(role_str, "white")
    return f"[{style}] [{role_str}] [/{style}]"

def render_status_badge(status):
    status_str = safe_upper(status, "DRAFT")
    status_map = {
        "PUBLISHED": "[bold green]PUBLISHED[/bold green]",
        "SUBMITTED": "[bold yellow]IN REVIEW[/bold yellow]",
        "DRAFT": "[bold cyan]DRAFT[/bold cyan]",
        "REJECTED": "[bold red]REJECTED[/bold red]"
    }
    return status_map.get(status_str, f"[white]{status_str}[/white]")

def format_menu_options(options):
    console.print("\n[bold gold1]AVAILABLE COMMANDS & DESK ACTIONS:[/bold gold1]")
    table = Table(show_header=True, header_style="bold yellow", box=None)
    table.add_column("KEY", style="bold cyan", width=8)
    table.add_column("COMMAND ACTION", style="bold white")
    table.add_column("DESCRIPTION", style="dim white")
    
    for key, label, desc in options:
        table.add_row(f"[{key}]", label, desc)
    console.print(table)
    console.print()

def print_error(msg):
    console.print(f"\n[bold red][X] ERROR:[/bold red] [red]{safe_str(msg)}[/red]\n")

def print_success(msg):
    console.print(f"\n[bold green][+] SUCCESS:[/bold green] [green]{safe_str(msg)}[/green]\n")

def print_info(msg):
    console.print(f"\n[bold cyan][i] INFO:[/bold cyan] [cyan]{safe_str(msg)}[/cyan]\n")
