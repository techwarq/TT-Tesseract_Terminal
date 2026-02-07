from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import List

import httpx
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


class StatusBar(Static):
    status = reactive("Idle")

    def render(self) -> Text:
        text = Text("STATUS: ", style="bold #94a3b8")
        text.append(self.status, style="#38bdf8")
        return text


class MarketOverviewPanel(Static):
    def __init__(self) -> None:
        super().__init__()
        self.loading = True
        self.overview: MarketOverview | None = None

    def render(self) -> Text:
        if self.loading:
            return Text("Loading market overview...", style="#94a3b8")
        if not self.overview:
            return Text("No market overview data.", style="#ef4444")

        lines: List[Text] = []
        header = Text(f"Market Overview (as of {self.overview.as_of})", style="bold #e5e7eb")
        lines.append(header)
        for index in self.overview.indices:
            change_color = "#22c55e" if index.change_pct >= 0 else "#ef4444"
            line = Text(f"{index.name}: {index.value:,.2f} ")
            line.append(f"({index.change_pct:+.2f}%)", style=change_color)
            lines.append(line)
        lines.append(Text(f"Advance/Decline: {self.overview.advances} / {self.overview.declines}", style="#94a3b8"))
        lines.append(Text("Sector Heatmap:", style="bold #e5e7eb"))

        for sector in self.overview.sectors:
            change = sector["change_pct"]
            color = "#22c55e" if change >= 0 else "#ef4444"
            lines.append(Text(f"- {sector['sector']}: {change:+.2f}%", style=color))

        return Text("\n").join(lines)


class Sparkline(Static):
    def __init__(self, values: List[float], label: str) -> None:
        super().__init__()
        self.values = values
        self.label = label

    def set_values(self, values: List[float]) -> None:
        self.values = values
        self.refresh()

    def render(self) -> Text:
        if not self.values:
            return Text(f"{self.label}: (no data)", style="#94a3b8")
        blocks = " ▂▃▄▅▆▇█"
        min_val = min(self.values)
        max_val = max(self.values)
        span = max_val - min_val if max_val != min_val else 1
        scaled = [int((value - min_val) / span * (len(blocks) - 1)) for value in self.values]
        line = "".join(blocks[idx] for idx in scaled)
        
        text = Text(f"{self.label}: ", style="#94a3b8")
        text.append(line, style="#38bdf8")
        text.append(f" [₹{min_val:,.0f} - ₹{max_val:,.0f}]", style="#64748b")
        return text


class StocksTable(DataTable):
    def on_mount(self) -> None:
        self.add_column("Ticker", width=10)
        self.add_column("Name", width=28)
        self.add_column("Price", width=12)
        self.add_column("Change", width=10)
        self.add_column("Trend", width=8)
        self.cursor_type = "row"


class StartupsTable(DataTable):
    def on_mount(self) -> None:
        self.add_column("Name", width=20)
        self.add_column("Sector", width=18)
        self.add_column("Country", width=12)
        self.add_column("Status", width=12)
        self.add_column("Description", width=40)
        self.cursor_type = "row"


class StockDetailView(Vertical):
    def __init__(self) -> None:
        super().__init__()
        self.text = Static()
        self.sparkline = Sparkline([], "Price Trend")
        self.current_stock: dict | None = None
        self.timeframe = "6M"

    def compose(self) -> ComposeResult:
        with Horizontal(id="timeframe_controls"):
            yield Label("Timeframe: ", classes="label")
            yield Static(" [1M] ", id="tf_1m", classes="tf_btn")
            yield Static(" [6M] ", id="tf_6m", classes="tf_btn active")
            yield Static(" [1Y] ", id="tf_1y", classes="tf_btn")
        yield self.text
        yield self.sparkline
        yield Static(" [Ask AI Insight] ", id="ask_ai_stock", classes="action_btn")

    def update_stock(self, stock: dict, timeframe: str = "6M") -> None:
        self.current_stock = stock
        self.timeframe = timeframe
        
        tf_map = {"1M": "one_month", "6M": "six_month", "1Y": "one_year"}
        series_key = tf_map.get(timeframe, "six_month")
        series = stock["series"].get(series_key, [])
        values = [point["price"] for point in series]
        
        details = Text("\n").join(
            [
                Text(f"{stock['name']} ({stock['ticker']})", style="bold #e5e7eb"),
                Text(f"Price: ₹ {stock['price']:.2f}", style="#94a3b8"),
                Text(f"Market Cap: {stock['market_cap']}", style="#94a3b8"),
                Text(f"PE: {stock['pe']:.1f}", style="#94a3b8"),
                Text(f"Trend: {stock['trend']}", style="#94a3b8"),
            ]
        )
        self.text.update(details)
        self.sparkline.label = f"{timeframe} Price Trend"
        self.sparkline.set_values(values)

    @on(events.Click, ".tf_btn")
    def handle_timeframe_click(self, event: events.Click) -> None:
        if not self.current_stock:
            return
        
        btn_id = event.static.id
        new_tf = {"tf_1m": "1M", "tf_6m": "6M", "tf_1y": "1Y"}.get(btn_id)
        if new_tf:
            # Update visual states
            for btn in self.query(".tf_btn"):
                btn.remove_class("active")
            event.static.add_class("active")
            self.update_stock(self.current_stock, new_tf)


