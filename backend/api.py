from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fetch_current_polymarket import fetch_polymarket_data_struct
from fetch_current_kalshi import fetch_kalshi_data_struct
from get_current_markets import get_current_market_urls
from config.settings import settings
from fees import calculate_arbitrage_with_fees, calculate_total_fees
import datetime
import pytz
import logging
import asyncio

# Try to import async fetcher, fall back to sync if not available
try:
    from async_fetcher import fetch_all_data_async
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("arbitrage")

app = FastAPI()

# Hour boundary protection settings
HOUR_BOUNDARY_BUFFER_MINUTES = 2  # Minutes before/after hour to pause trading
SUSPICIOUS_PRICE_THRESHOLD = 0.03  # Prices below 3¢ or above 97¢ are suspicious near boundaries
MAX_DATA_AGE_SECONDS = 5  # Maximum age of data before considering stale
MARKET_SYNC_TOLERANCE_MINUTES = 5  # Tolerance for market sync validation


def is_near_hour_boundary() -> tuple[bool, int]:
    """
    Check if we're near an hour boundary where markets transition.

    Returns:
        tuple: (is_near_boundary, minutes_until_safe)
    """
    now = datetime.datetime.now()
    minutes = now.minute

    # Check if within buffer of hour start (0-2 minutes)
    if minutes < HOUR_BOUNDARY_BUFFER_MINUTES:
        return True, HOUR_BOUNDARY_BUFFER_MINUTES - minutes

    # Check if within buffer of hour end (58-60 minutes)
    if minutes >= (60 - HOUR_BOUNDARY_BUFFER_MINUTES):
        return True, (60 - minutes) + HOUR_BOUNDARY_BUFFER_MINUTES

    return False, 0


def has_suspicious_prices(poly_prices: dict, kalshi_cost: float) -> bool:
    """
    Check if prices look suspicious (near 0 or 1), indicating market transition.

    During hour boundaries:
    - Closing markets have prices near $1.00 (winner) or $0.00 (loser)
    - Opening markets may have stale or extreme prices
    """
    up_price = poly_prices.get('Up', 0.5)
    down_price = poly_prices.get('Down', 0.5)

    # Check for extreme Polymarket prices
    if up_price <= SUSPICIOUS_PRICE_THRESHOLD or up_price >= (1 - SUSPICIOUS_PRICE_THRESHOLD):
        return True
    if down_price <= SUSPICIOUS_PRICE_THRESHOLD or down_price >= (1 - SUSPICIOUS_PRICE_THRESHOLD):
        return True

    # Check for extreme Kalshi prices
    if kalshi_cost <= SUSPICIOUS_PRICE_THRESHOLD or kalshi_cost >= (1 - SUSPICIOUS_PRICE_THRESHOLD):
        return True

    return False


