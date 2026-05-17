from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import httpx
import os
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
app.add_middleware(GZipMiddleware, minimum_size=1000)

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

@app.get("/api/market-indices")
async def get_market_indices():
    async with httpx.AsyncClient(timeout=10.0) as client:
        indices = []

        # Helper to fetch from Polygon
        async def fetch_polygon(ticker: str, name: str):
            try:
                url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev?adjusted=true&apiKey={POLYGON_API_KEY}"
                resp = await client.get(url)
                data = resp.json()
                if data.get("results"):
                    r = data["results"][0]
                    close = r.get("c")
                    open_price = r.get("o")
                    if close is not None and open_price is not None:
                        change = close - open_price
                        change_pct = (change / open_price) * 100 if open_price != 0 else 0
                        indices.append({
                            "name": name,
                            "value": round(close, 2),
                            "change": round(change, 2),
                            "changePercent": round(change_pct, 2)
                        })
                        return
            except Exception as e:
                print(f"Error fetching {name}: {e}")
            # Fallback
            indices.append({"name": name, "value": 0, "change": 0, "changePercent": 0})

        # Fetch all indices
        await fetch_polygon("SPY", "S&P 500")
        await fetch_polygon("QQQ", "NASDAQ")
        await fetch_polygon("C:XAUUSD", "Gold")
        await fetch_polygon("C:XAGUSD", "Silver")

        # Bitcoin
        try:
            resp = await client.get(
                "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
            )
            btc = resp.json().get("bitcoin", {})
            indices.append({
                "name": "Bitcoin",
                "value": round(btc.get("usd", 0), 2),
                "change": round(btc.get("usd_24h_change", 0), 2),
                "changePercent": round(btc.get("usd_24h_change", 0), 2)
            })
        except:
            indices.append({"name": "Bitcoin", "value": 0, "change": 0, "changePercent": 0})

        # Pokémon Indices (real placeholders for now)
        indices.append({"name": "Pokémon Card Index", "value": 2847.65, "change": 45.12, "changePercent": 1.61})
        indices.append({"name": "TCG Alt Art Index", "value": 1523.40, "change": 32.87, "changePercent": 2.20})

        return indices


@app.get("/api/market-indices/debug")
async def debug_market_indices():
    """Keep this for future debugging"""
    return {"status": "debug endpoint active - main endpoint should now work"}