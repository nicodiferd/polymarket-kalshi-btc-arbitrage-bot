"""
Async Data Fetcher - Parallel API calls for low-latency data retrieval

This module replaces sequential API calls with parallel async requests,
reducing total fetch time from ~1.5-2s to ~300-400ms.

Split VPN Routing:
- Polymarket requests → Through VPN proxy (geo-restricted)
- Kalshi requests → Direct (not geo-restricted)
- Binance requests → Direct (not geo-restricted)
"""

import asyncio
import aiohttp
import os
import time
import json
import re
import datetime
import pytz
from functools import lru_cache
from typing import Optional, Tuple, Dict, Any

# Try to import aiohttp_socks for proxy support
try:
    from aiohttp_socks import ProxyConnector
    PROXY_AVAILABLE = True
except ImportError:
    PROXY_AVAILABLE = False

# API URLs
POLYMARKET_GAMMA_API = "https://gamma-api.polymarket.com/events"
POLYMARKET_CLOB_API = "https://clob.polymarket.com/book"
KALSHI_API_URL = "https://api.elections.kalshi.com/trade-api/v2/markets"
BINANCE_PRICE_URL = "https://api.binance.us/api/v3/ticker/price"
BINANCE_KLINES_URL = "https://api.binance.us/api/v3/klines"
SYMBOL = "BTCUSDT"

# VPN Proxy configuration (only for Polymarket)
# Set VPN_PROXY_URL to route Polymarket through VPN, e.g., "socks5://vpn:1080"
VPN_PROXY_URL = os.environ.get("VPN_PROXY_URL", "")
# HTTP proxy as fallback (e.g., "http://vpn:8888")
VPN_HTTP_PROXY_URL = os.environ.get("VPN_HTTP_PROXY_URL", "")

# Cache for hourly metadata (token IDs don't change within an hour)
_metadata_cache: Dict[str, Any] = {}
_cache_timestamp: Optional[datetime.datetime] = None


def get_proxy_connector() -> Optional[Any]:
    """Get a proxy connector for VPN routing (Polymarket only)"""
    # Try SOCKS5 first
    if VPN_PROXY_URL and PROXY_AVAILABLE:
        try:
            connector = ProxyConnector.from_url(VPN_PROXY_URL)
            print(f"[Proxy] Using SOCKS5 proxy: {VPN_PROXY_URL}")
            return connector
        except Exception as e:
            print(f"[Warning] SOCKS5 proxy failed: {e}")

    # Try HTTP proxy as fallback
    if VPN_HTTP_PROXY_URL and PROXY_AVAILABLE:
        try:
            connector = ProxyConnector.from_url(VPN_HTTP_PROXY_URL)
            print(f"[Proxy] Using HTTP proxy: {VPN_HTTP_PROXY_URL}")
            return connector
        except Exception as e:
            print(f"[Warning] HTTP proxy failed: {e}")

    if VPN_PROXY_URL or VPN_HTTP_PROXY_URL:
        print("[Warning] No proxy available - Polymarket may be geo-blocked")

    return None


def get_cache_key() -> str:
    """Get cache key for current hour"""
    now = datetime.datetime.now(pytz.utc)
    return now.strftime("%Y-%m-%d-%H")


def is_cache_valid() -> bool:
    """Check if cache is still valid for current hour"""
    global _cache_timestamp
    if _cache_timestamp is None:
        return False
    now = datetime.datetime.now(pytz.utc)
    return now.hour == _cache_timestamp.hour and now.date() == _cache_timestamp.date()


async def fetch_json(session: aiohttp.ClientSession, url: str, params: dict = None) -> Tuple[Any, Optional[str]]:
    """Generic async JSON fetcher with error handling"""
    try:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
            response.raise_for_status()
            return await response.json(), None
    except asyncio.TimeoutError:
        return None, f"Timeout fetching {url}"
    except aiohttp.ClientError as e:
        return None, f"HTTP error fetching {url}: {str(e)}"
    except Exception as e:
        return None, f"Error fetching {url}: {str(e)}"


