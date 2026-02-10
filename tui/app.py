import asyncio
import os
from dataclasses import dataclass
from datetime import datetime
from typing import List

import httpx
import plotext as plt
from rich.text import Text
from textual import events, on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    Static,
    TabbedContent,
    TabPane,
)

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

# Bloomberg Colors
BG = "#000000"
HEADER_TEXT = "#FFB000"  # Amber
UI_CYAN = "#00FFFF"
POSITIVE = "#00FF00"
NEGATIVE = "#FF1A1A"
DIM_TEXT = "#94a3b8"

@dataclass
class IndexSnapshot:
    name: str
    value: float
    change_pct: float

@dataclass
class MarketOverview:
    as_of: str
    indices: List[IndexSnapshot]
    advances: int
    declines: int
    sectors: List[dict]

class CommandBar(Input):
    """Bloomberg-style command bar."""
    def on_mount(self) -> None:
        self.placeholder = "Enter Command or Ticker (e.g. RELIANCE, GO STARTUPS)"

class LiveTicker(Static):
    """Scrolling market ticker."""
    def __init__(self) -> None:
        super().__init__()
        self.data = []
        self._offset = 0

    def on_mount(self) -> None:
        self.set_interval(0.1, self.update_ticker)

    def update_ticker(self) -> None:
        if not self.data:
            return
        
        ticker_items = "  •  ".join(self.data)
        ticker_text = f" {ticker_items}  •  {ticker_items} "
        
        # Simple scroll
        win_size = self.size.width or 80
        display_text = ticker_text[self._offset : self._offset + win_size]
        if len(display_text) < win_size:
             display_text += ticker_text[:win_size - len(display_text)]
        
        text = Text(display_text, style=f"bold {UI_CYAN}")
        self.update(text)
        self._offset = (self._offset + 1) % (len(ticker_text) // 2)

class StatusBar(Static):
    status = reactive("READY")

    def render(self) -> Text:
        text = Text("STATUS: ", style=f"bold {DIM_TEXT}")
        text.append(self.status, style=UI_CYAN)
        return text

class PlotextChart(Static):
    """Advanced ASCII chart using plotext."""
    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label
        self.values = []
        self.dates = []

    def update_chart(self, series: List[dict]) -> None:
        self.values = [p["price"] for p in series]
        self.dates = [p["date"] for p in series]
        self.refresh()

    def render(self) -> Text:
        if not self.values:
            return Text(f"{self.label}: NO DATA", style=DIM_TEXT)
        
        plt.clf()
        plt.theme("dark")
        plt.canvas_color("black")
        plt.axes_color("black")
        plt.ticks_color("white")
        plt.plot(self.values, marker="dot", color="cyan")
        plt.title(f"{self.label} Historical")
        
        # Ensure we have valid size
        width = self.size.width or 40
        height = self.size.height or 10
        plt.plotsize(width, height)
        
        return Text.from_ansi(plt.build())

class NewsPanel(Static):
    """News ticker panel."""
    def update_news(self, news: List[dict]) -> None:
        lines = [Text("TOP HEADLINES", style=f"bold {HEADER_TEXT}")]
        for item in news:
            line = Text(f"{item['time']} ", style=DIM_TEXT)
            line.append(item["headline"], style="white")
            line.append(f" [{item['source']}]", style=UI_CYAN)
            lines.append(line)
        self.update(Text("\n").join(lines))

class StocksTable(DataTable):
    def on_mount(self) -> None:
        self.add_column("TICKER", width=12)
        self.add_column("NAME", width=25)
        self.add_column("PRICE", width=12)
        self.add_column("CHANGE%", width=10)
        self.cursor_type = "row"

class TerminalApp(App):
    CSS = f"""
    Screen {{
        background: {BG};
        color: #e5e7eb;
    }}

    CommandBar {{
        background: #1a1a1a;
        border: tall {UI_CYAN};
        color: {HEADER_TEXT};
        margin: 0 1;
        height: 3;
    }}

    .panel {{
        border: solid #333;
        padding: 0 1;
    }}

    .title {{
        color: {HEADER_TEXT};
        text-style: bold;
        background: #1a1a1a;
        padding: 0 1;
    }}

    DataTable {{
        background: {BG};
        border: solid #222;
        color: white;
    }}

    DataTable > .datatable--cursor {{
        background: {UI_CYAN};
        color: black;
    }}

    LiveTicker {{
        background: #050505;
        color: {UI_CYAN};
        height: 1;
        dock: bottom;
    }}

    PlotextChart {{
        height: 15;
        border: solid #222;
    }}
    """

    BINDINGS = [
        ("/", "focus_command", "Cmd"),
        ("1", "switch_tab('market')", "Market"),
        ("2", "switch_tab('startups')", "S-Signals"),
        ("3", "switch_tab('insights')", "AI-I"),
        ("q", "quit", "Quit"),
    ]

    command_bar = CommandBar()
    ticker = LiveTicker()
    stocks_table = StocksTable()
    chart = PlotextChart("Price")
    news_panel = NewsPanel()
    status_bar = StatusBar()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True, id="app_header")
        yield self.command_bar
        with TabbedContent(id="main_tabs"):
            with TabPane("Market Overview", id="market"):
                with Horizontal():
                    with Vertical(id="market_list", classes="panel"):
                        yield Label("EQUITIES", classes="title")
                        yield self.stocks_table
                    with Vertical(id="market_detail", classes="panel"):
                        yield Label("SECURITY DETAIL & CHART", classes="title")
                        yield self.chart
                        yield self.news_panel
            with TabPane("Startup Signals", id="startups"):
                yield Static("Startup intelligence module loading...", classes="panel")
            with TabPane("AI Insights", id="insights"):
                yield Static("AI terminal engaged. Awaiting query...", classes="panel")
        yield self.ticker
        yield Footer()

    async def on_mount(self) -> None:
        self.load_data_task = asyncio.create_task(self.refresh_all())

    async def refresh_all(self) -> None:
        while True:
            self.status_bar.status = "SYNCING"
            await asyncio.gather(
                self.load_stocks(),
                self.load_news(),
                self.load_market_ticker()
            )
            self.status_bar.status = "READY"
            await asyncio.sleep(30)

    async def load_stocks(self) -> None:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{API_BASE}/api/stocks")
                response.raise_for_status()
                stocks = response.json()
            
            self.stocks_table.clear()
            for s in stocks:
                change = s["daily_change_pct"]
                color = POSITIVE if change >= 0 else NEGATIVE
                self.stocks_table.add_row(
                    s["ticker"],
                    s["name"],
                    f"{s['price']:,.2f}",
                    Text(f"{change:+.2f}%", style=color),
                    key=s["ticker"]
                )
            if stocks:
                await self.load_stock_detail(stocks[0]["ticker"])
        except Exception as e:
            self.notify(f"Stocks Error: {e}", severity="error")

    async def load_news(self) -> None:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{API_BASE}/api/news")
                response.raise_for_status()
                news = response.json()
            self.news_panel.update_news(news)
        except:
            pass

    async def load_market_ticker(self) -> None:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp1 = await client.get(f"{API_BASE}/api/stocks/overview")
                overview = resp1.json()
            
            ticker_items = []
            for idx in overview["indices"]:
                # color = "green" if idx["change_pct"] >= 0 else "red"
                ticker_items.append(f"{idx['name']} {idx['value']:,.2f} ({idx['change_pct']:+.2f}%)")
            self.ticker.data = ticker_items
        except:
            pass

    @on(DataTable.RowHighlighted)
    async def handle_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        ticker = str(event.row_key.value)
        await self.load_stock_detail(ticker)

    async def load_stock_detail(self, ticker: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{API_BASE}/api/stocks/{ticker}")
                response.raise_for_status()
                stock = response.json()
            
            series = stock["series"].get("6M", [])
            self.chart.label = f"{ticker}"
            self.chart.update_chart(series)
        except:
            pass

    def action_focus_command(self) -> None:
        self.command_bar.focus()

    @on(Input.Submitted, "CommandBar")
    def handle_command(self, event: Input.Submitted) -> None:
        cmd = event.value.strip().upper()
        self.command_bar.value = ""
        
        if cmd.startswith("GO "):
            target = cmd[3:].lower()
            if "market" in target: self.action_switch_tab("market")
            elif "startups" in target: self.action_switch_tab("startups")
            elif "insights" in target: self.action_switch_tab("insights")
        elif cmd == "QUIT":
            self.exit()
        else:
            # Try to find stock
            self.notify(f"Executing: {cmd}", title="Terminal")

    def action_switch_tab(self, tab_id: str) -> None:
        self.query_one("#main_tabs", TabbedContent).active = tab_id

if __name__ == "__main__":
    TerminalApp().run()
