import flet as ft
from git_manager import GitManager


# ─── Palette ───────────────────────────────────────────────────────────────────
BG        = "#0d1117"
SURFACE   = "#161b22"
SURFACE2  = "#21262d"
BORDER    = "#30363d"
TEXT      = "#e6edf3"
TEXT_DIM  = "#8b949e"
GREEN     = "#3fb950"
GREEN_DIM = "#1a4a2e"
ORANGE    = "#d29922"
ORANGE_DIM= "#3d2b0a"
BLUE      = "#58a6ff"
BLUE_DIM  = "#0c2d6b"
RED       = "#f85149"
RED_DIM   = "#3d0f0e"
PURPLE    = "#bc8cff"
ACCENT    = "#238636"


def section_header(title: str, icon: str) -> ft.Row:
    return ft.Row([
        ft.Icon(icon, size=16, color=BLUE),
        ft.Text(title, size=13, weight=ft.FontWeight.W_600, color=TEXT),
    ], spacing=8)


def badge(label: str, color: str, bg: str) -> ft.Container:
        return ft.Container(
        content=ft.Text(label, size=11, color=color, weight=ft.FontWeight.W_500),
        bgcolor=bg, border_radius=20, padding=ft.Padding.symmetric(horizontal=4, vertical=10),
    )


class GitFlowApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "GitFlow Desktop"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = BG
        self.page.window.width = 1100
        self.page.window.height = 720
        self.page.window.min_width = 800
        self.page.window.min_height = 600
        self.page.padding = 0
        self.page.fonts = {
            "JetBrains": "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&display=swap",
        }

        self.git_manager: GitManager = None
        self.current_path = ""
        self._active_tab = "status"   # status | history | branches | stash | stats
        self._add_remote_name_ref = ft.Ref[ft.TextField]()
        self._add_remote_url_ref = ft.Ref[ft.TextField]()

        self._build_header()
        self._build_sidebar()
        self._build_status_tab()
        self._build_history_tab()
        self._build_branches_tab()
        self._build_stash_tab()
        self._build_stats_tab()
        self._build_log()
        self._assemble()

    # ─────────────────────────── Header ────────────────────────────────────────

    def _build_header(self):
        self.path_input = ft.TextField(
            hint_text="Paste your project directory path here…",
            expand=True,
            height=42,
            text_size=13,
            border_color=BORDER,
            focused_border_color=BLUE,
            bgcolor=SURFACE2,
            color=TEXT,
            cursor_color=BLUE,
            on_submit=self._load_path,
        )
        self.pick_btn = ft.IconButton(
            icon=ft.Icons.FOLDER_OPEN,
            icon_color=TEXT_DIM,
            tooltip="Browse folder",
            on_click=self._pick_folder,
        )
        self.load_btn = ft.Button(
            "Load",
            icon=ft.Icons.PLAY_ARROW,
            height=42,
            style=ft.ButtonStyle(
                bgcolor=ACCENT,
                color=TEXT,
                shape=ft.RoundedRectangleBorder(radius=6),
            ),
            on_click=self._load_path,
        )

        self.branch_badge = ft.Container(visible=False)
        self.dirty_badge = ft.Container(visible=False)

        self.header = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("⬡ GitFlow", size=18, weight=ft.FontWeight.BOLD,
                            color=BLUE, font_family="JetBrains"),
                    ft.Container(expand=True),
                    self.branch_badge,
                    self.dirty_badge,
                ]),
                ft.Row([self.path_input, self.pick_btn, self.load_btn], spacing=8),
            ], spacing=10),
            bgcolor=SURFACE,
            padding=ft.Padding.symmetric(horizontal=14, vertical=18),
            border=ft.Border(bottom=ft.BorderSide(1, BORDER)),
        )

    # ─────────────────────────── Sidebar nav ───────────────────────────────────

    def _build_sidebar(self):
        tabs = [
            ("status",   ft.Icons.DASHBOARD_OUTLINED,   "Status"),
            ("history",  ft.Icons.HISTORY,               "History"),
            ("branches", ft.Icons.ACCOUNT_TREE_OUTLINED, "Branches"),
            ("stash",    ft.Icons.INVENTORY_2_OUTLINED,  "Stash"),
            ("stats",    ft.Icons.BAR_CHART,             "Stats"),
        ]
        self._nav_buttons = {}
        nav_col = ft.Column(spacing=4)
        for key, icon, label in tabs:
            btn = ft.Container(
                content=ft.Row([
                    ft.Icon(icon, size=16),
                    ft.Text(label, size=13),
                ], spacing=10),
                padding=ft.Padding.symmetric(horizontal=10, vertical=14),
                border_radius=6,
                on_click=lambda e, k=key: self._switch_tab(k),
                ink=True,
            )
            self._nav_buttons[key] = btn
            nav_col.controls.append(btn)

        self.sidebar = ft.Container(
            content=ft.Column([
                ft.Text("NAVIGATION", size=10, color=TEXT_DIM,
                        weight=ft.FontWeight.W_600, font_family="JetBrains"),
                ft.Divider(height=1, color=BORDER),
                nav_col,
            ], spacing=8),
            width=170,
            bgcolor=SURFACE,
            padding=14,
            border=ft.Border(right=ft.BorderSide(1, BORDER)),
        )
        self._update_nav_highlight()

    def _update_nav_highlight(self):
        for key, btn in self._nav_buttons.items():
            if key == self._active_tab:
                btn.bgcolor = BLUE_DIM
                btn.content.controls[0].color = BLUE
                btn.content.controls[1].color = BLUE
            else:
                btn.bgcolor = None
                btn.content.controls[0].color = TEXT_DIM
                btn.content.controls[1].color = TEXT_DIM

    def _switch_tab(self, tab: str):
        self._active_tab = tab
        self._update_nav_highlight()
        for key, panel in self._panels.items():
            panel.visible = (key == tab)
        self.page.update()

    # ─────────────────────────── Status tab ────────────────────────────────────

    def _build_status_tab(self):
        self.staged_list   = ft.Column(spacing=4)
        self.unstaged_list = ft.Column(spacing=4)
        self.untracked_list= ft.Column(spacing=4)

        self.commit_msg = ft.TextField(
            label="Commit message",
            hint_text="feat: describe your changes",
            expand=True,
            height=42,
            text_size=13,
            border_color=BORDER,
            focused_border_color=GREEN,
            bgcolor=SURFACE2,
            color=TEXT,
        )
        self.amend_check = ft.Checkbox(label="Amend last commit", value=False,
                                        active_color=BLUE, label_style=ft.TextStyle(color=TEXT_DIM, size=12))

        self.not_repo_banner = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.WARNING_AMBER, color=ORANGE, size=32),
                    ft.Column([
                        ft.Text("Not a Git repository", size=15, weight=ft.FontWeight.BOLD, color=TEXT),
                        ft.Text("Initialize a new repo or choose a different path.", size=12, color=TEXT_DIM),
                    ], spacing=2),
                ], spacing=12),
                ft.Button(
                    "git init here",
                    icon=ft.Icons.SETTINGS_SUGGEST,
                    style=ft.ButtonStyle(bgcolor=ACCENT, color=TEXT, shape=ft.RoundedRectangleBorder(radius=6)),
                    on_click=self._init_repo,
                ),
            ], spacing=16),
            bgcolor=SURFACE2, border_radius=10,
            border=ft.Border.all(1, ORANGE),
            padding=20, visible=False,
        )

        self.remote_url_text = ft.Text("", size=11, color=TEXT_DIM, selectable=True)

        status_tab = ft.Column([
            # Remote info row
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.CLOUD_OUTLINED, size=14, color=TEXT_DIM),
                    self.remote_url_text,
                ], spacing=6),
                visible=True,
            ),
            self.not_repo_banner,

            # File sections
            ft.Container(
                content=ft.Column([
                    section_header("Staged Changes", ft.Icons.CHECK_CIRCLE_OUTLINE),
                    self.staged_list,
                ], spacing=8),
                bgcolor=SURFACE,
                border_radius=8,
                padding=14,
                border=ft.Border.all(1, BORDER),
            ),
            ft.Container(
                content=ft.Column([
                    section_header("Unstaged Changes", ft.Icons.EDIT_NOTE),
                    self.unstaged_list,
                ], spacing=8),
                bgcolor=SURFACE,
                border_radius=8,
                padding=14,
                border=ft.Border.all(1, BORDER),
            ),
            ft.Container(
                content=ft.Column([
                    section_header("Untracked Files", ft.Icons.FIBER_NEW_OUTLINED),
                    self.untracked_list,
                ], spacing=8),
                bgcolor=SURFACE,
                border_radius=8,
                padding=14,
                border=ft.Border.all(1, BORDER),
            ),

            ft.Divider(height=1, color=BORDER),

            # Commit section
            ft.Container(
                content=ft.Column([
                    section_header("Commit", ft.Icons.COMMIT),
                    ft.Row([self.commit_msg, self.amend_check], spacing=12),
                    ft.Row([
                        ft.Button("Stage All + Commit",
                            icon=ft.Icons.DONE_ALL,
                            style=ft.ButtonStyle(bgcolor=ACCENT, color=TEXT, shape=ft.RoundedRectangleBorder(radius=6)),
                            on_click=self._add_all_and_commit),
                        ft.OutlinedButton("Commit Staged",
                            icon=ft.Icons.CHECK,
                            style=ft.ButtonStyle(side=ft.BorderSide(1, GREEN), color=GREEN, shape=ft.RoundedRectangleBorder(radius=6)),
                            on_click=self._commit),
                        ft.OutlinedButton("Add All",
                            icon=ft.Icons.ADD,
                            style=ft.ButtonStyle(side=ft.BorderSide(1, BORDER), color=TEXT_DIM, shape=ft.RoundedRectangleBorder(radius=6)),
                            on_click=self._add_all),
                    ], wrap=True, spacing=8),
                ], spacing=10),
                bgcolor=SURFACE, border_radius=8, padding=14,
                border=ft.Border.all(1, BORDER),
            ),

            ft.Divider(height=1, color=BORDER),

            # Sync section
            ft.Container(
                content=ft.Column([
                    section_header("Remote Sync", ft.Icons.SYNC),
                    ft.Row([
                        ft.Button("Pull",
                            icon=ft.Icons.DOWNLOAD,
                            style=ft.ButtonStyle(bgcolor=SURFACE2, color=TEXT, shape=ft.RoundedRectangleBorder(radius=6)),
                            on_click=self._pull),
                        ft.Button("Push",
                            icon=ft.Icons.UPLOAD,
                            style=ft.ButtonStyle(bgcolor=SURFACE2, color=TEXT, shape=ft.RoundedRectangleBorder(radius=6)),
                            on_click=self._push),
                        ft.Button("Fetch All",
                            icon=ft.Icons.REFRESH,
                            style=ft.ButtonStyle(bgcolor=SURFACE2, color=TEXT, shape=ft.RoundedRectangleBorder(radius=6)),
                            on_click=self._fetch),
                        ft.OutlinedButton("Push + Set Upstream",
                            icon=ft.Icons.CLOUD_UPLOAD,
                            style=ft.ButtonStyle(side=ft.BorderSide(1, BORDER), color=TEXT_DIM, shape=ft.RoundedRectangleBorder(radius=6)),
                            on_click=self._push_upstream),
                    ], wrap=True, spacing=8),
                    # Add remote row
                    ft.Row([
                        ft.TextField(
                            ref=self._add_remote_name_ref,
                            label="Remote name", width=140, height=38, text_size=12,
                            border_color=BORDER, focused_border_color=BLUE, bgcolor=SURFACE2, color=TEXT,
                        ),
                        ft.TextField(
                            ref=self._add_remote_url_ref,
                            label="Remote URL", expand=True, height=38, text_size=12,
                            border_color=BORDER, focused_border_color=BLUE, bgcolor=SURFACE2, color=TEXT,
                        ),
                        ft.OutlinedButton("Add Remote",
                            style=ft.ButtonStyle(side=ft.BorderSide(1, BORDER), color=TEXT_DIM, shape=ft.RoundedRectangleBorder(radius=6)),
                            on_click=self._add_remote),
                    ], spacing=8),
                ], spacing=10),
                bgcolor=SURFACE, border_radius=8, padding=14,
                border=ft.Border.all(1, BORDER),
            ),
        ], spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

        self._status_panel = ft.Container(content=status_tab, expand=True, padding=ft.Padding.all(16))

    # ─────────────────────────── History tab ───────────────────────────────────

    def _build_history_tab(self):
        self.history_list = ft.Column(spacing=6)

        hist_tab = ft.Column([
            ft.Row([
                section_header("Commit History", ft.Icons.HISTORY),
                ft.Container(expand=True),
                ft.OutlinedButton("Refresh",
                    icon=ft.Icons.REFRESH,
                    style=ft.ButtonStyle(side=ft.BorderSide(1, BORDER), color=TEXT_DIM, shape=ft.RoundedRectangleBorder(radius=6)),
                    on_click=self._load_history),
            ]),
            self.history_list,
        ], spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

        self._history_panel = ft.Container(content=hist_tab, expand=True, padding=16)

    # ─────────────────────────── Branches tab ──────────────────────────────────

    def _build_branches_tab(self):
        self.local_branches_col  = ft.Column(spacing=6)
        self.remote_branches_col = ft.Column(spacing=6)

        self.new_branch_field = ft.TextField(
            label="New branch name", expand=True, height=42, text_size=13,
            border_color=BORDER, focused_border_color=BLUE, bgcolor=SURFACE2, color=TEXT,
        )
        self.merge_branch_field = ft.TextField(
            label="Branch to merge into current", expand=True, height=42, text_size=13,
            border_color=BORDER, focused_border_color=BLUE, bgcolor=SURFACE2, color=TEXT,
        )
        self.tag_name_field = ft.TextField(
            label="Tag name", width=160, height=42, text_size=13,
            border_color=BORDER, focused_border_color=BLUE, bgcolor=SURFACE2, color=TEXT,
        )
        self.tag_msg_field = ft.TextField(
            label="Tag message (optional)", expand=True, height=42, text_size=13,
            border_color=BORDER, focused_border_color=BLUE, bgcolor=SURFACE2, color=TEXT,
        )
        self.tags_col = ft.Column(spacing=4)

        branch_tab = ft.Column([
            section_header("Local Branches", ft.Icons.ACCOUNT_TREE_OUTLINED),
            self.local_branches_col,
            ft.Divider(height=1, color=BORDER),
            section_header("Remote Branches", ft.Icons.CLOUD_OUTLINED),
            self.remote_branches_col,
            ft.Divider(height=1, color=BORDER),
            ft.Container(
                content=ft.Column([
                    section_header("Create Branch", ft.Icons.ADD_CIRCLE_OUTLINE),
                    ft.Row([
                        self.new_branch_field,
                        ft.Button("Create",
                            style=ft.ButtonStyle(bgcolor=SURFACE2, color=TEXT, shape=ft.RoundedRectangleBorder(radius=6)),
                            on_click=self._create_branch),
                        ft.Button("Create & Switch",
                            style=ft.ButtonStyle(bgcolor=ACCENT, color=TEXT, shape=ft.RoundedRectangleBorder(radius=6)),
                            on_click=self._create_and_switch_branch),
                    ], spacing=8),
                ], spacing=10),
                bgcolor=SURFACE, border_radius=8, padding=14, border=ft.Border.all(1, BORDER),
            ),
            ft.Container(
                content=ft.Column([
                    section_header("Merge", ft.Icons.MERGE_TYPE),
                    ft.Row([
                        self.merge_branch_field,
                        ft.Button("Merge into current",
                            style=ft.ButtonStyle(bgcolor=SURFACE2, color=TEXT, shape=ft.RoundedRectangleBorder(radius=6)),
                            on_click=self._merge_branch),
                    ], spacing=8),
                ], spacing=10),
                bgcolor=SURFACE, border_radius=8, padding=14, border=ft.Border.all(1, BORDER),
            ),
            ft.Container(
                content=ft.Column([
                    section_header("Tags", ft.Icons.LABEL_OUTLINE),
                    self.tags_col,
                    ft.Row([
                        self.tag_name_field,
                        self.tag_msg_field,
                        ft.Button("Create Tag",
                            style=ft.ButtonStyle(bgcolor=SURFACE2, color=TEXT, shape=ft.RoundedRectangleBorder(radius=6)),
                            on_click=self._create_tag),
                    ], spacing=8),
                ], spacing=10),
                bgcolor=SURFACE, border_radius=8, padding=14, border=ft.Border.all(1, BORDER),
            ),
        ], spacing=14, scroll=ft.ScrollMode.AUTO, expand=True)

        self._branches_panel = ft.Container(content=branch_tab, expand=True, padding=16)

    # ─────────────────────────── Stash tab ─────────────────────────────────────

    def _build_stash_tab(self):
        self.stash_list_col = ft.Column(spacing=6)
        self.stash_msg_field = ft.TextField(
            label="Stash message (optional)", expand=True, height=42, text_size=13,
            border_color=BORDER, focused_border_color=BLUE, bgcolor=SURFACE2, color=TEXT,
        )

        stash_tab = ft.Column([
            ft.Container(
                content=ft.Column([
                    section_header("Stash Changes", ft.Icons.INVENTORY_2_OUTLINED),
                    ft.Row([
                        self.stash_msg_field,
                        ft.Button("Stash",
                            icon=ft.Icons.SAVE,
                            style=ft.ButtonStyle(bgcolor=ACCENT, color=TEXT, shape=ft.RoundedRectangleBorder(radius=6)),
                            on_click=self._stash),
                        ft.OutlinedButton("Pop Latest",
                            icon=ft.Icons.UNARCHIVE,
                            style=ft.ButtonStyle(side=ft.BorderSide(1, BORDER), color=TEXT_DIM, shape=ft.RoundedRectangleBorder(radius=6)),
                            on_click=self._stash_pop),
                    ], spacing=8),
                ], spacing=10),
                bgcolor=SURFACE, border_radius=8, padding=14, border=ft.Border.all(1, BORDER),
            ),
            section_header("Stash List", ft.Icons.LIST),
            self.stash_list_col,
        ], spacing=14, scroll=ft.ScrollMode.AUTO, expand=True)

        self._stash_panel = ft.Container(content=stash_tab, expand=True, padding=16)

    # ─────────────────────────── Stats tab ─────────────────────────────────────

    def _build_stats_tab(self):
        self.stats_col = ft.Column(spacing=12)

        stats_tab = ft.Column([
            ft.Row([
                section_header("Repository Stats", ft.Icons.BAR_CHART),
                ft.Container(expand=True),
                ft.OutlinedButton("Refresh",
                    icon=ft.Icons.REFRESH,
                    style=ft.ButtonStyle(side=ft.BorderSide(1, BORDER), color=TEXT_DIM, shape=ft.RoundedRectangleBorder(radius=6)),
                    on_click=self._load_stats),
            ]),
            self.stats_col,
        ], spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

        self._stats_panel = ft.Container(content=stats_tab, expand=True, padding=16)

    # ─────────────────────────── Log ───────────────────────────────────────────

    def _build_log(self):
        self.log_col = ft.Column(spacing=2)
        self.log_container = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.TERMINAL, size=14, color=TEXT_DIM),
                    ft.Text("OUTPUT LOG", size=10, color=TEXT_DIM, weight=ft.FontWeight.W_600, font_family="JetBrains"),
                    ft.Container(expand=True),
                    ft.IconButton(ft.Icons.DELETE_SWEEP, icon_color=TEXT_DIM, tooltip="Clear log",
                                  icon_size=16, on_click=lambda _: self._clear_log()),
                ]),
                ft.Container(
                    content=ft.Column(
                        controls=[self.log_col],
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    bgcolor=BG, border_radius=6, padding=10, height=130,
                ),
            ], spacing=6),
            bgcolor=SURFACE,
            padding=12,
            border=ft.Border(top=ft.BorderSide(1, BORDER)),
        )

    # ─────────────────────────── Assembly ──────────────────────────────────────

    def _assemble(self):
        self._panels = {
            "status":   self._status_panel,
            "history":  self._history_panel,
            "branches": self._branches_panel,
            "stash":    self._stash_panel,
            "stats":    self._stats_panel,
        }
        for key, panel in self._panels.items():
            panel.visible = (key == self._active_tab)

        content_area = ft.Stack(
            controls=list(self._panels.values()),
            expand=True,
        )

        body = ft.Row([
            self.sidebar,
            content_area,
        ], expand=True, spacing=0)

        self.page.add(
            self.header,
            ft.Container(content=body, expand=True),
            self.log_container,
        )

    # ─────────────────────────── Helpers ───────────────────────────────────────

    def log(self, message: str, color: str = TEXT):
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_col.controls.append(
            ft.Text(f"[{ts}] {message}", size=11, color=color, font_family="JetBrains", selectable=True)
        )
        # Keep last 100 lines
        if len(self.log_col.controls) > 100:
            self.log_col.controls = self.log_col.controls[-100:]
        self.page.update()

    def _clear_log(self):
        self.log_col.controls.clear()
        self.page.update()

    def _refresh_all(self):
        """Refresh status and currently open tab."""
        if not self.git_manager:
            return
        status = self.git_manager.scan_directory()
        self._update_status_ui(status)
        if self._active_tab == "history":
            self._load_history(None)
        elif self._active_tab == "branches":
            self._load_branches()
        elif self._active_tab == "stash":
            self._load_stash()
        elif self._active_tab == "stats":
            self._load_stats(None)

    def _update_status_ui(self, status: dict):
        if status.get("error"):
            self.log(f"Error: {status['error']}", RED)
            self.not_repo_banner.visible = True
            return

        if status["is_repo"]:
            self.not_repo_banner.visible = False

            # Header badges
            self.branch_badge.visible = True
            self.branch_badge.content = ft.Row([
                ft.Icon(ft.Icons.ACCOUNT_TREE, size=14, color=GREEN),
                ft.Text(status["branch"] or "HEAD", size=12, color=GREEN, font_family="JetBrains"),
            ], spacing=4)
            self.branch_badge.bgcolor = GREEN_DIM
            self.branch_badge.border_radius = 20
            self.branch_badge.padding = ft.Padding.symmetric(horizontal=4, vertical=10)

            self.dirty_badge.visible = True
            if status["is_dirty"]:
                self.dirty_badge.content = ft.Text("● dirty", size=12, color=ORANGE, font_family="JetBrains")
                self.dirty_badge.bgcolor = ORANGE_DIM
            else:
                self.dirty_badge.content = ft.Text("✓ clean", size=12, color=GREEN, font_family="JetBrains")
                self.dirty_badge.bgcolor = GREEN_DIM
            self.dirty_badge.border_radius = 20
            self.dirty_badge.padding = ft.Padding.symmetric(horizontal=4, vertical=10)

            # Remote URL
            remotes = self.git_manager.get_remotes()
            if remotes:
                self.remote_url_text.value = f"origin: {remotes[0]['url']}"
            else:
                self.remote_url_text.value = "No remotes configured"

            # Build file lists
            self._build_file_list(self.staged_list, status["staged_files"], "staged")
            self._build_file_list(self.unstaged_list, status["unstaged_files"], "unstaged")
            self._build_file_list(self.untracked_list, status["untracked_files"], "untracked")

        else:
            self.branch_badge.visible = False
            self.dirty_badge.visible = False
            self.not_repo_banner.visible = True
            self.remote_url_text.value = ""

        self.page.update()

    def _build_file_list(self, col: ft.Column, files: list, kind: str):
        col.controls.clear()
        if not files:
            col.controls.append(ft.Text("  No files", size=12, color=TEXT_DIM, italic=True))
            return
        for f in files:
            if kind == "staged":
                color, icon, action_icon, action_tip = GREEN, ft.Icons.CHECK_CIRCLE_OUTLINE, ft.Icons.REMOVE_CIRCLE_OUTLINE, "Unstage"
                action = lambda e, fp=f: self._unstage_file(fp)
            elif kind == "unstaged":
                color, icon, action_icon, action_tip = ORANGE, ft.Icons.EDIT_NOTE, ft.Icons.ADD_CIRCLE_OUTLINE, "Stage"
                action = lambda e, fp=f: self._stage_file(fp)
                discard = lambda e, fp=f: self._discard_file(fp)
            else:
                color, icon, action_icon, action_tip = BLUE, ft.Icons.FIBER_NEW_OUTLINED, ft.Icons.ADD_CIRCLE_OUTLINE, "Track & Stage"
                action = lambda e, fp=f: self._stage_file(fp)

            row_controls = [
                ft.Icon(icon, size=14, color=color),
                ft.Text(f, size=12, expand=True, color=TEXT, font_family="JetBrains", selectable=True),
                ft.IconButton(action_icon, icon_color=color, icon_size=16,
                              tooltip=action_tip, on_click=action),
            ]
            if kind == "unstaged":
                row_controls.append(
                    ft.IconButton(ft.Icons.UNDO, icon_color=RED, icon_size=16,
                                  tooltip="Discard changes", on_click=discard)
                )
            if kind != "untracked":
                row_controls.append(
                    ft.IconButton(ft.Icons.DIFFERENCE_OUTLINED, icon_color=TEXT_DIM, icon_size=16,
                                  tooltip="View diff", on_click=lambda e, fp=f, st=(kind=="staged"): self._show_diff(fp, st))
                )
            col.controls.append(
                ft.Container(
                    content=ft.Row(row_controls, spacing=4),
                    bgcolor=SURFACE2, border_radius=6, padding=ft.Padding.symmetric(horizontal=4, vertical=8),
                )
            )

    def _load_history(self, e):
        if not self.git_manager:
            return
        history = self.git_manager.get_history(50)
        self.history_list.controls.clear()
        if not history:
            self.history_list.controls.append(ft.Text("No commits yet.", color=TEXT_DIM, italic=True, size=12))
        else:
            for commit in history:
                self.history_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Container(
                                content=ft.Text(commit["hash"], size=11, color=PURPLE, font_family="JetBrains"),
                                bgcolor=SURFACE2, border_radius=4, padding=ft.Padding.symmetric(horizontal=2, vertical=6),
                            ),
                            ft.Column([
                                ft.Text(commit["subject"], size=13, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(f"{commit['author']}  ·  {commit['date']}", size=11, color=TEXT_DIM),
                            ], spacing=2, expand=True),
                            ft.OutlinedButton(
                                "Checkout",
                                style=ft.ButtonStyle(side=ft.BorderSide(1, BORDER), color=TEXT_DIM, shape=ft.RoundedRectangleBorder(radius=4)),
                                on_click=lambda e, h=commit["hash"]: self._checkout_commit(h),
                            ),
                        ], spacing=10),
                        bgcolor=SURFACE, border_radius=8, padding=12,
                        border=ft.Border.all(1, BORDER),
                    )
                )
        self.page.update()

    def _load_branches(self):
        if not self.git_manager:
            return
        branches = self.git_manager.get_branches()
        current = self.git_manager.scan_directory().get("branch", "")

        self.local_branches_col.controls.clear()
        for b in branches["local"]:
            is_current = (b == current)
            self.local_branches_col.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CIRCLE, size=10, color=GREEN if is_current else TEXT_DIM),
                        ft.Text(b, size=12, expand=True, color=GREEN if is_current else TEXT, font_family="JetBrains"),
                        ft.OutlinedButton("Switch",
                            style=ft.ButtonStyle(side=ft.BorderSide(1, BORDER), color=TEXT_DIM, shape=ft.RoundedRectangleBorder(radius=4)),
                            disabled=is_current,
                            on_click=lambda e, br=b: self._switch_branch(br),
                        ),
                        ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=RED, icon_size=16,
                                      tooltip="Delete branch", disabled=is_current,
                                      on_click=lambda e, br=b: self._delete_branch(br)),
                    ], spacing=8),
                     bgcolor=GREEN_DIM if is_current else SURFACE2,
                     border_radius=6, padding=ft.Padding.symmetric(horizontal=6, vertical=10),
                     border=ft.Border.all(1, GREEN if is_current else BORDER),
                )
            )

        self.remote_branches_col.controls.clear()
        for b in branches["remote"]:
            self.remote_branches_col.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CLOUD_OUTLINED, size=12, color=TEXT_DIM),
                        ft.Text(b, size=12, color=TEXT_DIM, font_family="JetBrains"),
                    ], spacing=8),
                     bgcolor=SURFACE2, border_radius=6, padding=ft.Padding.symmetric(horizontal=6, vertical=10),
                )
            )
        if not branches["remote"]:
            self.remote_branches_col.controls.append(ft.Text("No remote branches", size=12, color=TEXT_DIM, italic=True))

        # Tags
        tags = self.git_manager.get_tags()
        self.tags_col.controls.clear()
        if tags:
            self.tags_col.controls.append(
                ft.Row([
                    badge(t, PURPLE, SURFACE2)
                    for t in tags[:10]
                ], wrap=True, spacing=6)
            )
        else:
            self.tags_col.controls.append(ft.Text("No tags", size=12, color=TEXT_DIM, italic=True))

        self.page.update()

    def _load_stash(self):
        if not self.git_manager:
            return
        stashes = self.git_manager.stash_list()
        self.stash_list_col.controls.clear()
        if not stashes:
            self.stash_list_col.controls.append(ft.Text("Stash is empty.", size=12, color=TEXT_DIM, italic=True))
        else:
            for s in stashes:
                self.stash_list_col.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Container(
                                content=ft.Text(s["ref"], size=11, color=ORANGE, font_family="JetBrains"),
                                 bgcolor=ORANGE_DIM, border_radius=4, padding=ft.Padding.symmetric(horizontal=2, vertical=6),
                            ),
                            ft.Text(s["message"], size=12, expand=True, color=TEXT),
                        ], spacing=10),
                        bgcolor=SURFACE, border_radius=8, padding=12,
                        border=ft.Border.all(1, BORDER),
                    )
                )
        self.page.update()

    def _load_stats(self, e):
        if not self.git_manager:
            return
        stats = self.git_manager.get_stats()
        self.stats_col.controls.clear()

        self.stats_col.controls.append(
            ft.Container(
                content=ft.Row([
                    ft.Column([
                        ft.Text("Total Commits", size=11, color=TEXT_DIM),
                        ft.Text(stats.get("total_commits", "—"), size=32, weight=ft.FontWeight.BOLD, color=BLUE),
                    ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.VerticalDivider(width=1, color=BORDER),
                    ft.Column([
                        ft.Text("Top Contributors", size=11, color=TEXT_DIM, weight=ft.FontWeight.W_600),
                        *[ft.Row([
                            ft.Text(c["count"], size=12, color=GREEN, width=40, font_family="JetBrains"),
                            ft.Text(c["name"], size=12, color=TEXT),
                        ]) for c in stats.get("contributors", [])],
                    ], spacing=4, expand=True),
                ], spacing=24),
                bgcolor=SURFACE, border_radius=8, padding=20, border=ft.Border.all(1, BORDER),
            )
        )

        remotes = stats.get("remotes", [])
        if remotes:
            remote_rows = [
                ft.Row([
                    ft.Icon(ft.Icons.CLOUD_OUTLINED, size=14, color=BLUE),
                    ft.Text(r["name"], size=12, color=TEXT_DIM, width=80),
                    ft.Text(r["url"], size=12, color=BLUE, selectable=True, expand=True),
                ])
                for r in remotes
            ]
            self.stats_col.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Text("Remotes", size=13, weight=ft.FontWeight.W_600, color=TEXT),
                        *remote_rows,
                    ], spacing=8),
                    bgcolor=SURFACE, border_radius=8, padding=16, border=ft.Border.all(1, BORDER),
                )
            )

        self.page.update()

    # ─────────────────────────── Event handlers ─────────────────────────────────

    def _pick_folder(self, e):
        def result(ev: ft.FilePickerResultEvent):
            if ev.path:
                self.path_input.value = ev.path
                self.page.update()
                self._load_path(None)

        picker = ft.FilePicker(on_result=result)
        self.page.overlay.append(picker)
        self.page.update()
        picker.get_directory_path(dialog_title="Select project directory")

    def _load_path(self, e):
        path = self.path_input.value.strip() if self.path_input.value else ""
        if not path:
            self.log("Please enter a path.", ORANGE)
            return
        self.current_path = path
        self.git_manager = GitManager(path)
        self.log(f"Loading: {path}")
        status = self.git_manager.scan_directory()
        self._update_status_ui(status)
        self._load_history(None)
        self._load_branches()
        self._load_stash()
        self._load_stats(None)

    def _stage_file(self, file_path: str):
        if self.git_manager:
            res = self.git_manager.add_file(file_path)
            self.log(res, GREEN)
            self._update_status_ui(self.git_manager.scan_directory())

    def _unstage_file(self, file_path: str):
        if self.git_manager:
            res = self.git_manager.unstage_file(file_path)
            self.log(res, ORANGE)
            self._update_status_ui(self.git_manager.scan_directory())

    def _discard_file(self, file_path: str):
        def confirm(e):
            dlg.open = False
            self.page.update()
            if e.control.text == "Discard":
                res = self.git_manager.discard_changes(file_path)
                self.log(res, RED)
                self._update_status_ui(self.git_manager.scan_directory())

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Discard changes?", color=RED),
            content=ft.Text(f"This will permanently discard all changes to:\n{file_path}", size=13, color=TEXT),
            actions=[
                ft.TextButton("Cancel", style=ft.ButtonStyle(color=TEXT_DIM), on_click=confirm),
                ft.Button("Discard", style=ft.ButtonStyle(bgcolor=RED, color=TEXT), on_click=confirm),
            ],
        )
        self.page.open(dlg)

    def _show_diff(self, file_path: str, staged: bool):
        if not self.git_manager:
            return
        diff = self.git_manager.get_diff(file_path, staged)
        if not diff:
            diff = "No diff available."

        lines = []
        for line in diff.splitlines()[:300]:
            if line.startswith("+") and not line.startswith("+++"):
                color = GREEN
            elif line.startswith("-") and not line.startswith("---"):
                color = RED
            elif line.startswith("@@"):
                color = BLUE
            else:
                color = TEXT_DIM
            lines.append(ft.Text(line, size=11, color=color, font_family="JetBrains", selectable=True))

        dlg = ft.AlertDialog(
            title=ft.Text(f"Diff: {file_path}", size=14, color=BLUE),
            content=ft.Container(
                content=ft.Column(lines, scroll=ft.ScrollMode.AUTO, spacing=0),
                bgcolor=BG, border_radius=6, padding=10,
                width=700, height=450,
            ),
            actions=[ft.TextButton("Close", on_click=lambda _: self.page.close(dlg))],
        )
        self.page.open(dlg)

    def _add_all(self, e):
        if self.git_manager:
            res = self.git_manager.add_all()
            self.log(res, GREEN)
            self._update_status_ui(self.git_manager.scan_directory())

    def _commit(self, e):
        if not self.git_manager:
            return
        msg = self.commit_msg.value.strip() if self.commit_msg.value else ""
        if not msg:
            self.log("Commit message is empty.", ORANGE)
            return
        res = self.git_manager.commit(msg)
        self.log(res, GREEN if "Error" not in res else RED)
        self.commit_msg.value = ""
        self._update_status_ui(self.git_manager.scan_directory())

    def _add_all_and_commit(self, e):
        if not self.git_manager:
            return
        msg = self.commit_msg.value.strip() if self.commit_msg.value else ""
        if not msg:
            self.log("Commit message is empty.", ORANGE)
            return
        r1 = self.git_manager.add_all()
        self.log(r1, GREEN)
        r2 = self.git_manager.commit(msg)
        self.log(r2, GREEN if "Error" not in r2 else RED)
        self.commit_msg.value = ""
        self._update_status_ui(self.git_manager.scan_directory())

    def _pull(self, e):
        if self.git_manager:
            self.log("Pulling…")
            res = self.git_manager.pull()
            self.log(res, GREEN if "successful" in res else RED)
            self._refresh_all()

    def _push(self, e):
        if self.git_manager:
            self.log("Pushing…")
            res = self.git_manager.push()
            self.log(res, GREEN if "successful" in res else RED)

    def _push_upstream(self, e):
        if self.git_manager:
            status = self.git_manager.scan_directory()
            branch = status.get("branch", "main")
            self.log(f"Pushing with --set-upstream origin {branch}…")
            res = self.git_manager.push_set_upstream(branch)
            self.log(res, GREEN if "successful" in res else RED)

    def _fetch(self, e):
        if self.git_manager:
            self.log("Fetching all remotes…")
            res = self.git_manager.fetch()
            self.log(res, GREEN if "complete" in res else RED)

    def _add_remote(self, e):
        if not self.git_manager:
            return
        name = self._add_remote_name_ref.current.value.strip()
        url  = self._add_remote_url_ref.current.value.strip()
        if not name or not url:
            self.log("Remote name and URL are required.", ORANGE)
            return
        res = self.git_manager.add_remote(name, url)
        self.log(res, GREEN if "added" in res else RED)
        self._add_remote_name_ref.current.value = ""
        self._add_remote_url_ref.current.value = ""
        self._load_stats(None)
        self.page.update()

    def _init_repo(self, e):
        if self.git_manager:
            res = self.git_manager.initialize_repo()
            self.log(res, GREEN if "successfully" in res else RED)
            self._refresh_all()

    def _checkout_commit(self, commit_hash: str):
        if self.git_manager:
            res = self.git_manager.checkout_commit(commit_hash)
            self.log(res, GREEN if "Error" not in res else RED)
            self._refresh_all()

    def _switch_branch(self, branch: str):
        if self.git_manager:
            res = self.git_manager.checkout_branch(branch)
            self.log(res, GREEN if "Error" not in res else RED)
            self._refresh_all()

    def _create_branch(self, e):
        if not self.git_manager:
            return
        name = self.new_branch_field.value.strip()
        if not name:
            return
        res = self.git_manager.create_branch(name)
        self.log(res, GREEN if "Error" not in res else RED)
        self.new_branch_field.value = ""
        self._load_branches()

    def _create_and_switch_branch(self, e):
        if not self.git_manager:
            return
        name = self.new_branch_field.value.strip()
        if not name:
            return
        res = self.git_manager.create_and_checkout_branch(name)
        self.log(res, GREEN if "Error" not in res else RED)
        self.new_branch_field.value = ""
        self._refresh_all()

    def _delete_branch(self, branch: str):
        def confirm(e):
            dlg.open = False
            self.page.update()
            if e.control.text == "Delete":
                res = self.git_manager.delete_branch(branch)
                self.log(res, RED if "Error" in res else GREEN)
                self._load_branches()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Delete branch '{branch}'?", color=RED),
            content=ft.Text("This cannot be undone.", size=13, color=TEXT_DIM),
            actions=[
                ft.TextButton("Cancel", style=ft.ButtonStyle(color=TEXT_DIM), on_click=confirm),
                ft.Button("Delete", style=ft.ButtonStyle(bgcolor=RED, color=TEXT), on_click=confirm),
            ],
        )
        self.page.open(dlg)

    def _merge_branch(self, e):
        if not self.git_manager:
            return
        name = self.merge_branch_field.value.strip()
        if not name:
            return
        res = self.git_manager.merge_branch(name)
        self.log(res, GREEN if "Error" not in res and "failed" not in res else RED)
        self.merge_branch_field.value = ""
        self._refresh_all()

    def _stash(self, e):
        if not self.git_manager:
            return
        msg = self.stash_msg_field.value.strip() if self.stash_msg_field.value else ""
        res = self.git_manager.stash(msg)
        self.log(res, GREEN if "Error" not in res else RED)
        self.stash_msg_field.value = ""
        self._load_stash()
        self._update_status_ui(self.git_manager.scan_directory())

    def _stash_pop(self, e):
        if not self.git_manager:
            return
        res = self.git_manager.stash_pop()
        self.log(res, GREEN if "Error" not in res else RED)
        self._load_stash()
        self._update_status_ui(self.git_manager.scan_directory())

    def _create_tag(self, e):
        if not self.git_manager:
            return
        name = self.tag_name_field.value.strip()
        msg = self.tag_msg_field.value.strip() if self.tag_msg_field.value else ""
        if not name:
            return
        res = self.git_manager.create_tag(name, msg)
        self.log(res, GREEN if "Error" not in res else RED)
        self.tag_name_field.value = ""
        self.tag_msg_field.value = ""
        self._load_branches()


def main(page: ft.Page):
    GitFlowApp(page)
    page.update()


if __name__ == "__main__":
    ft.run(main)