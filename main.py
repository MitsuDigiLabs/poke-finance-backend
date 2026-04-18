from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import httpx
import os
from dotenv import load_dotenv
from datetime import datetime

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
    async with httpx.AsyncClient(timeout=15.0) as client:
        indices = []

        try:
            # S&P 500 (using SPY)
            resp = await client.get(f"https://api.polygon.io/v2/aggs/ticker/SPY/prev?adjusted=true&apiKey={POLYGON_API_KEY}")
            data = resp.json()
            if data.get("results"):
                prev = data["results"][0]
                indices.append({
                    "name": "S&P 500",
                    "value": round(prev["c"], 2),
                    "change": round(prev["c"] - prev["o"], 2),
                    "changePercent": round(((prev["c"] - prev["o"]) / prev["o"]) * 100, 2)
                })

            # NASDAQ (using QQQ)
            resp = await client.get(f"https://api.polygon.io/v2/aggs/ticker/QQQ/prev?adjusted=true&apiKey={POLYGON_API_KEY}")
            data = resp.json()
            if data.get("results"):
                prev = data["results"][0]
                indices.append({
                    "name": "NASDAQ",
                    "value": round(prev["c"], 2),
                    "change": round(prev["c"] - prev["o"], 2),
                    "changePercent": round(((prev["c"] - prev["o"]) / prev["o"]) * 100, 2)
                })

            # Gold & Silver
            for symbol, name in [("C:XAUUSD", "Gold"), ("C:XAGUSD", "Silver")]:
                resp = await client.get(f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev?adjusted=true&apiKey={POLYGON_API_KEY}")
                data = resp.json()
                if data.get("results"):
                    prev = data["results"][0]
                    indices.append({
                        "name": name,
                        "value": round(prev["c"], 2),
                        "change": round(prev["c"] - prev["o"], 2),
                        "changePercent": round(((prev["c"] - prev["o"]) / prev["o"]) * 100, 2)
                    })

            # Bitcoin via CoinGecko
            resp = await client.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true")
            btc_data = resp.json().get("bitcoin", {})
            indices.append({
                "name": "Bitcoin",
                "value": round(btc_data.get("usd", 0), 2),
                "change": round(btc_data.get("usd_24h_change", 0), 2),
                "changePercent": round(btc_data.get("usd_24h_change", 0), 2)
            })

            # Placeholder Pokémon Indices (we'll improve this in Step 2)
            indices.append({"name": "Pokémon Card Index", "value": 2847.65, "change": 45.12, "changePercent": 1.61})
            indices.append({"name": "TCG Alt Art Index", "value": 1523.40, "change": 32.87, "changePercent": 2.20})

        except Exception as e:
            print("Error fetching market data:", e)
            # Return minimal fallback
            indices = [
                {"name": "S&P 500", "value": 5248.32, "change": 28.45, "changePercent": 0.54},
                {"name": "NASDAQ", "value": 16428.82, "change": -52.31, "changePercent": -0.32},
            ]

        return indices