from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fetch_current_polymarket import fetch_polymarket_data_struct
from fetch_current_kalshi import fetch_kalshi_data_struct
from config.settings import settings
from fees import calculate_arbitrage_with_fees, calculate_total_fees
import datetime

app = FastAPI()

# Hour boundary protection settings
HOUR_BOUNDARY_BUFFER_MINUTES = 2  # Minutes before/after hour to pause trading
SUSPICIOUS_PRICE_THRESHOLD = 0.03  # Prices below 3¢ or above 97¢ are suspicious near boundaries


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
def get_arbitrage_data(contracts: int = Query(default=100, ge=1, le=10000, description="Number of contracts for fee calculation")):
    # Fetch Data
    poly_data, poly_err = fetch_polymarket_data_struct()
    kalshi_data, kalshi_err = fetch_kalshi_data_struct()

    # Check hour boundary protection
    near_boundary, minutes_until_safe = is_near_hour_boundary()

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
    }

    if poly_err:
        response["errors"].append(poly_err)
    if kalshi_err:
        response["errors"].append(kalshi_err)

    if not poly_data or not kalshi_data:
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

    for km in selected_markets:
        kalshi_strike = km['strike']
        kalshi_yes_cost = km['yes_ask'] / 100.0
        kalshi_no_cost = km['no_ask'] / 100.0

        check_data = {
            "kalshi_strike": kalshi_strike,
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
    }

    # Auto-trade logic: execute if enabled and NET profitable opportunity exists
    if trading_state["auto_trade_enabled"] and response["opportunities"]:
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
def manual_execute_trade(trade: TradeRequest):
    """Manually execute an arbitrage trade"""
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

    # For now, only execute Kalshi trades since Polymarket isn't set up yet
    # Execute Kalshi leg
    if kalshi.is_ready():
        kalshi_side = "yes" if opportunity["kalshi_leg"] == "Yes" else "no"
        kalshi_price_cents = int(opportunity["kalshi_cost"] * 100)

        # Build ticker from strike (this is simplified - may need adjustment)
        # Format: KXBTCD-25DEC1016-B{strike} or similar
        kalshi_result = kalshi.place_order(
            ticker=f"KXBTCD",  # You'll need to get the actual ticker
            side=kalshi_side,
            quantity=quantity,
            price_cents=kalshi_price_cents
        )
        trade_record["kalshi_order"] = kalshi_result
    else:
        trade_record["kalshi_order"] = {"error": "Kalshi not ready"}

    # Execute Polymarket leg (when available)
    if polymarket.is_ready():
        poly_side = "BUY"
        poly_price = opportunity["poly_cost"]

        polymarket_result = polymarket.place_limit_order(
            token_id="",  # You'll need to get the actual token ID
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
