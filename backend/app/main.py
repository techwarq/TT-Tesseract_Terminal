from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.data import MARKET_OVERVIEW, STARTUPS, STOCKS, WATCHLIST
from app.models import MarketOverview, Startup, StartupListItem, Stock

app = FastAPI(title="Market Intelligence API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get("/api/stocks/overview", response_model=MarketOverview)
async def get_market_overview():
    return MARKET_OVERVIEW


@app.get("/api/stocks", response_model=list[Stock])
async def list_stocks():
    return [Stock.from_dict(stock) for stock in STOCKS]


@app.get("/api/stocks/{ticker}", response_model=Stock)
async def get_stock(ticker: str):
    for stock in STOCKS:
        if stock["ticker"] == ticker:
            return Stock.from_dict(stock)
    raise HTTPException(status_code=404, detail="Stock not found")


@app.get("/api/stocks/watchlist", response_model=list[str])
async def get_watchlist():
    return WATCHLIST


@app.get("/api/startups", response_model=list[StartupListItem])
async def list_startups():
    return [
        StartupListItem(
            id=item["id"],
            name=item["name"],
            sector=item["sector"],
            country=item["country"],
            description=item["description"],
            status=item["status"],
        )
        for item in STARTUPS
    ]


@app.get("/api/startups/{startup_id}", response_model=Startup)
async def get_startup(startup_id: str):
    for startup in STARTUPS:
        if startup["id"] == startup_id:
            return Startup(**startup)
    raise HTTPException(status_code=404, detail="Startup not found")
