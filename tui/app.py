# pip install textual
# python dashboard.py

from textual.app import App, ComposeResult
from textual.widgets import Static, Header, Footer
from textual.containers import Grid, Vertical, Horizontal
from textual.reactive import reactive
from textual import work
from textual.timer import Timer
from rich.text import Text
from rich.table import Table
from rich.panel import Panel
from rich.progress import BarColumn, Progress
from rich.console import Console
from rich import box
import random
import time
from datetime import datetime, timezone


# ── DATA ──────────────────────────────────────────────────────────────────────

SOURCES = [
    ("Photo AI",    107209, "#af87ff"),
    ("Remote OK",     5840, "#00ff87"),
    ("Nomads.com",    3120, "#00afff"),
    ("Interior AI",   1530, "#ff8700"),
    ("MAKE Book",      505, "#ffd700"),
]

LOCATIONS = ["United States", "Germany", "Japan", "India", "Kazakhstan",
             "Brazil", "Singapore", "Canada", "Netherlands", "Australia"]

PRODUCTS = ["Photo AI", "Remote OK", "Nomads.com", "Interior AI", "MAKE Book"]
PROD_COLORS = {
    "Photo AI":    "#af87ff",
    "Remote OK":   "#00ff87",
    "Nomads.com":  "#00afff",
    "Interior AI": "#ff8700",
    "MAKE Book":   "#ffd700",
}

AMOUNTS = [9, 19, 29, 49, 99, 197, 299]

LOGS = [
    ("00m", "●", "#00ff87", "set match time to 10m for q3.pieter.com",         "Pieter"),
    ("36m", "●", "#00ff87", "q3.pieter.com server busy",                        "Pieter"),
    ("49m", "●", "#00ff87", "launch q3.pieter.com on X",                        "Pieter"),
    ("5h",  "○", "#555555", "make daily match at UTC countdown",                 "Pieter"),
    ("6h",  "○", "#555555", "add web notifications for player threshold",        "Pieter"),
    ("7h",  "○", "#555555", "show human players in green",                       "Pieter"),
    ("22h", "○", "#555555", "fix infinite redirect on missing profile pic",      "Nomads"),
]

BUGS = [
    ("✗", "#ff5f5f", "Telegram not working",            "Nomads"),
    ("!", "#ff8700", "Nothing really works",             "Interior"),
    ("?", "#00afff", "Find more sponsors for Nomads",   "Nomads"),
    ("→", "#00ff87", "Enable B2 backups — Hotel List",  "Hotels"),
    ("→", "#00ff87", "Migrate Photo AI to own VPS",     "Photo AI"),
]

SERVICES = [
    ("Photo AI",    "99.9%", "up"),
    ("Remote OK",   "99.7%", "up"),
    ("Nomads.com",  "DOWN",  "down"),
    ("Pieter.com",  "98.2%", "warn"),
    ("Hotel List",  "99.1%", "up"),
    ("MAKE Book",   "99.5%", "up"),
    ("Interior AI", "99.9%", "up"),
    ("levelsio",    "100%",  "up"),
]

INFRA = [
    ("CPU",       34),
    ("MEMORY",    61),
    ("DISK I/O",  18),
    ("NETWORK",   88),
    ("DB CONNS",  45),
]


# ── WIDGETS ───────────────────────────────────────────────────────────────────

class MetricsPanel(Static):
    """Top-left: Revenue metrics + source breakdown."""

    gross   = reactive(118204)
    mrr     = reactive(15322)
    net_rev = reactive(11421)
    last_pay= reactive(197)

    def render(self) -> Panel:
        t = Text()

        # ── big numbers ──
        def stat_line(label, val, color, delta=""):
            t.append(f" {label:<14}", style="dim")
            t.append(f"${val:>10,}", style=f"bold {color}")
            if delta:
                col = "#00ff87" if delta.startswith("▲") else "#ff5f5f"
                t.append(f"  {delta}", style=col)
            t.append("\n")

        t.append(" ┌─ REVENUE ─────────────────────────────────────────\n", style="dim")
        stat_line("GROSS",        self.gross,    "#00ff87", "▲ +4.2%")
        stat_line("MRR",          self.mrr,      "#00afff", "▲ +1.8%")
        stat_line("NET REVENUE",  self.net_rev,  "#ffd700", "▼ -0.3%")
        stat_line("LAST PAYMENT", self.last_pay, "#ff5f5f")
        t.append(" └───────────────────────────────────────────────────\n", style="dim")

        # ── source breakdown ──
        t.append("\n SOURCE BREAKDOWN\n", style="dim italic")
        bar_width = 28
        total = sum(v for _, v, _ in SOURCES)
        for name, val, color in SOURCES:
            pct = val / total
            filled = int(pct * bar_width)
            bar = "█" * filled + "░" * (bar_width - filled)
            t.append(f" {name:<12}", style="dim")
            t.append(bar, style=color)
            t.append(f"  ${val:>7,}\n", style=f"{color} bold")

        return Panel(t, title="[bold #00ff87]▸ REVENUE / METRICS[/]",
                     border_style="#1e2530", padding=(0, 0))

    def on_mount(self) -> None:
        self.set_interval(4.5, self._jitter)

    def _jitter(self) -> None:
        self.mrr = 15322 + random.randint(-60, 60)
        self.gross += random.randint(0, 199)