def validate_market_sync(poly_data: dict, kalshi_data: dict) -> tuple[bool, list[str]]:
    """
    Validate that Polymarket and Kalshi data are synchronized and valid.

    Checks:
    1. Both data sources have valid timestamps for the same market hour
    2. Data is fresh (not stale from previous hour)
    3. Markets exist and have valid prices

    Returns:
        tuple: (is_valid, list of warning/error messages)
    """
    issues = []
    is_valid = True

    now = datetime.datetime.now(pytz.utc)
    current_minute = now.minute
    current_second = now.second

    # Check 1: Polymarket has required data
    if not poly_data:
        issues.append("SYNC_ERROR: Polymarket data is missing")
        is_valid = False
        return is_valid, issues

    poly_target_time = poly_data.get('target_time_utc')
    poly_prices = poly_data.get('prices', {})

    # Check 2: Kalshi has required data
    if not kalshi_data:
        issues.append("SYNC_ERROR: Kalshi data is missing")
        is_valid = False
        return is_valid, issues

    kalshi_markets = kalshi_data.get('markets', [])

    # Check 3: Polymarket target time is valid and current
    if poly_target_time:
        expected_target = now.replace(minute=0, second=0, microsecond=0)
        time_diff = abs((poly_target_time - expected_target).total_seconds())

        if time_diff > MARKET_SYNC_TOLERANCE_MINUTES * 60:
            issues.append(f"SYNC_ERROR: Polymarket target time mismatch. Expected {expected_target}, got {poly_target_time}")
            is_valid = False
    else:
        issues.append("SYNC_ERROR: Polymarket target time is missing")
        is_valid = False

    # Check 4: Polymarket prices are valid (not zero or extreme during transition)
    up_price = poly_prices.get('Up', 0.0)
    down_price = poly_prices.get('Down', 0.0)

    if up_price == 0.0 and down_price == 0.0:
        issues.append("SYNC_ERROR: Polymarket prices are both zero - likely stale or market not yet open")
        is_valid = False

    # Sanity check: Up + Down should be close to 1.0 (with some spread)
    price_sum = up_price + down_price
    if price_sum > 0 and (price_sum < 0.85 or price_sum > 1.15):
        issues.append(f"SYNC_WARNING: Polymarket prices sum to {price_sum:.3f} - potential data issue")
        # This is a warning, not necessarily invalid

    # Check 5: Kalshi has markets available
    if not kalshi_markets:
        issues.append("SYNC_ERROR: No Kalshi markets available - possible market transition")
        is_valid = False

    # Check 6: Near hour boundary, apply stricter validation
    if current_minute >= 58 or current_minute <= 2:
        # During transition window, check for signs of stale data

        # If Polymarket has extreme prices near boundary, likely transitioning
        if up_price <= 0.02 or up_price >= 0.98:
            issues.append(f"TRANSITION_BLOCK: Polymarket Up price ({up_price:.3f}) is extreme near hour boundary")
            is_valid = False
        if down_price <= 0.02 or down_price >= 0.98:
            issues.append(f"TRANSITION_BLOCK: Polymarket Down price ({down_price:.3f}) is extreme near hour boundary")
            is_valid = False

        # Check Kalshi for extreme prices
        for km in kalshi_markets:
            yes_ask = km.get('yes_ask', 0) / 100.0
            no_ask = km.get('no_ask', 0) / 100.0
            if yes_ask <= 0.02 or yes_ask >= 0.98 or no_ask <= 0.02 or no_ask >= 0.98:
                issues.append(f"TRANSITION_BLOCK: Kalshi strike ${km['strike']:.0f} has extreme prices near boundary")
                is_valid = False
                break  # One is enough to block

    # Check 7: Validate price_to_beat exists (Binance data)
    price_to_beat = poly_data.get('price_to_beat')
    if price_to_beat is None:
        issues.append("SYNC_ERROR: Binance price_to_beat is missing - kline may not be available yet")
        is_valid = False

    return is_valid, issues


def detect_market_transition_anomaly(poly_data: dict, kalshi_data: dict) -> tuple[bool, str]:
    """
    Detect anomalies that indicate a market transition is causing false arbitrage signals.

    This specifically looks for patterns that occur during hour boundaries:
    - One source updated to new market, other still on old
    - Prices that don't make logical sense together
    - Arbitrage opportunities that are "too good to be true"

    Returns:
        tuple: (is_anomaly_detected, reason)
    """
    now = datetime.datetime.now(pytz.utc)
    current_minute = now.minute

    # Only check near hour boundaries
    if not (current_minute >= 55 or current_minute <= 5):
        return False, ""

    if not poly_data or not kalshi_data:
        return True, "Missing data during transition window"

    poly_prices = poly_data.get('prices', {})
    up_price = poly_prices.get('Up', 0.5)
    down_price = poly_prices.get('Down', 0.5)

    kalshi_markets = kalshi_data.get('markets', [])

    # Anomaly 1: Polymarket prices are at settlement values (0 or 1)
    if up_price <= 0.01 or up_price >= 0.99 or down_price <= 0.01 or down_price >= 0.99:
        logger.warning(f"TRANSITION_ANOMALY: Polymarket prices at settlement values (Up: {up_price}, Down: {down_price})")
        return True, f"Polymarket prices at settlement values during transition (Up: {up_price:.3f}, Down: {down_price:.3f})"

    # Anomaly 2: Kalshi has very few markets or markets with extreme prices
    if kalshi_markets:
        extreme_count = 0
        for km in kalshi_markets:
            yes_ask = km.get('yes_ask', 50) / 100.0
            no_ask = km.get('no_ask', 50) / 100.0
            if yes_ask <= 0.02 or yes_ask >= 0.98 or no_ask <= 0.02 or no_ask >= 0.98:
                extreme_count += 1

        # If more than half have extreme prices, likely transitioning
        if extreme_count > len(kalshi_markets) / 2:
            logger.warning(f"TRANSITION_ANOMALY: {extreme_count}/{len(kalshi_markets)} Kalshi markets have extreme prices")
            return True, f"{extreme_count} of {len(kalshi_markets)} Kalshi markets have extreme prices"

    # Anomaly 3: Price_to_beat doesn't exist yet (new candle not started)
    if poly_data.get('price_to_beat') is None and current_minute <= 2:
        logger.warning("TRANSITION_ANOMALY: Binance kline not available yet for new hour")
        return True, "Binance price data not available for new market hour"

    return False, ""


