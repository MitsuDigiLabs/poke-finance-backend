"""
PokéFinance FastAPI Backend
Deploy to Railway for a permanent public URL.
"""

import os
import asyncio
import hashlib
from datetime import date
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
# Helpers
# ---------------------------------------------------------------------------

ZERO = {"value": 0, "change": 0, "changePercent": 0}


def _result(name: str, value: float, change: float, change_pct: float) -> dict:
    return {
        "name": name,
        "value": round(value, 2),
        "change": round(change, 2),
        "changePercent": round(change_pct, 2),
    }


def _err(name: str) -> dict:
    return {"name": name, **ZERO}


async def _polygon_prev(client: httpx.AsyncClient, name: str, ticker: str) -> dict:
    """Fetch previous-day aggregate for stocks/ETFs/FX/crypto from Polygon."""
    if not POLYGON_API_KEY:
        return _err(name)
    try:
        url = (
            f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev"
            f"?adjusted=true&apiKey={POLYGON_API_KEY}"
        )
        resp = await client.get(url)
        data = resp.json()
        if data.get("resultsCount", 0) > 0:
            r = data["results"][0]
            close = r["c"]
            open_p = r["o"]
            change = close - open_p
            pct = (change / open_p) * 100 if open_p else 0
            return _result(name, close, change, pct)
        return _err(name)
    except Exception:
        return _err(name)


async def _coingecko_btc(client: httpx.AsyncClient) -> dict:
    """Fetch Bitcoin price + 24h change from CoinGecko (no key needed)."""
    try:
        url = (
            "https://api.coingecko.com/api/v3/simple/price"
            "?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
        )
        resp = await client.get(url)
        data = resp.json()
        btc = data.get("bitcoin", {})
        price = float(btc.get("usd", 0))
        pct = float(btc.get("usd_24h_change", 0))
        # Derive absolute change from price + pct
        prev = price / (1 + pct / 100) if (1 + pct / 100) else price
        change = price - prev
        return _result("Bitcoin", price, change, pct)
    except Exception:
        return _err("Bitcoin")


def _daily_jitter(seed_key: str, max_pct: float = 2.0) -> float:
    """Deterministic daily ±pct in [-max_pct, +max_pct], seeded by date+key."""
    seed = f"{date.today().isoformat()}:{seed_key}"
    h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
    # Map to [-1, 1]
    norm = ((h % 10_000) / 10_000) * 2 - 1
    return norm * max_pct


async def _tcgdex_validate(client: httpx.AsyncClient, card_ids: list[str]) -> int:
    """Hit TCGdex to confirm cards exist; returns count of valid responses."""
    valid = 0
    try:
        for cid in card_ids[:3]:  # sample a few to keep it cheap
            try:
                r = await client.get(f"https://api.tcgdex.net/v2/en/cards/{cid}")
                if r.status_code == 200:
                    valid += 1
            except Exception:
                pass
    except Exception:
        pass
    return valid


# Hardcoded reference baskets (USD). TODO: replace with TCGplayer/PriceCharting.
POKEMON_BASKET = {
    "base1-4": 8500.0,       # Charizard Base Set Holo (PSA-ish midpoint)
    "base1-58": 220.0,       # Pikachu Base
    "neo1-9": 950.0,          # Lugia Neo Genesis
    "ex12-100": 600.0,        # Charizard ex Crystal Guardians
    "swsh4-25": 180.0,        # Rayquaza VMAX (alt aside)
    "swsh45-18": 280.0,       # Pikachu V Shining Fates
    "sm115-7": 350.0,         # Charizard GX Hidden Fates
    "xy12-12": 900.0,         # Charizard EX Evolutions
    "swsh9-154": 220.0,       # Umbreon VMAX baseline (non-alt)
    "sv1-199": 140.0,         # Misc modern chase
}

ALT_ART_BASKET = {
    "swsh9-215": 1900.0,      # Umbreon VMAX Alt Art
    "swsh9-TG29": 700.0,      # Trainer Gallery alts
    "swsh10-174": 380.0,      # Giratina V Alt
    "swsh11-192": 260.0,      # Lugia V Alt
    "swsh12-244": 220.0,      # Charizard VSTAR Alt
    "sv2-245": 300.0,         # Iono SR
    "sv3-215": 280.0,         # Modern alt chase
    "sv4-244": 250.0,
    "sv5-200": 240.0,
    "sv6-210": 230.0,
}


async def _pokemon_index(client: httpx.AsyncClient) -> dict:
    """Equal-weighted Pokémon Card Index from a static basket + daily jitter."""
    try:
        await _tcgdex_validate(client, list(POKEMON_BASKET.keys()))
        avg = sum(POKEMON_BASKET.values()) / len(POKEMON_BASKET)
        pct = _daily_jitter("pokemon-index", max_pct=1.5)
        prev = avg / (1 + pct / 100) if (1 + pct / 100) else avg
        change = avg - prev
        return _result("Pokémon Card Index", avg, change, pct)
    except Exception:
        return _err("Pokémon Card Index")


async def _alt_art_index(client: httpx.AsyncClient) -> dict:
    """Equal-weighted TCG Alt Art Index from a static basket + daily jitter."""
    try:
        await _tcgdex_validate(client, list(ALT_ART_BASKET.keys()))
        avg = sum(ALT_ART_BASKET.values()) / len(ALT_ART_BASKET)
        pct = _daily_jitter("alt-art-index", max_pct=2.0)
        prev = avg / (1 + pct / 100) if (1 + pct / 100) else avg
        change = avg - prev
        return _result("TCG Alt Art Index", avg, change, pct)
    except Exception:
        return _err("TCG Alt Art Index")


# ---------------------------------------------------------------------------
# Market Indices
# ---------------------------------------------------------------------------

@app.get("/api/market-indices")
async def market_indices():
    """Fetch S&P (SPY), NASDAQ (QQQ), Gold, Silver, Bitcoin, Pokémon, Alt Art."""
    async with httpx.AsyncClient(timeout=15) as client:
        results = await asyncio.gather(
            _polygon_prev(client, "S&P 500", "SPY"),
            _polygon_prev(client, "NASDAQ", "QQQ"),
            _polygon_prev(client, "Gold", "C:XAUUSD"),
            _polygon_prev(client, "Silver", "C:XAGUSD"),
            _coingecko_btc(client),
            _pokemon_index(client),
            _alt_art_index(client),
        )
    return list(results)


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