class StartupDetailView(Vertical):
    def __init__(self) -> None:
        super().__init__()
        self.text = Static()
        self.hiring = Sparkline([], "Hiring")
        self.buzz = Sparkline([], "Buzz")

    def compose(self) -> ComposeResult:
        yield self.text
        yield self.hiring
        yield self.buzz
        yield Static(" [Ask AI Insight] ", id="ask_ai_startup", classes="action_btn")

    def update_startup(self, startup: dict) -> None:
        momentum = startup.get("momentum", [])
        hiring = [point["hiring"] for point in momentum]
        buzz = [point["buzz"] for point in momentum]

        body = Text("\n").join(
            [
                Text(f"{startup['name']}", style="bold #e5e7eb"),
                Text(f"Sector: {startup['sector']}", style="#94a3b8"),
                Text(f"Country: {startup['country']}", style="#94a3b8"),
                Text(f"Status: {startup['status']}", style="#94a3b8"),
                Text(startup["overview"], style="#94a3b8"),
            ]
        )
        self.text.update(body)
        self.hiring.set_values(hiring)
        self.buzz.set_values(buzz)


class InsightPane(Vertical):
    def __init__(self) -> None:
        super().__init__()
        self.log = RichLog()
        self.input = Input(placeholder="Ask AI for insights (e.g. 'How is RELIANCE doing?')")

    def compose(self) -> ComposeResult:
        yield Label("Market Intelligence Assistant", classes="title")
        yield self.log
        yield self.input

    def on_mount(self) -> None:
        self.log.write(Text("AI Assistant connected. How can I help you today?", style="#38bdf8"))

    @on(Input.Submitted)
    def handle_submit(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if not query:
            return
        
        self.log.write(Text(f"\n> {query}", style="bold #e5e7eb"))
        self.input.value = ""
        
        response = self.generate_response(query)
        self.log.write(Text(response, style="#38bd8f"))

    def generate_response(self, query: str) -> str:
        q = query.upper()
        if "RELIANCE" in q:
            return "Reliance shows strong technical support at 2800. Momentum indicators suggest a continued 'Up' trend centered around refining margins."
        elif "TCS" in q:
            return "TCS is currently in a consolidation phase. Watch for resistance at 4000. Institutional interest remains 'Flat' but stable."
        elif "AIRSHIP" in q:
            return "Airship ML has seen a 20% increase in buzz following their Series A. Hiring is peaking, indicating rapid execution phase."
        elif "VOLTGRID" in q:
            return "Voltgrid is a 'Watch' candidate. Their recent MOU suggests enterprise validation, though hiring is modest."
        else:
            return "I don't have specific insights on that query yet. Try asking about tracked stocks like RELIANCE, TCS, or startups like Airship ML."

    def ask_about(self, topic: str) -> None:
        self.log.write(Text(f"\n[AI Query]: Analyzing {topic}...", style="italic #94a3b8"))
        response = self.generate_response(topic)
        self.log.write(Text(response, style="#38bd8f"))


class TerminalApp(App):
    CSS = """
    Screen {
        background: #0b0f14;
        color: #e5e7eb;
    }

    .panel {
        border: solid #1f2937;
        padding: 1 2;
        margin: 1 0;
    }

    .title {
        color: #94a3b8;
        text-style: bold;
    }

    DataTable {
        background: #121826;
        border: solid #1f2937;
        height: 16;
    }

    .tf_btn {
        background: #1f2937;
        color: #94a3b8;
        padding: 0 1;
        margin-right: 1;
        border: outset #374151;
    }

    .tf_btn.active {
        background: #38bdf8;
        color: #0b0f14;
        text-style: bold;
    }

    .action_btn {
        background: #1e293b;
        color: #38bdf8;
        padding: 0 1;
        margin-top: 1;
        border: solid #334155;
        width: auto;
    }

    .action_btn:hover {
        background: #334155;
    }

    #timeframe_controls {
        margin-bottom: 1;
        height: auto;
    }

    RichLog {
        background: #121826;
        border: solid #1f2937;
        height: 1fr;
    }

    Input {
        background: #1f2937;
        border: solid #374151;
        margin-top: 1;
    }
    """

    BINDINGS = [
        ("1", "switch_tab('stocks')", "Stocks"),
        ("2", "switch_tab('startups')", "Startups"),
        ("3", "switch_tab('insights')", "AI Insights"),
        ("q", "quit", "Quit"),
    ]

    overview_panel = MarketOverviewPanel()
    status_bar = StatusBar()
    stocks_table = StocksTable()
    startups_table = StartupsTable()

    stock_detail = StockDetailView()
    startup_detail = StartupDetailView()
    insight_pane = InsightPane()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(id="main_tabs"):
            with TabPane("Stocks", id="stocks"):
                with Container():
                    yield Label("Stocks :: Market Overview", classes="title")
                    yield self.overview_panel
                with Container(classes="panel"):
                    yield Label("Tracked Stocks", classes="title")
                    yield self.stocks_table
                    yield self.stock_detail
            with TabPane("Startups", id="startups"):
                with Container(classes="panel"):
                    yield Label("Startup Signals", classes="title")
                    yield self.startups_table
                    yield self.startup_detail
            with TabPane("AI Insights", id="insights"):
                yield self.insight_pane
        with Horizontal(classes="panel"):
            yield self.status_bar
        yield Footer()

    async def on_mount(self) -> None:
        await self.load_data()

    async def load_data(self) -> None:
        self.status_bar.status = "Fetching data"
        await asyncio.gather(self.load_market_overview(), self.load_stocks(), self.load_startups())
        self.status_bar.status = "Ready"

    async def load_market_overview(self) -> None:
        self.overview_panel.loading = True
        self.overview_panel.refresh()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{API_BASE}/api/stocks/overview")
                response.raise_for_status()
                data = response.json()
                overview = MarketOverview(
                    as_of=data["as_of"],
                    indices=[IndexSnapshot(**item) for item in data["indices"]],
                    advances=data["advance_decline"]["advances"],
                    declines=data["advance_decline"]["declines"],
                    sectors=data["sectors"],
                )
                self.overview_panel.overview = overview
        except Exception as exc:
            self.overview_panel.overview = None
            self.status_bar.status = f"Overview error: {exc}"
        finally:
            self.overview_panel.loading = False
            self.overview_panel.refresh()

    async def load_stocks(self) -> None:
        self.stocks_table.clear()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{API_BASE}/api/stocks")
                response.raise_for_status()
                data = response.json()

            for item in data:
                change = item["daily_change_pct"]
                change_text = Text(f"{change:+.2f}%", style="#22c55e" if change >= 0 else "#ef4444")
                self.stocks_table.add_row(
                    item["ticker"],
                    item["name"],
                    f"₹ {item['price']:.2f}",
                    change_text,
                    item["trend"],
                    key=item["ticker"],
                )
        except Exception as exc:
            self.status_bar.status = f"Stocks error: {exc}"

    async def load_startups(self) -> None:
        self.startups_table.clear()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{API_BASE}/api/startups")
                response.raise_for_status()
                data = response.json()

            for item in data:
                status_color = {
                    "Ignore": "#94a3b8",
                    "Watch": "#f59e0b",
                    "Interesting": "#22c55e",
                }.get(item["status"], "#94a3b8")
                status_text = Text(item["status"], style=status_color)
                self.startups_table.add_row(
                    item["name"],
                    item["sector"],
                    item["country"],
                    status_text,
                    item["description"],
                    key=item["id"],
                )
        except Exception as exc:
            self.status_bar.status = f"Startups error: {exc}"

    @on(DataTable.RowHighlighted)
    async def show_stock_detail(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table is not self.stocks_table:
            return
        ticker = str(event.row_key.value)
        await self.render_stock_detail(ticker)

    async def render_stock_detail(self, ticker: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{API_BASE}/api/stocks/{ticker}")
                response.raise_for_status()
                stock = response.json()
        except Exception as exc:
            self.stock_detail.text.update(Text(f"Failed to load {ticker}: {exc}", style="#ef4444"))
            self.stock_detail.sparkline.set_values([])
            return

        self.stock_detail.update_stock(stock)

    @on(DataTable.RowHighlighted)
    async def show_startup_detail(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table is not self.startups_table:
            return
        startup_id = str(event.row_key.value)
        await self.render_startup_detail(startup_id)

    async def render_startup_detail(self, startup_id: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{API_BASE}/api/startups/{startup_id}")
                response.raise_for_status()
                startup = response.json()
        except Exception as exc:
            self.startup_detail.text.update(Text(f"Failed to load {startup_id}: {exc}", style="#ef4444"))
            self.startup_detail.hiring.set_values([])
            self.startup_detail.buzz.set_values([])
            return

        self.startup_detail.update_startup(startup)

    def action_switch_tab(self, tab_id: str) -> None:
        tabs = self.query_one("#main_tabs", TabbedContent)
        tabs.active = tab_id

    @on(events.Click, "#ask_ai_stock")
    def handle_ask_ai_stock(self) -> None:
        if self.stock_detail.current_stock:
            ticker = self.stock_detail.current_stock["ticker"]
            self.action_switch_tab("insights")
            self.insight_pane.ask_about(ticker)

    @on(events.Click, "#ask_ai_startup")
    def handle_ask_ai_startup(self) -> None:
        # In this mock, we'll just use the name if available
        # You'd typically get this from the state
        name = "this startup" 
        # For better UX, we can try to find the highlighted row
        try:
            row_index = self.startups_table.cursor_row
            name = self.startups_table.get_row_at(row_index)[0]
        except:
            pass
        self.action_switch_tab("insights")
        self.insight_pane.ask_about(name)


if __name__ == "__main__":
    TerminalApp().run()