async def fetch_binance_prices(session: aiohttp.ClientSession, target_time_utc: datetime.datetime) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """Fetch both current price and open price from Binance in parallel"""

    # Current price request
    current_task = fetch_json(session, BINANCE_PRICE_URL, {"symbol": SYMBOL})

    # Kline (open price) request
    timestamp_ms = int(target_time_utc.timestamp() * 1000)
    kline_params = {
        "symbol": SYMBOL,
        "interval": "1h",
        "startTime": timestamp_ms,
        "limit": 1
    }
    kline_task = fetch_json(session, BINANCE_KLINES_URL, kline_params)

    # Execute both in parallel
    current_result, kline_result = await asyncio.gather(current_task, kline_task)

    current_data, current_err = current_result
    kline_data, kline_err = kline_result

    current_price = None
    open_price = None
    error = None

    if current_err:
        error = current_err
    elif current_data:
        current_price = float(current_data.get("price", 0))

    if kline_err:
        error = error or kline_err
    elif kline_data and len(kline_data) > 0:
        open_price = float(kline_data[0][1])  # Open price is index 1

    return current_price, open_price, error


async def fetch_polymarket_metadata(session: aiohttp.ClientSession, slug: str) -> Tuple[Optional[Dict], Optional[str]]:
    """Fetch Polymarket event metadata (cached per hour)"""
    global _metadata_cache, _cache_timestamp

    cache_key = get_cache_key()

    # Check cache first
    if cache_key in _metadata_cache and is_cache_valid():
        return _metadata_cache[cache_key], None

    # Fetch fresh metadata
    data, err = await fetch_json(session, POLYMARKET_GAMMA_API, {"slug": slug})

    if err:
        return None, f"Polymarket metadata error: {err}"

    if not data:
        return None, "Polymarket event not found"

    event = data[0]
    markets = event.get("markets", [])
    if not markets:
        return None, "No markets in Polymarket event"

    market = markets[0]

    # Parse token IDs safely (no eval!)
    clob_token_ids_raw = market.get("clobTokenIds", "[]")
    outcomes_raw = market.get("outcomes", "[]")

    if isinstance(clob_token_ids_raw, str):
        clob_token_ids = json.loads(clob_token_ids_raw)
    else:
        clob_token_ids = clob_token_ids_raw

    if isinstance(outcomes_raw, str):
        outcomes = json.loads(outcomes_raw)
    else:
        outcomes = outcomes_raw

    if len(clob_token_ids) != 2:
        return None, f"Unexpected token count: {len(clob_token_ids)}"

    metadata = {
        "token_ids": dict(zip(outcomes, clob_token_ids)),
        "outcomes": outcomes,
        "condition_id": market.get("conditionId"),
    }

    # Cache the metadata
    _metadata_cache[cache_key] = metadata
    _cache_timestamp = datetime.datetime.now(pytz.utc)

    return metadata, None


async def fetch_clob_price(session: aiohttp.ClientSession, token_id: str) -> Optional[float]:
    """Fetch best ask price from Polymarket CLOB"""
    data, err = await fetch_json(session, POLYMARKET_CLOB_API, {"token_id": token_id})

    if err or not data:
        return None

    asks = data.get("asks", [])
    if asks:
        return min(float(a["price"]) for a in asks)
    return None


async def fetch_polymarket_prices(session: aiohttp.ClientSession, metadata: Dict) -> Tuple[Dict[str, float], Optional[str]]:
    """Fetch Polymarket prices for all outcomes in parallel"""
    token_ids = metadata["token_ids"]

    # Create tasks for all token prices
    tasks = {
        outcome: fetch_clob_price(session, token_id)
        for outcome, token_id in token_ids.items()
    }

    # Execute all in parallel
    results = await asyncio.gather(*tasks.values())

    prices = {}
    for outcome, price in zip(tasks.keys(), results):
        prices[outcome] = price if price is not None else 0.0

    return prices, None


async def fetch_kalshi_markets(session: aiohttp.ClientSession, event_ticker: str) -> Tuple[Optional[list], Optional[str]]:
    """Fetch Kalshi markets for event"""
    data, err = await fetch_json(session, KALSHI_API_URL, {"limit": 100, "event_ticker": event_ticker})

    if err:
        return None, f"Kalshi error: {err}"

    markets = data.get("markets", [])

    # Parse and structure market data
    market_data = []
    for m in markets:
        subtitle = m.get("subtitle", "")
        match = re.search(r'\$([\d,]+)', subtitle)
        if match:
            strike = float(match.group(1).replace(',', ''))
            market_data.append({
                "strike": strike,
                "yes_bid": m.get("yes_bid", 0),
                "yes_ask": m.get("yes_ask", 0),
                "no_bid": m.get("no_bid", 0),
                "no_ask": m.get("no_ask", 0),
                "subtitle": subtitle,
                "ticker": m.get("ticker"),  # Include actual ticker for trading!
            })

    market_data.sort(key=lambda x: x["strike"])
    return market_data, None