def log_transition_event(event_type: str, details: dict):
    """
    Log market transition events for debugging and monitoring.
    """
    now = datetime.datetime.now(pytz.utc)
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S UTC")

    log_entry = {
        "timestamp": timestamp,
        "minute": now.minute,
        "second": now.second,
        "event_type": event_type,
        **details
    }

    if event_type == "TRANSITION_BLOCK":
        logger.warning(f"[{timestamp}] BLOCKED TRADE - {details.get('reason', 'Unknown')}")
    elif event_type == "SYNC_ERROR":
        logger.error(f"[{timestamp}] SYNC ERROR - {details.get('issues', [])}")
    elif event_type == "ANOMALY_DETECTED":
        logger.warning(f"[{timestamp}] ANOMALY - {details.get('reason', 'Unknown')}")
    else:
        logger.info(f"[{timestamp}] {event_type} - {details}")

    return log_entry


# Trading state
trading_state = {
    "auto_trade_enabled": False,
    "last_auto_trade": None,
    "trade_history": [],
    "kalshi_ready": False,
    "polymarket_ready": False,
}

# Initialize traders (lazy loading)
kalshi_trader = None
polymarket_trader = None

def get_kalshi_trader():
    global kalshi_trader
    if kalshi_trader is None:
        from traders.kalshi_trader import KalshiTrader
        kalshi_trader = KalshiTrader()
        trading_state["kalshi_ready"] = kalshi_trader.is_ready()
    return kalshi_trader

def get_polymarket_trader():
    global polymarket_trader
    if polymarket_trader is None:
        from traders.polymarket_trader import PolymarketTrader
        polymarket_trader = PolymarketTrader()
        trading_state["polymarket_ready"] = polymarket_trader.is_ready()
    return polymarket_trader

