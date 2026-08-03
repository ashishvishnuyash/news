import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer, Grid
from textual.widgets import (
    Header, Footer, Static, Button, DataTable, Input, TextArea,
    TabbedContent, TabPane, Markdown, Switch, Label, Select
)
from textual.screen import ModalScreen
from textual.binding import Binding

from api_client import APIClient, BASE_URL

def safe_str(val, default=""):
    if val is None:
        return default
    return str(val)

def safe_upper(val, default=""):
    if val is None:
        return default.upper()
    return str(val).upper()

# Modal Screen for Reading Full Article Broadside
class ArticleReaderModal(ModalScreen):
    BINDINGS = [Binding("escape", "dismiss", "Close Modal")]

    def __init__(self, article: dict, comments: list, api_client: APIClient):
        super().__init__()
        self.article = article
        self.comments = comments or []
        self.api_client = api_client

    def compose(self) -> ComposeResult:
        with Container(id="article-modal-box"):
            yield Button("✕ CLOSE BROADSIDE [Esc]", id="btn-close-modal", variant="error")
            
            cat = safe_upper(self.article.get("category"), "GENERAL")
            title = safe_upper(self.article.get("title"), "UNTITLED DISPATCH")
            summary = safe_str(self.article.get("summary"))
            author = safe_upper((self.article.get("author") or {}).get("username"), "UNKNOWN")
            editor = safe_upper((self.article.get("editor") or {}).get("username"), "N/A")
            date_str = safe_str(self.article.get("published_at") or self.article.get("created_at"))[:16]

            yield Static(f"[bold red]SECTION: {cat}[/bold red]  •  [bold white]PRINTED: {date_str}[/bold white]", classes="meta-header")
            yield Static(f"[bold white]{title}[/bold white]", classes="article-title")

            if summary:
                yield Static(f"[italic gold1]{summary}[/italic gold1]", classes="article-summary")
            yield Static(f"[dim white]SCRIBE: {author}  |  EDITOR: {editor}  |  VIEWS: {self.article.get('view_count', 0)}[/dim white]", classes="meta-bar")
            
            with ScrollableContainer(classes="markdown-scroll-container"):
                yield Markdown(safe_str(self.article.get("content")))
                
                yield Static(f"\n[bold yellow]READER RESPONSES ({len(self.comments)} FILED):[/bold yellow]", classes="comment-title")
                if not self.comments:
                    yield Static("[italic dim]No public responses filed yet. Be the first to post.[/italic dim]")
                else:
                    for c in self.comments:
                        uinfo = c.get("author") or {}
                        uname = safe_upper(uinfo.get("username"), "ANONYMOUS")
                        urole = safe_str(uinfo.get("role"), "READER")
                        cdate = safe_str(c.get("created_at"))[:16]
                        yield Static(f"[bold cyan]• {uname} ({urole})[/bold cyan] [dim]at {cdate}[/dim]:\n  {safe_str(c.get('content'))}\n")
                        
                with Vertical(classes="comment-input-box"):
                    yield Label("Write your public response:")
                    yield Input(placeholder="Submit your thoughts for the public record...", id="comment-text-input")
                    yield Button("💬 POST RESPONSE TO RECORD", id="btn-post-comment", variant="success")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close-modal":
            self.dismiss()
        elif event.button.id == "btn-post-comment":
            if not self.api_client.current_user:
                self.app.notify("You must be signed in to post a public response!", severity="error")
                return
            inp = self.query_one("#comment-text-input", Input)
            text = inp.value.strip()
            if text:
                ok, msg = self.api_client.post_comment(self.article["slug"], text)
                if ok:
                    self.app.notify("Response recorded to the public record!", severity="information")
                    inp.value = ""
                    # Refresh comments
                    _, new_comments = self.api_client.get_comments(self.article["slug"])
                    self.comments = new_comments or []
                    self.refresh()
                else:
                    self.app.notify(f"Failed to post comment: {msg}", severity="error")