class ShippingLog(Static):
    """Top-right: Shipping / activity log."""

    tick = reactive(0)

    def render(self) -> Panel:
        t = Text()
        now = datetime.now(timezone.utc)
        t.append(f" UTC {now.strftime('%H:%M:%S')}\n\n", style="dim")

        for age, dot, dot_col, msg, src in LOGS:
            t.append(f" {age:>4} ", style="dim")
            t.append(dot + " ", style=f"bold {dot_col}")
            t.append(f"{msg[:46]:<46}", style="white")
            t.append(f" {src}\n", style="dim")

        return Panel(t, title="[bold #00afff]▸ SHIPPING LOG  [dim]WIP.CO[/][/]",
                     border_style="#1e2530", padding=(0, 0))

    def on_mount(self) -> None:
        self.set_interval(1, lambda: setattr(self, "tick", self.tick + 1))


class SystemStatus(Static):
    """Bottom-left: Infra gauges + uptime + bugs."""

    tick = reactive(0)
    _cpu = 34

    def render(self) -> Panel:
        t = Text()

        # ── infra gauges ──
        t.append(" INFRASTRUCTURE\n", style="dim italic")
        bar_w = 24
        infra = list(INFRA)
        infra[0] = ("CPU", self._cpu)
        for name, pct in infra:
            if pct >= 80:   col = "#ff5f5f"
            elif pct >= 55: col = "#ffd700"
            else:           col = "#00ff87"
            filled = int((pct / 100) * bar_w)
            bar = "█" * filled + "░" * (bar_w - filled)
            t.append(f" {name:<10}", style="dim")
            t.append(bar, style=col)
            t.append(f" {pct:>3}%\n", style=f"bold {col}")

        # ── service uptime ──
        t.append("\n SERVICE UPTIME\n", style="dim italic")
        for i, (svc, val, state) in enumerate(SERVICES):
            col = {"up": "#00ff87", "down": "#ff5f5f", "warn": "#ffd700"}[state]
            t.append(f" {svc:<14}", style="dim")
            t.append(f"{val:>6}", style=f"bold {col}")
            if i % 2 == 1:
                t.append("\n")
            else:
                t.append("   ")
        t.append("\n")

        # ── bugs / ideas ──
        t.append("\n IDEAS + BUGS\n", style="dim italic")
        for icon, col, msg, src in BUGS:
            t.append(f" {icon} ", style=f"bold {col}")
            t.append(f"{msg[:40]:<40}", style="white")
            t.append(f" {src}\n", style="dim")

        return Panel(t, title="[bold #ffd700]▸ SYSTEM STATUS[/]",
                     border_style="#1e2530", padding=(0, 0))

    def on_mount(self) -> None:
        self.set_interval(2, self._update)

    def _update(self) -> None:
        self._cpu = max(5, min(99, self._cpu + random.randint(-4, 6)))
        self.tick += 1


class LiveFeed(Static):
    """Bottom-right: Live transaction stream."""

    transactions: reactive = reactive([], recompose=False)
    tick = reactive(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._txns = []

    def _add_txn(self) -> None:
        prod = random.choice(PRODUCTS)
        loc  = random.choice(LOCATIONS)
        amt  = random.choice(AMOUNTS)
        uid  = "usr_" + "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=5))
        self._txns.insert(0, (uid, prod, loc, amt, "just now"))
        if len(self._txns) > 12:
            self._txns.pop()
        self.tick += 1

    def render(self) -> Panel:
        t = Text()
        t.append(" ● LIVE TRANSACTIONS\n\n", style="bold #ff5f5f")

        if not self._txns:
            t.append(" Waiting for transactions…\n", style="dim")
        else:
            for uid, prod, loc, amt, when in self._txns:
                col = PROD_COLORS.get(prod, "#ffffff")
                t.append(f" {uid:<12}", style="dim")
                t.append(f"  +${amt:<5}", style=f"bold {col}")
                t.append(f"  {prod:<14}", style=col)
                t.append(f"  {loc}\n", style="dim")

        t.append("\n")
        total_today = sum(a for _, _, _, a, _ in self._txns)
        t.append(f" Session total: ", style="dim")
        t.append(f"${total_today:,}", style="bold #00ff87")
        t.append(f"  ({len(self._txns)} txns)\n", style="dim")

        return Panel(t, title="[bold #ff5f5f]▸ LIVE FEED  [blink]●[/][/]",
                     border_style="#1e2530", padding=(0, 0))

    def on_mount(self) -> None:
        self.set_interval(2.5, self._add_txn)


# ── APP ───────────────────────────────────────────────────────────────────────

CSS = """
Screen {
    background: #0a0c0f;
}

Grid {
    grid-size: 2 2;
    grid-gutter: 1;
    padding: 0 1;
    height: 1fr;
}

MetricsPanel, ShippingLog, SystemStatus, LiveFeed {
    height: 1fr;
}

Header {
    background: #0d1117;
    color: #00ff87;
}

Footer {
    background: #0d1117;
    color: #556070;
}
"""


class SituationMonitor(App):
    CSS = CSS
    TITLE = "SITUATION MONITOR"
    SUB_TITLE = "▓ live dashboard"

    BINDINGS = [
        ("q", "quit",       "Quit"),
        ("r", "refresh",    "Refresh"),
        ("d", "dark",       "Theme"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Grid(
            MetricsPanel(),
            ShippingLog(),
            SystemStatus(),
            LiveFeed(),
        )
        yield Footer()

    def action_refresh(self) -> None:
        self.refresh(layout=True)

    def action_dark(self) -> None:
        self.dark = not self.dark


if __name__ == "__main__":
    SituationMonitor().run()