class TradeRequest(BaseModel):
    kalshi_strike: float
    poly_leg: str  # "Up" or "Down"
    kalshi_leg: str  # "Yes" or "No"
    poly_cost: float
    kalshi_cost: float
    quantity: int = 1

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/arbitrage")
async def get_arbitrage_data(contracts: int = Query(default=100, ge=1, le=10000, description="Number of contracts for fee calculation")):
    now = datetime.datetime.now(pytz.utc)
    fetch_start_time = now

    # Get market URLs
    market_info = get_current_market_urls()
    poly_slug = market_info["polymarket"].split("/")[-1]
    kalshi_ticker = market_info["kalshi"].split("/")[-1].upper()
    target_time = market_info["target_time_utc"]

    poly_err = None
    kalshi_err = None
    timing_info = {}

    # Use async fetcher if available (much faster)
    if ASYNC_AVAILABLE:
        try:
            all_data = await fetch_all_data_async(poly_slug, kalshi_ticker, target_time)
            poly_data = all_data["polymarket"]
            kalshi_data = all_data["kalshi"]
            timing_info = all_data.get("timing", {})

            # Check for errors in async fetch
            if all_data["errors"]:
                for err in all_data["errors"]:
                    if "polymarket" in err.lower():
                        poly_err = err
                    elif "kalshi" in err.lower():
                        kalshi_err = err
                    else:
                        poly_err = poly_err or err
        except Exception as e:
            logger.error(f"Async fetch failed, falling back to sync: {e}")
            poly_data, poly_err = fetch_polymarket_data_struct()
            kalshi_data, kalshi_err = fetch_kalshi_data_struct()
    else:
        # Fallback to sequential fetching
        poly_data, poly_err = fetch_polymarket_data_struct()
        kalshi_data, kalshi_err = fetch_kalshi_data_struct()

    fetch_end_time = datetime.datetime.now(pytz.utc)
    fetch_duration_ms = (fetch_end_time - fetch_start_time).total_seconds() * 1000

    # Check hour boundary protection
    near_boundary, minutes_until_safe = is_near_hour_boundary()

    # Validate market synchronization
    is_synced, sync_issues = validate_market_sync(poly_data, kalshi_data)

    # Detect transition anomalies
    has_anomaly, anomaly_reason = detect_market_transition_anomaly(poly_data, kalshi_data)

    # Determine if trading should be blocked
    transition_blocked = not is_synced or has_anomaly

    # Log transition events if blocked
    if transition_blocked:
        log_transition_event("TRANSITION_BLOCK", {
            "reason": anomaly_reason if has_anomaly else "Sync validation failed",
            "sync_issues": sync_issues,
            "near_boundary": near_boundary,
            "minute": now.minute,
            "second": now.second,
        })

    response = {
        "timestamp": datetime.datetime.now().isoformat(),
        "polymarket": poly_data,
        "kalshi": kalshi_data,
        "checks": [],
        "opportunities": [],
        "errors": [],
        "contracts": contracts,
        "hour_boundary_protection": {
            "active": near_boundary,
            "minutes_until_safe": minutes_until_safe,
            "reason": f"Market transition in progress - waiting {minutes_until_safe} min" if near_boundary else None,
        },
        "market_sync": {
            "is_synced": is_synced,
            "issues": sync_issues,
            "transition_blocked": transition_blocked,
            "anomaly_detected": has_anomaly,
            "anomaly_reason": anomaly_reason if has_anomaly else None,
            "fetch_duration_ms": round(fetch_duration_ms, 2),
            "timing_breakdown": timing_info,  # Detailed timing from async fetcher
            "async_mode": ASYNC_AVAILABLE,
            "current_minute": now.minute,
            "current_second": now.second,
        },
    }

    if poly_err:
        response["errors"].append(poly_err)
    if kalshi_err:
        response["errors"].append(kalshi_err)

    # Add sync issues to errors for visibility
    for issue in sync_issues:
        if issue not in response["errors"]:
            response["errors"].append(issue)

    if not poly_data or not kalshi_data:
        return response

    # If transition is blocked, return early with no opportunities (but include trading state)
    if transition_blocked:
        logger.warning(f"Trading blocked due to market transition: {anomaly_reason or sync_issues}")
        # Still add trading state for visibility
        response["trading"] = {
            "auto_trade_enabled": trading_state["auto_trade_enabled"],
            "kalshi_ready": trading_state["kalshi_ready"],
            "polymarket_ready": trading_state["polymarket_ready"],
            "paper_trading": settings.PAPER_TRADING,
            "last_auto_trade": trading_state["last_auto_trade"],
            "transition_blocked": True,
        }
        return response

    # Logic
    poly_strike = poly_data['price_to_beat']
    poly_up_cost = poly_data['prices'].get('Up', 0.0)
    poly_down_cost = poly_data['prices'].get('Down', 0.0)
    
    if poly_strike is None:
        response["errors"].append("Polymarket Strike is None")
        return response

    kalshi_markets = kalshi_data.get('markets', [])
    
    # Ensure sorted by strike
    kalshi_markets.sort(key=lambda x: x['strike'])
    
    # Find index closest to poly_strike
    closest_idx = 0
    min_diff = float('inf')
    for i, m in enumerate(kalshi_markets):
        diff = abs(m['strike'] - poly_strike)
        if diff < min_diff:
            min_diff = diff
            closest_idx = i
            
    # Select 4 below and 4 above (approx 8-9 markets total)
    # If closest is at index C, we want [C-4, C+5] roughly
    start_idx = max(0, closest_idx - 4)
    end_idx = min(len(kalshi_markets), closest_idx + 5) # +5 to include the closest and 4 above
    
    selected_markets = kalshi_markets[start_idx:end_idx]
    
    def add_fee_calculations(check: dict, num_contracts: int) -> dict:
        """Add fee calculations to a check dictionary"""
        fee_breakdown = calculate_arbitrage_with_fees(
            check["poly_cost"],
            check["kalshi_cost"],
            num_contracts
        )
        check["gross_margin"] = fee_breakdown.gross_margin
        check["net_margin"] = fee_breakdown.net_margin
        check["fees"] = {
            "polymarket_trading": fee_breakdown.polymarket_trading_fee,
            "polymarket_gas": fee_breakdown.polymarket_gas_fee,
            "kalshi": fee_breakdown.kalshi_fee,
            "total": fee_breakdown.total_fees,
        }
        check["is_profitable_after_fees"] = fee_breakdown.is_profitable
        # Keep backward compatibility: margin = gross_margin
        check["margin"] = fee_breakdown.gross_margin
        return check

    # Get Polymarket token IDs for trade execution (from async fetcher or None)
    poly_token_ids = poly_data.get('token_ids', {})

    for km in selected_markets:
        kalshi_strike = km['strike']
        kalshi_yes_cost = km['yes_ask'] / 100.0
        kalshi_no_cost = km['no_ask'] / 100.0
        kalshi_ticker = km.get('ticker', '')  # Actual market ticker for trading

        check_data = {
            "kalshi_strike": kalshi_strike,
            "kalshi_ticker": kalshi_ticker,  # Include actual ticker for trade execution
            "kalshi_yes": kalshi_yes_cost,
            "kalshi_no": kalshi_no_cost,
            "type": "",
            "poly_leg": "",
            "kalshi_leg": "",
            "poly_cost": 0,
            "kalshi_cost": 0,
            "total_cost": 0,
            "is_arbitrage": False,
            "margin": 0,
            "gross_margin": 0,
            "net_margin": 0,
            "fees": {},
            "is_profitable_after_fees": False,
            "poly_token_ids": poly_token_ids,  # Include for trade execution
        }

        if poly_strike > kalshi_strike:
            check_data["type"] = "Poly > Kalshi"
            check_data["poly_leg"] = "Down"
            check_data["kalshi_leg"] = "Yes"
            check_data["poly_cost"] = poly_down_cost
            check_data["kalshi_cost"] = kalshi_yes_cost
            check_data["total_cost"] = poly_down_cost + kalshi_yes_cost

        elif poly_strike < kalshi_strike:
            check_data["type"] = "Poly < Kalshi"
            check_data["poly_leg"] = "Up"
            check_data["kalshi_leg"] = "No"
            check_data["poly_cost"] = poly_up_cost
            check_data["kalshi_cost"] = kalshi_no_cost
            check_data["total_cost"] = poly_up_cost + kalshi_no_cost

        elif poly_strike == kalshi_strike:
            # Check 1: Down + Yes
            check1 = check_data.copy()
            check1["type"] = "Equal"
            check1["poly_leg"] = "Down"
            check1["kalshi_leg"] = "Yes"
            check1["poly_cost"] = poly_down_cost
            check1["kalshi_cost"] = kalshi_yes_cost
            check1["total_cost"] = poly_down_cost + kalshi_yes_cost

            if check1["total_cost"] < 1.00:
                check1["is_arbitrage"] = True
                check1 = add_fee_calculations(check1, contracts)
                # Only add to opportunities if profitable AFTER fees AND not near hour boundary with suspicious prices
                is_suspicious = near_boundary and has_suspicious_prices(poly_data['prices'], kalshi_yes_cost)
                check1["hour_boundary_blocked"] = is_suspicious
                if check1["is_profitable_after_fees"] and not is_suspicious:
                    response["opportunities"].append(check1)
            response["checks"].append(check1)

            # Check 2: Up + No
            check2 = check_data.copy()
            check2["type"] = "Equal"
            check2["poly_leg"] = "Up"
            check2["kalshi_leg"] = "No"
            check2["poly_cost"] = poly_up_cost
            check2["kalshi_cost"] = kalshi_no_cost
            check2["total_cost"] = poly_up_cost + kalshi_no_cost

            if check2["total_cost"] < 1.00:
                check2["is_arbitrage"] = True
                check2 = add_fee_calculations(check2, contracts)
                is_suspicious = near_boundary and has_suspicious_prices(poly_data['prices'], kalshi_no_cost)
                check2["hour_boundary_blocked"] = is_suspicious
                if check2["is_profitable_after_fees"] and not is_suspicious:
                    response["opportunities"].append(check2)
            response["checks"].append(check2)
            continue

        # Calculate fees for all checks
        check_data = add_fee_calculations(check_data, contracts)

        if check_data["total_cost"] < 1.00:
            check_data["is_arbitrage"] = True
            # Only add to opportunities if profitable AFTER fees AND not near hour boundary with suspicious prices
            kalshi_cost_to_check = kalshi_yes_cost if check_data["kalshi_leg"] == "Yes" else kalshi_no_cost
            is_suspicious = near_boundary and has_suspicious_prices(poly_data['prices'], kalshi_cost_to_check)
            check_data["hour_boundary_blocked"] = is_suspicious
            if check_data["is_profitable_after_fees"] and not is_suspicious:
                response["opportunities"].append(check_data)

        response["checks"].append(check_data)

    # Add trading state to response
    response["trading"] = {
        "auto_trade_enabled": trading_state["auto_trade_enabled"],
        "kalshi_ready": trading_state["kalshi_ready"],
        "polymarket_ready": trading_state["polymarket_ready"],
        "paper_trading": settings.PAPER_TRADING,
        "last_auto_trade": trading_state["last_auto_trade"],
        "transition_blocked": False,
    }

    # Find and mark the best opportunity by net margin
    if response["checks"]:
        # Find the check with highest net margin (even if not profitable)
        best_check = max(response["checks"], key=lambda x: x.get("net_margin", float('-inf')))
        best_strike = best_check.get("kalshi_strike")

        # Mark each check if it's the best
        for check in response["checks"]:
            check["is_best_strike"] = check.get("kalshi_strike") == best_strike

        # Add best strike info to response for easy access
        response["best_strike"] = {
            "kalshi_strike": best_strike,
            "net_margin": best_check.get("net_margin", 0),
            "is_profitable": best_check.get("is_profitable_after_fees", False),
        }

    # Auto-trade logic: execute if enabled and NET profitable opportunity exists
    # IMPORTANT: Never execute trades during market transitions
    if trading_state["auto_trade_enabled"] and response["opportunities"] and not transition_blocked:
        # Filter to only net-profitable opportunities
        profitable_opps = [o for o in response["opportunities"] if o.get("is_profitable_after_fees", False)]
        if profitable_opps:
            # Select best by NET margin (not gross)
            best_opp = max(profitable_opps, key=lambda x: x.get("net_margin", 0))
            if best_opp.get("net_margin", 0) >= settings.MIN_PROFIT_MARGIN:
                trade_result = execute_arbitrage_trade(best_opp, quantity=contracts)
                if trade_result:
                    trading_state["last_auto_trade"] = datetime.datetime.now().isoformat()
                    response["auto_trade_executed"] = trade_result

    return response


