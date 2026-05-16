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

@app.get("/api/market-indices/debug")
async def debug_market_indices():
    """Detailed debug info to see exactly what is failing"""
    results = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, ticker in [
            ("S&P 500", "SPY"),
            ("NASDAQ", "QQQ"),
            ("Gold", "C:XAUUSD"),
            ("Silver", "C:XAGUSD"),
        ]:
            try:
                url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev?adjusted=true&apiKey={POLYGON_API_KEY}"
                resp = await client.get(url)
                data = resp.json()
                results[name] = {
                    "status": resp.status_code,
                    "success": bool(data.get("results")),
                    "data": data,
                    "url": url
                }
            except Exception as e:
                results[name] = {"error": str(e)}

        # Bitcoin debug
        try:
            resp = await client.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true")
            results["Bitcoin"] = {"status": resp.status_code, "data": resp.json()}
        except Exception as e:
            results["Bitcoin"] = {"error": str(e)}

    return results

# Keep your existing /api/market-indices for the frontend
@app.get("/api/market-indices")
async def get_market_indices():
    # ... (same code as before, or the one I gave you earlier)
    # For now, it will still return 0s until we fix the root cause
    pass  # We'll update this after seeing the debug output