"""
PokéFinance FastAPI Backend
Deploy to Railway for a permanent public URL.
"""

import os
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="PokéFinance API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "https://*.lovable.app", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "")

# ---------------------------------------------------------------------------
# Market Indices
# ---------------------------------------------------------------------------

@app.get("/api/market-indices")
async def market_indices():
    """Fetch S&P 500, NASDAQ, DOW from Polygon.io"""
    tickers = {
        "S&P 500": "I:SPX",
        "NASDAQ": "I:COMP",
        "DOW": "I:DJI",
    }
    results = []
    async with httpx.AsyncClient(timeout=15) as client:
        for name, ticker in tickers.items():
            try:
                url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev?adjusted=true&apiKey={POLYGON_API_KEY}"
                resp = await client.get(url)
                data = resp.json()
                if data.get("resultsCount", 0) > 0:
                    r = data["results"][0]
                    close = r["c"]
                    open_price = r["o"]
                    change = round(close - open_price, 2)
                    change_pct = round((change / open_price) * 100, 2) if open_price else 0
                    results.append({
                        "name": name,
                        "value": close,
                        "change": change,
                        "changePercent": change_pct,
                    })
                else:
                    results.append({"name": name, "value": 0, "change": 0, "changePercent": 0})
            except Exception:
                results.append({"name": name, "value": 0, "change": 0, "changePercent": 0})
    return results


# ---------------------------------------------------------------------------
# Portfolio Summary (placeholder)
# ---------------------------------------------------------------------------

@app.get("/api/portfolio-summary")
async def portfolio_summary():
    """Placeholder portfolio summary endpoint."""
    return {
        "totalValue": 0,
        "allocation": {"pokemon": 0, "stocks": 0, "cryptocurrency": 0},
        "holdings": {"pokemon": [], "stocks": [], "cryptocurrency": []},
    }


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {"status": "ok"}