@app.get("/trading/status")
def get_trading_status():
    """Get current trading configuration and status"""
    # Initialize traders to check their status
    get_kalshi_trader()
    get_polymarket_trader()

    return {
        "auto_trade_enabled": trading_state["auto_trade_enabled"],
        "kalshi_ready": trading_state["kalshi_ready"],
        "polymarket_ready": trading_state["polymarket_ready"],
        "paper_trading": settings.PAPER_TRADING,
        "max_position_size": settings.MAX_POSITION_SIZE,
        "min_profit_margin": settings.MIN_PROFIT_MARGIN,
        "last_auto_trade": trading_state["last_auto_trade"],
        "trade_history": trading_state["trade_history"][-10:],  # Last 10 trades
    }


@app.post("/trading/auto-trade")
def toggle_auto_trade(enabled: bool):
    """Enable or disable automatic trading on arbitrage detection"""
    # Initialize traders when enabling
    if enabled:
        get_kalshi_trader()
        get_polymarket_trader()

        # Warn if traders aren't ready
        warnings = []
        if not trading_state["kalshi_ready"]:
            warnings.append("Kalshi trader not configured")
        if not trading_state["polymarket_ready"]:
            warnings.append("Polymarket trader not configured")

        trading_state["auto_trade_enabled"] = enabled

        return {
            "auto_trade_enabled": enabled,
            "warnings": warnings,
            "paper_trading": settings.PAPER_TRADING,
        }

    trading_state["auto_trade_enabled"] = enabled
    return {"auto_trade_enabled": enabled}