async def fetch_all_data_async(polymarket_slug: str, kalshi_event_ticker: str, target_time_utc: datetime.datetime) -> Dict:
    """
    Fetch all market data in parallel with SPLIT VPN ROUTING.

    - Polymarket requests → Through VPN proxy (if VPN_PROXY_URL is set)
    - Kalshi/Binance requests → Direct (faster, no geo-restriction)

    This is the main entry point that replaces sequential fetching.
    Expected latency: ~200-300ms (down from 1.5-2s)
    """
    start_time = time.time()
    timing = {}
    routing_info = {"polymarket": "direct", "kalshi": "direct", "binance": "direct"}

    # Create sessions - one for VPN (Polymarket), one for direct (Kalshi/Binance)
    proxy_connector = get_proxy_connector()

    # Direct session for Kalshi and Binance (no VPN needed)
    direct_session = aiohttp.ClientSession()

    # VPN session for Polymarket (geo-restricted)
    if proxy_connector:
        vpn_session = aiohttp.ClientSession(connector=proxy_connector)
        routing_info["polymarket"] = f"vpn ({VPN_PROXY_URL})"
    else:
        # Fallback to direct if no proxy configured
        vpn_session = direct_session
        if VPN_PROXY_URL:
            routing_info["polymarket"] = "direct (proxy unavailable)"

    try:
        # Phase 1: Fetch all data in parallel with appropriate routing
        phase1_start = time.time()

        # Polymarket through VPN
        metadata_task = fetch_polymarket_metadata(vpn_session, polymarket_slug)

        # Kalshi and Binance direct (faster!)
        binance_task = fetch_binance_prices(direct_session, target_time_utc)
        kalshi_task = fetch_kalshi_markets(direct_session, kalshi_event_ticker)

        metadata_result, binance_result, kalshi_result = await asyncio.gather(
            metadata_task, binance_task, kalshi_task
        )

        timing["phase1_ms"] = round((time.time() - phase1_start) * 1000, 2)

        metadata, meta_err = metadata_result
        current_price, open_price, binance_err = binance_result
        kalshi_markets, kalshi_err = kalshi_result

        errors = []
        if meta_err:
            errors.append(meta_err)
        if binance_err:
            errors.append(binance_err)
        if kalshi_err:
            errors.append(kalshi_err)

        # Phase 2: Fetch Polymarket prices through VPN (needs metadata first)
        poly_prices = {}
        if metadata and not meta_err:
            phase2_start = time.time()
            poly_prices, price_err = await fetch_polymarket_prices(vpn_session, metadata)
            timing["phase2_ms"] = round((time.time() - phase2_start) * 1000, 2)
            if price_err:
                errors.append(price_err)

        timing["total_ms"] = round((time.time() - start_time) * 1000, 2)

        return {
            "polymarket": {
                "slug": polymarket_slug,
                "price_to_beat": open_price,
                "current_price": current_price,
                "prices": poly_prices,
                "target_time_utc": target_time_utc,
                "token_ids": metadata.get("token_ids") if metadata else None,
            },
            "kalshi": {
                "event_ticker": kalshi_event_ticker,
                "current_price": current_price,
                "markets": kalshi_markets or [],
            },
            "errors": errors,
            "timing": timing,
            "routing": routing_info,
        }

    finally:
        # Clean up sessions
        await direct_session.close()
        if vpn_session is not direct_session:
            await vpn_session.close()


def fetch_all_data_sync(polymarket_slug: str, kalshi_event_ticker: str, target_time_utc: datetime.datetime) -> Dict:
    """
    Synchronous wrapper for fetch_all_data_async.

    Use this in non-async contexts (like FastAPI sync endpoints).
    """
    return asyncio.run(fetch_all_data_async(polymarket_slug, kalshi_event_ticker, target_time_utc))


# For testing
if __name__ == "__main__":
    from get_current_markets import get_current_market_urls

    market_info = get_current_market_urls()
    poly_slug = market_info["polymarket"].split("/")[-1]
    kalshi_ticker = market_info["kalshi"].split("/")[-1].upper()
    target_time = market_info["target_time_utc"]

    print(f"Fetching data for:")
    print(f"  Polymarket: {poly_slug}")
    print(f"  Kalshi: {kalshi_ticker}")
    print(f"  Target time: {target_time}")
    print()

    result = fetch_all_data_sync(poly_slug, kalshi_ticker, target_time)

    print(f"Timing: {result['timing']}")
    print(f"Errors: {result['errors']}")
    print()
    print(f"Polymarket price_to_beat: ${result['polymarket']['price_to_beat']:,.2f}")
    print(f"Polymarket prices: {result['polymarket']['prices']}")
    print(f"Kalshi markets: {len(result['kalshi']['markets'])} found")