# Main Broadsheet Textual Application
class BroadsheetApp(App):
    CSS = """
    Screen {
        background: #f6f3eb;
        color: #1c1917;
    }

    #masthead-box {
        background: #262626;
        color: #fef08a;
        padding: 1;
        text-align: center;
        border-bottom: double #d97706;
    }


    #masthead-title {
        text-style: bold;
        color: #fde047;
    }

    #user-badge-bar {
        background: #1c1917;
        color: #fafafa;
        padding: 0 1;
        height: 3;
    }

    #user-status-label {
        color: #facc15;
        text-style: bold;
        margin-top: 1;
    }

    .section-btn {
        margin-right: 1;
        height: 1;
        min-width: 10;
        background: #78350f;
        color: #ffffff;
    }

    .role-btn {
        margin: 1;
        height: 3;
        min-width: 18;
        border: heavy #d97706;
    }

    #article-table, #journalist-table, #editor-table, #users-table, #admin-articles-table {
        height: 100%;
        border: double #78350f;
        background: #fffbeb;
        color: #0f172a;
    }

    #article-modal-box {
        padding: 2;
        background: #fef3c7;
        border: heavy #b45309;
        width: 85%;
        height: 85%;
    }

    .markdown-scroll-container {
        height: 1fr;
        border: solid #d97706;
        padding: 1;
        background: #ffffff;
    }

    .stat-card {
        border: double #78350f;
        background: #fef08a;
        padding: 1;
        margin: 1;
        text-align: center;
        text-style: bold;
    }
    """

    TITLE = "THE REPUBLIC BULLETIN ⚜️ BROADSHEET TERMINAL"
    SUB_TITLE = "Mouse Interactive Edition"
    BINDINGS = [
        Binding("q", "quit", "Quit Terminal"),
        Binding("r", "refresh", "Refresh Page"),
    ]

    def __init__(self, base_url: str = BASE_URL):
        super().__init__()
        self.api = APIClient(base_url=base_url)
        self.articles_cache = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(id="masthead-box"):
            yield Static("[bold yellow]THE REPUBLIC BULLETIN[/bold yellow]", id="masthead-title")

            yield Static("⚜️ THE VOICE OF TRUTH, UNFILTERED & UNCOMPROMISED ⚜️", classes="sub-title")


        with Horizontal(id="user-badge-bar"):
            yield Label("AUTHENTICATED AS: GUEST READER (GUEST)", id="user-status-label")
            yield Button("🔐 SIGN IN / CHANGE ROLE", id="btn-goto-login", variant="primary")

        with TabbedContent(initial="tab-frontpage", id="main-tabs"):
            # TAB 1: FRONT PAGE BROADSHEET
            with TabPane("📰 Front Page Broadsheet", id="tab-frontpage"):
                with Horizontal(classes="action-bar"):
                    yield Input(placeholder="🔍 Search archives by keyword...", id="search-input")
                    yield Button("Search", id="btn-search", variant="warning")
                    yield Button("ALL", id="btn-cat-all", classes="section-btn")
                    yield Button("POLITICS", id="btn-cat-politics", classes="section-btn")
                    yield Button("WORLD", id="btn-cat-world", classes="section-btn")
                    yield Button("ECONOMY", id="btn-cat-economy", classes="section-btn")
                    yield Button("TECH", id="btn-cat-tech", classes="section-btn")
                    yield Button("OPINION", id="btn-cat-opinion", classes="section-btn")

                yield Static("[bold italic red]★ CLICK ANY DISPATCH ROW TO OPEN & READ FULL BROADSIDE[/bold italic red]", id="hint-label")
                yield DataTable(id="article-table")

            # TAB 2: PRESS CORRESPONDENT DESK (JOURNALIST)
            with TabPane("✒️ Press Correspondent Desk", id="tab-journalist"):
                with Horizontal():
                    with Vertical(classes="left-pane", id="journo-left-pane"):
                        yield Label("[bold yellow]MY FILED DISPATCHES:[/bold yellow]")
                        yield DataTable(id="journalist-table")
                    with Vertical(classes="right-pane", id="journo-right-pane"):
                        yield Label("[bold gold1]COMPOSE / EDIT DISPATCH FORM:[/bold gold1]")
                        yield Input(placeholder="Headline Title", id="j-title-input")
                        yield Input(placeholder="Abstract Summary", id="j-summary-input")
                        yield Input(placeholder="Category (Tech, Politics, Economy, etc.)", id="j-category-input")
                        yield Label("Dispatch Body Content:")
                        yield TextArea(id="j-content-input")
                        with Horizontal():
                            yield Button("📝 SAVE DRAFT", id="btn-j-save", variant="primary")
                            yield Button("🚀 SUBMIT FOR REVIEW", id="btn-j-submit", variant="success")

            # TAB 3: EDITORIAL REVIEW BOARD (EDITOR)
            with TabPane("✍️ Editorial Review Board", id="tab-editor"):
                with Horizontal():
                    yield Button("Filter: SUBMITTED", id="btn-e-submitted", variant="warning")
                    yield Button("Filter: DRAFT", id="btn-e-draft")
                    yield Button("Filter: PUBLISHED", id="btn-e-published")
                    yield Button("Filter: REJECTED", id="btn-e-rejected")
                
                with Horizontal():
                    with Vertical(id="editor-left-pane"):
                        yield Label("[bold yellow]SUBMISSION QUEUE:[/bold yellow]")
                        yield DataTable(id="editor-table")
                    with Vertical(id="editor-right-pane"):
                        yield Label("[bold gold1]SELECTED PROOF CONTENT:[/bold gold1]")
                        yield Static("Select a dispatch row from table to proof...", id="proof-summary-box")
                        yield ScrollableContainer(Static("", id="proof-content-box"))
                        yield Input(placeholder="Editorial feedback & revision notes...", id="e-notes-input")
                        with Horizontal():
                            yield Button("✓ APPROVE & PUBLISH", id="btn-e-approve", variant="success")
                            yield Button("X REJECT WITH NOTES", id="btn-e-reject", variant="error")

            # TAB 4: CHIEF EDITOR OPERATIONS DESK (ADMIN)
            with TabPane("🛡️ Operations Desk", id="tab-admin"):
                yield Static("[bold yellow]NETWORK PLATFORM METRICS:[/bold yellow]")
                with Grid(id="stats-grid"):
                    yield Static("Total Users: ...", id="stat-users", classes="stat-card")
                    yield Static("Total Articles: ...", id="stat-articles", classes="stat-card")
                    yield Static("Published: ...", id="stat-published", classes="stat-card")
                    yield Static("Queue: ...", id="stat-queue", classes="stat-card")
                
                with Horizontal():
                    with Vertical():
                        yield Label("[bold yellow]USER REGISTRY & STAFF ROLES:[/bold yellow]")
                        yield DataTable(id="users-table")
                    with Vertical():
                        yield Label("[bold yellow]ARTICLES ARCHIVE & MODERATION:[/bold yellow]")
                        yield DataTable(id="admin-articles-table")
                        yield Button("🗑️ DELETE SELECTED DISPATCH", id="btn-admin-delete-article", variant="error")

            # TAB 5: CENTRAL PUBLICATION CONTROL (SUPER ADMIN)
            with TabPane("👑 Super Admin Desk", id="tab-superadmin"):
                yield Label("[bold gold1]GLOBAL PUBLICATION BRANDING & CONFIGURATION:[/bold gold1]")
                yield Input(placeholder="Publication Title", id="sa-title-input")
                yield Input(placeholder="Masthead Motto / Tagline", id="sa-motto-input")
                yield Button("💾 SAVE BRANDING SETTINGS", id="btn-sa-save-branding", variant="primary")
                
                yield Label("\n[bold red]LIVE BREAKING NEWS TICKER ALERT:[/bold red]")
                with Horizontal():
                    yield Label("Ticker Active: ")
                    yield Switch(id="sa-ticker-switch")
                yield Input(placeholder="Breaking Alert Text...", id="sa-ticker-text-input")
                yield Button("📢 UPDATE TICKER ALERT", id="btn-sa-save-ticker", variant="warning")

            # TAB 6: SUBSCRIBER & PRESS DOSSIER (PROFILE)
            with TabPane("👤 Member Dossier", id="tab-dossier"):
                yield Label("[bold yellow]MY PROFILE & STAFF DOSSIER DETAILS:[/bold yellow]")
                yield Input(placeholder="Email Address", id="prof-email-input")
                yield Label("Biographical Staff Note:")
                yield TextArea(id="prof-bio-input")
                yield Button("💾 SAVE PROFILE DOSSIER", id="btn-prof-save", variant="primary")

            # TAB 7: QUICK ROLE SIGN IN
            with TabPane("🔐 Sign In / Roles", id="tab-login"):
                yield Label("[bold yellow center]SELECT QUICK DEMO ROLE TO AUTHENTICATE INSTANTLY:[/bold yellow center]")
                with Grid(id="roles-grid"):
                    yield Button("👑 SUPER ADMIN\n(superadmin / password123)", id="btn-role-superadmin", classes="role-btn", variant="error")

                    yield Button("🛡️ CHIEF ADMIN\n(admin / password123)", id="btn-role-admin", classes="role-btn", variant="primary")
                    yield Button("✍️ MANAGING EDITOR\n(editor / password123)", id="btn-role-editor", classes="role-btn", variant="success")
                    yield Button("✒️ PRESS CORRESPONDENT\n(journalist / password123)", id="btn-role-journalist", classes="role-btn", variant="warning")
                    yield Button("👤 SUBSCRIBER READER\n(reader / password123)", id="btn-role-reader", classes="role-btn", variant="default")

        yield Footer()

    def on_mount(self) -> None:
        self.setup_tables()
        self.load_frontpage_articles()

    def setup_tables(self) -> None:
        # Front page table
        table = self.query_one("#article-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("#", "SECTION", "HEADLINE", "SCRIBE", "READS", "SLUG")

        # Journalist table
        j_table = self.query_one("#journalist-table", DataTable)
        j_table.cursor_type = "row"
        j_table.add_columns("ID", "STATUS", "SECTION", "HEADLINE", "DATE")

        # Editor table
        e_table = self.query_one("#editor-table", DataTable)
        e_table.cursor_type = "row"
        e_table.add_columns("ID", "STATUS", "SECTION", "HEADLINE", "SCRIBE")

        # Users table
        u_table = self.query_one("#users-table", DataTable)
        u_table.cursor_type = "row"
        u_table.add_columns("ID", "USERNAME", "ROLE", "EMAIL")

        # Admin articles table
        a_table = self.query_one("#admin-articles-table", DataTable)
        a_table.cursor_type = "row"
        a_table.add_columns("ID", "STATUS", "SECTION", "HEADLINE", "SCRIBE")

    def update_user_status_badge(self) -> None:
        label = self.query_one("#user-status-label", Label)
        if self.api.current_user:
            uname = safe_upper(self.api.current_user.get("username"))
            urole = safe_upper(self.api.current_user.get("role"))
            label.update(f"AUTHENTICATED AS: [bold green]{uname}[/bold green] ([bold yellow]{urole}[/bold yellow])")
        else:
            label.update("AUTHENTICATED AS: [bold dim]GUEST READER (GUEST)[/bold dim]")

    def load_frontpage_articles(self, category=None, search=None) -> None:

        table = self.query_one("#article-table", DataTable)
        table.clear()
        ok, articles = self.api.get_articles(category=category, search=search)
        if ok and isinstance(articles, list):
            self.articles_cache = articles
            for idx, a in enumerate(articles, start=1):
                cat = safe_upper(a.get("category"), "TECH")
                title = safe_str(a.get("title"), "Untitled")
                author = safe_upper((a.get("author") or {}).get("username"), "STAFF")
                views = str(a.get("view_count", 0))
                slug = safe_str(a.get("slug"))
                table.add_row(str(idx), cat, title, author, views, slug)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table_id = event.data_table.id
        if table_id == "article-table":
            row_data = event.data_table.get_row(event.row_key)
            slug = row_data[5]
            if slug:
                ok, article = self.api.get_article(slug)
                if ok and article:
                    _, comments = self.api.get_comments(slug)
                    self.push_screen(ArticleReaderModal(article, comments, self.api))
                else:
                    self.notify("Could not fetch full dispatch proof.", severity="error")

        elif table_id == "editor-table":
            row_data = event.data_table.get_row(event.row_key)
            art_id = row_data[0]
            ok, queue = self.api.get_editor_queue(status_filter=None)
            if ok:
                target = next((a for a in queue if str(a.get("id")) == str(art_id)), None)
                if target:
                    self.selected_editor_article = target
                    p_summary = self.query_one("#proof-summary-box", Static)
                    p_summary.update(f"[bold white]{target.get('title')}[/bold white]\n[italic gold1]{target.get('summary')}[/italic gold1]\nScribe: {target.get('author', {}).get('username')}")
                    p_content = self.query_one("#proof-content-box", Static)
                    p_content.update(target.get("content", ""))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        
        if btn_id == "btn-goto-login":
            tabs = self.query_one("#main-tabs", TabbedContent)
            tabs.active = "tab-login"

        elif btn_id and btn_id.startswith("btn-role-"):
            role_name = btn_id.replace("btn-role-", "")
            target_user = "reader" if role_name in ("reader", "user") else role_name
            ok, msg = self.api.login(target_user, "password123")
            if ok:
                self.update_user_status_badge()
                self.notify(f"Successfully authenticated as {self.api.current_user['role']}: {self.api.current_user['username']}", severity="information")
                tabs = self.query_one("#main-tabs", TabbedContent)
                tabs.active = "tab-frontpage"
                self.load_frontpage_articles()
                self.refresh_desk_data()
            else:
                self.notify(f"Role authentication failed: {msg}", severity="error")

        elif btn_id == "btn-search":
            search_val = self.query_one("#search-input", Input).value.strip()
            self.load_frontpage_articles(search=search_val if search_val else None)

        elif btn_id and btn_id.startswith("btn-cat-"):
            cat_name = btn_id.replace("btn-cat-", "").upper()
            self.load_frontpage_articles(category=None if cat_name == "ALL" else cat_name)

        elif btn_id == "btn-j-save":
            title = self.query_one("#j-title-input", Input).value.strip()
            summary = self.query_one("#j-summary-input", Input).value.strip()
            category = self.query_one("#j-category-input", Input).value.strip() or "Tech"
            content = self.query_one("#j-content-input", TextArea).text
            if title and content:
                ok, res = self.api.create_article(title, summary, category, content)
                if ok:
                    self.notify("Draft saved successfully!", severity="information")
                    self.load_journalist_data()
                else:
                    self.notify(f"Save failed: {res}", severity="error")
            else:
                self.notify("Title and Content are required!", severity="warning")

        elif btn_id == "btn-e-approve":
            if hasattr(self, "selected_editor_article") and self.selected_editor_article:
                notes = self.query_one("#e-notes-input", Input).value
                ok, msg = self.api.review_article(self.selected_editor_article["id"], "PUBLISHED", notes)
                if ok:
                    self.notify("Dispatch APPROVED & PUBLISHED to front page!", severity="information")
                    self.load_editor_data()
                else:
                    self.notify(f"Approval failed: {msg}", severity="error")

        elif btn_id == "btn-e-reject":
            if hasattr(self, "selected_editor_article") and self.selected_editor_article:
                notes = self.query_one("#e-notes-input", Input).value
                ok, msg = self.api.review_article(self.selected_editor_article["id"], "REJECTED", notes)
                if ok:
                    self.notify("Dispatch REJECTED and returned to scribe.", severity="warning")
                    self.load_editor_data()
                else:
                    self.notify(f"Rejection failed: {msg}", severity="error")

        elif btn_id and btn_id.startswith("btn-e-"):
            status_filter = btn_id.replace("btn-e-", "").upper()
            self.load_editor_data(status_filter=status_filter)

    def refresh_desk_data(self) -> None:
        self.load_journalist_data()
        self.load_editor_data()
        self.load_admin_data()

    def load_journalist_data(self) -> None:
        if not self.api.current_user:
            return
        table = self.query_one("#journalist-table", DataTable)
        table.clear()
        ok, my_articles = self.api.get_my_articles()
        if ok and isinstance(my_articles, list):
            for a in my_articles:
                table.add_row(
                    str(a.get("id")),
                    safe_str(a.get("status")),
                    safe_upper(a.get("category"), "TECH"),
                    safe_str(a.get("title")),
                    safe_str(a.get("created_at"))[:10]
                )

    def load_editor_data(self, status_filter="SUBMITTED") -> None:
        if not self.api.current_user:
            return
        table = self.query_one("#editor-table", DataTable)
        table.clear()
        ok, queue = self.api.get_editor_queue(status_filter=None if status_filter == "ALL" else status_filter)
        if ok and isinstance(queue, list):
            for a in queue:
                table.add_row(
                    str(a.get("id")),
                    safe_str(a.get("status")),
                    safe_upper(a.get("category"), "TECH"),
                    safe_str(a.get("title")),
                    safe_upper((a.get("author") or {}).get("username"), "STAFF")
                )

    def load_admin_data(self) -> None:
        if not self.api.current_user or self.api.current_user.get("role") not in ("ADMIN", "SUPER_ADMIN"):
            return
        # Stats
        ok_st, stats = self.api.get_admin_stats()
        if ok_st and isinstance(stats, dict):
            self.query_one("#stat-users", Static).update(f"Total Users: [bold cyan]{stats.get('total_users', 0)}[/bold cyan]")
            self.query_one("#stat-articles", Static).update(f"Total Articles: [bold cyan]{stats.get('total_articles', 0)}[/bold cyan]")
            self.query_one("#stat-published", Static).update(f"Published: [bold green]{stats.get('published_articles', 0)}[/bold green]")
            self.query_one("#stat-queue", Static).update(f"In Queue: [bold yellow]{stats.get('queue_articles', 0)}[/bold yellow]")

        # Users table
        u_table = self.query_one("#users-table", DataTable)
        u_table.clear()
        ok_u, users = self.api.get_admin_users()
        if ok_u and isinstance(users, list):
            for u in users:
                u_table.add_row(str(u.get("id")), safe_str(u.get("username")), safe_str(u.get("role")), safe_str(u.get("email")))

        # Admin articles table
        a_table = self.query_one("#admin-articles-table", DataTable)
        a_table.clear()
        ok_a, articles = self.api.get_admin_articles()
        if ok_a and isinstance(articles, list):
            for a in articles:
                a_table.add_row(str(a.get("id")), safe_str(a.get("status")), safe_upper(a.get("category")), safe_str(a.get("title")), safe_upper((a.get("author") or {}).get("username")))


if __name__ == "__main__":
    app = BroadsheetApp()
    app.run()