@app.post("/trading/execute")
def manual_execute_trade(trade: TradeRequest, force: bool = False):
    """
    Manually execute an arbitrage trade.

    Args:
        trade: Trade details
        force: If True, bypass transition safety checks (use with caution!)
    """
    # Check for market transition before executing
    if not force:
        poly_data, _ = fetch_polymarket_data_struct()
        kalshi_data, _ = fetch_kalshi_data_struct()

        is_synced, sync_issues = validate_market_sync(poly_data, kalshi_data)
        has_anomaly, anomaly_reason = detect_market_transition_anomaly(poly_data, kalshi_data)

        if not is_synced or has_anomaly:
            reason = anomaly_reason if has_anomaly else "; ".join(sync_issues)
            logger.warning(f"Manual trade blocked due to market transition: {reason}")
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "Trade blocked due to market transition",
                    "reason": reason,
                    "sync_issues": sync_issues,
                    "anomaly_detected": has_anomaly,
                    "hint": "Wait for market transition to complete or use force=true to bypass (dangerous)"
                }
            )

    # Initialize traders
    kalshi = get_kalshi_trader()
    polymarket = get_polymarket_trader()

    trade_data = {
        "kalshi_strike": trade.kalshi_strike,
        "poly_leg": trade.poly_leg,
        "kalshi_leg": trade.kalshi_leg,
        "poly_cost": trade.poly_cost,
        "kalshi_cost": trade.kalshi_cost,
        "total_cost": trade.poly_cost + trade.kalshi_cost,
        "margin": 1.0 - (trade.poly_cost + trade.kalshi_cost),
        "quantity": trade.quantity,
    }

    result = execute_arbitrage_trade(trade_data, quantity=trade.quantity)

    if result:
        return {
            "success": True,
            "trade": result,
            "paper_trading": settings.PAPER_TRADING,
            "forced": force,
        }
    else:
        raise HTTPException(status_code=500, detail="Trade execution failed")


