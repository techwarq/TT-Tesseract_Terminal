from typing import List, Literal, Optional
from pydantic import BaseModel

Trend = Literal["Up", "Flat", "Down"]
Status = Literal["Ignore", "Watch", "Interesting"]


class IndexSnapshot(BaseModel):
    name: str
    value: float
    change_pct: float


class AdvanceDecline(BaseModel):
    advances: int
    declines: int


class SectorPerformance(BaseModel):
    sector: str
    change_pct: float


class MarketOverview(BaseModel):
    as_of: str
    indices: List[IndexSnapshot]
    advance_decline: AdvanceDecline
    sectors: List[SectorPerformance]


class StockPoint(BaseModel):
    date: str
    price: float


class StockSeries(BaseModel):
    one_month: List[StockPoint]
    six_month: List[StockPoint]
    one_year: List[StockPoint]

    @classmethod
    def from_dict(cls, data: dict) -> "StockSeries":
        return cls(
            one_month=data.get("1M", []),
            six_month=data.get("6M", []),
            one_year=data.get("1Y", []),
        )


class Stock(BaseModel):
    name: str
    ticker: str
    price: float
    market_cap: str
    pe: float
    trend: Trend
    daily_change_pct: float
    series: StockSeries

    @classmethod
    def from_dict(cls, data: dict) -> "Stock":
        return cls(
            name=data["name"],
            ticker=data["ticker"],
            price=data["price"],
            market_cap=data["market_cap"],
            pe=data["pe"],
            trend=data["trend"],
            daily_change_pct=data["daily_change_pct"],
            series=StockSeries.from_dict(data.get("series", {})),
        )


class StartupMomentumPoint(BaseModel):
    month: str
    hiring: int
    buzz: int
    events: Optional[List[str]] = None


class Startup(BaseModel):
    id: str
    name: str
    sector: str
    country: str
    description: str
    status: Status
    overview: str
    momentum: List[StartupMomentumPoint]
    notes: str


class StartupListItem(BaseModel):
    id: str
    name: str
    sector: str
    country: str
    description: str
    status: Status