def execute_arbitrage_trade(opportunity: dict, quantity: int = 1):
    """
    Execute an arbitrage trade on both platforms

    Args:
        opportunity: Dict with trade details (kalshi_strike, poly_leg, kalshi_leg, etc.)
        quantity: Number of contracts to buy

    Returns:
        Trade result dict or None on failure
    """
    kalshi = get_kalshi_trader()
    polymarket = get_polymarket_trader()

    timestamp = datetime.datetime.now().isoformat()

    trade_record = {
        "timestamp": timestamp,
        "opportunity": opportunity,
        "quantity": quantity,
        "kalshi_order": None,
        "polymarket_order": None,
        "status": "pending",
        "paper_trading": settings.PAPER_TRADING,
    }

    # Execute Kalshi leg
    if kalshi.is_ready():
        kalshi_side = "yes" if opportunity["kalshi_leg"] == "Yes" else "no"
        kalshi_price_cents = int(opportunity["kalshi_cost"] * 100)

        # Use actual ticker from market data
        kalshi_ticker = opportunity.get("kalshi_ticker", "")
        if not kalshi_ticker:
            logger.error("Kalshi ticker missing from opportunity - trade cannot execute")
            trade_record["kalshi_order"] = {"error": "Kalshi ticker missing"}
        else:
            kalshi_result = kalshi.place_order(
                ticker=kalshi_ticker,
                side=kalshi_side,
                quantity=quantity,
                price_cents=kalshi_price_cents
            )
            trade_record["kalshi_order"] = kalshi_result
    else:
        trade_record["kalshi_order"] = {"error": "Kalshi not ready"}

    # Execute Polymarket leg
    if polymarket.is_ready():
        poly_side = "BUY"
        poly_price = opportunity["poly_cost"]
        poly_leg = opportunity["poly_leg"]  # "Up" or "Down"

        # Get token ID for the leg we're buying
        poly_token_ids = opportunity.get("poly_token_ids", {})
        token_id = poly_token_ids.get(poly_leg, "")

        if not token_id:
            logger.error(f"Polymarket token ID missing for {poly_leg} - trade cannot execute")
            trade_record["polymarket_order"] = {"error": f"Token ID missing for {poly_leg}"}
        else:
            polymarket_result = polymarket.place_limit_order(
                token_id=token_id,
                side=poly_side,
                size=float(quantity),
                price=poly_price
            )
            trade_record["polymarket_order"] = polymarket_result
    else:
        trade_record["polymarket_order"] = {"error": "Polymarket not ready"}

    # Determine overall status
    if trade_record["kalshi_order"] and trade_record["polymarket_order"]:
        if "error" not in str(trade_record["kalshi_order"]) and "error" not in str(trade_record["polymarket_order"]):
            trade_record["status"] = "executed"
        else:
            trade_record["status"] = "partial"
    else:
        trade_record["status"] = "failed"

    # Record trade in history
    trading_state["trade_history"].append(trade_record)

    # Keep only last 100 trades
    if len(trading_state["trade_history"]) > 100:
        trading_state["trade_history"] = trading_state["trade_history"][-100:]

    print(f"[Trade] {trade_record['status'].upper()}: {opportunity['poly_leg']}/{opportunity['kalshi_leg']} @ ${opportunity['total_cost']:.3f}")

    return trade_record


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
