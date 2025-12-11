"""
Fee Calculation Module for Polymarket and Kalshi

Fee Structures (as of 2024-2025):

POLYMARKET:
- US (Regulated): 0.01% taker fee (1 basis point)
- International: $0 trading fees
- Gas: ~$0.01-0.05 per transaction on Polygon

KALSHI:
- Taker: round_up(0.07 × contracts × price × (1-price))
- Max fee: 1.75¢ per contract (occurs at price = $0.50)
- Maker: $0 for general markets
- No settlement fees
"""

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class FeeBreakdown:
    """Detailed breakdown of fees for a trade"""
    polymarket_trading_fee: float
    polymarket_gas_fee: float
    kalshi_fee: float
    total_fees: float
    gross_margin: float
    net_margin: float
    is_profitable: bool
    profit_after_fees: float  # Per contract


# Configuration
POLYMARKET_TAKER_FEE_RATE = 0.0001  # 0.01% = 1 basis point
POLYMARKET_GAS_FEE = 0.02  # ~$0.01-0.02 per transaction, use conservative estimate
KALSHI_FEE_MULTIPLIER = 0.07  # 7% of price variance
KALSHI_MAX_FEE_PER_CONTRACT = 0.0175  # 1.75 cents max

# Minimum net profit threshold (configurable)
MIN_NET_PROFIT_MARGIN = 0.01  # $0.01 minimum profit per contract after fees


def calculate_polymarket_fee(contracts: int, price: float, is_us: bool = True) -> float:
    """
    Calculate Polymarket trading fee

    Args:
        contracts: Number of contracts to buy
        price: Price per contract (0.01 to 0.99)
        is_us: Whether using Polymarket US (has 0.01% fee) or International (free)

    Returns:
        Total fee in dollars

    Example:
        2000 contracts at $0.50 = $1000 notional
        Fee = $1000 × 0.0001 = $0.10
    """
    if not is_us:
        return 0.0

    notional_value = contracts * price
    return notional_value * POLYMARKET_TAKER_FEE_RATE


def calculate_kalshi_fee(contracts: int, price: float) -> float:
    """
    Calculate Kalshi taker fee using official formula

    Formula: round_up(0.07 × contracts × price × (1-price))
    Maximum: 1.75¢ per contract (at price = $0.50)

    Args:
        contracts: Number of contracts to buy
        price: Price per contract (0.01 to 0.99, where 0.50 = 50¢)

    Returns:
        Total fee in dollars

    Example:
        2000 contracts at $0.50:
        = ceil(0.07 × 2000 × 0.50 × 0.50)
        = ceil(35)
        = $35.00
    """
    # Calculate fee using the formula
    fee = KALSHI_FEE_MULTIPLIER * contracts * price * (1 - price)

    # Round up to nearest cent
    fee = math.ceil(fee * 100) / 100

    # Cap at maximum fee per contract
    max_fee = contracts * KALSHI_MAX_FEE_PER_CONTRACT

    return min(fee, max_fee)


def calculate_kalshi_fee_per_contract(price: float) -> float:
    """
    Calculate Kalshi fee for a single contract

    Useful for understanding fee impact at different price points.
    Fee is maximized at price = $0.50 (1.75¢)
    Fee approaches $0 as price approaches $0 or $1

    Args:
        price: Price per contract (0.01 to 0.99)

    Returns:
        Fee per contract in dollars
    """
    fee = KALSHI_FEE_MULTIPLIER * price * (1 - price)
    return min(fee, KALSHI_MAX_FEE_PER_CONTRACT)


def calculate_total_fees(
    contracts: int,
    poly_price: float,
    kalshi_price: float,
    is_polymarket_us: bool = True,
    include_gas: bool = True
) -> dict:
    """
    Calculate total fees for an arbitrage trade on both platforms

    Args:
        contracts: Number of contracts on each platform
        poly_price: Polymarket contract price
        kalshi_price: Kalshi contract price (in dollars, e.g., 0.50 for 50¢)
        is_polymarket_us: Whether using Polymarket US
        include_gas: Whether to include Polygon gas fees

    Returns:
        Dictionary with fee breakdown
    """
    poly_trading_fee = calculate_polymarket_fee(contracts, poly_price, is_polymarket_us)
    poly_gas_fee = POLYMARKET_GAS_FEE if include_gas else 0.0
    kalshi_fee = calculate_kalshi_fee(contracts, kalshi_price)

    total = poly_trading_fee + poly_gas_fee + kalshi_fee

    return {
        "polymarket_trading_fee": round(poly_trading_fee, 4),
        "polymarket_gas_fee": round(poly_gas_fee, 4),
        "kalshi_fee": round(kalshi_fee, 4),
        "total_fees": round(total, 4),
        "fee_per_contract": round(total / contracts, 4) if contracts > 0 else 0,
    }


def calculate_arbitrage_with_fees(
    poly_cost: float,
    kalshi_cost: float,
    contracts: int = 1,
    is_polymarket_us: bool = True
) -> FeeBreakdown:
    """
    Calculate full arbitrage profitability including all fees

    The arbitrage pays out $1.00 per contract if successful.
    Gross margin = $1.00 - (poly_cost + kalshi_cost)
    Net margin = Gross margin - fees

    Args:
        poly_cost: Cost of Polymarket contract (e.g., 0.07 for 7¢)
        kalshi_cost: Cost of Kalshi contract (e.g., 0.99 for 99¢)
        contracts: Number of contracts to trade
        is_polymarket_us: Whether using Polymarket US (has fees)

    Returns:
        FeeBreakdown with complete analysis
    """
    # Calculate gross margin (before fees)
    total_cost = poly_cost + kalshi_cost
    gross_margin = 1.00 - total_cost

    # Calculate fees
    poly_trading_fee = calculate_polymarket_fee(contracts, poly_cost, is_polymarket_us)
    poly_gas_fee = POLYMARKET_GAS_FEE  # Per transaction
    kalshi_fee = calculate_kalshi_fee(contracts, kalshi_cost)

    total_fees = poly_trading_fee + poly_gas_fee + kalshi_fee
    fee_per_contract = total_fees / contracts if contracts > 0 else 0

    # Calculate net margin (after fees)
    # Gross profit = gross_margin * contracts
    # Net profit = gross_profit - total_fees
    gross_profit = gross_margin * contracts
    net_profit = gross_profit - total_fees
    net_margin = net_profit / contracts if contracts > 0 else 0

    # Determine if profitable
    is_profitable = net_margin > 0

    return FeeBreakdown(
        polymarket_trading_fee=round(poly_trading_fee, 4),
        polymarket_gas_fee=round(poly_gas_fee, 4),
        kalshi_fee=round(kalshi_fee, 4),
        total_fees=round(total_fees, 4),
        gross_margin=round(gross_margin, 4),
        net_margin=round(net_margin, 4),
        is_profitable=is_profitable,
        profit_after_fees=round(net_margin, 4),
    )


def calculate_breakeven_margin(
    poly_price: float,
    kalshi_price: float,
    contracts: int = 100,
    is_polymarket_us: bool = True
) -> float:
    """
    Calculate the minimum gross margin needed to break even after fees

    Args:
        poly_price: Approximate Polymarket price
        kalshi_price: Approximate Kalshi price
        contracts: Number of contracts (affects fee calculation)
        is_polymarket_us: Whether using Polymarket US

    Returns:
        Minimum gross margin needed to break even (as decimal, e.g., 0.035 = 3.5%)
    """
    fees = calculate_total_fees(contracts, poly_price, kalshi_price, is_polymarket_us)
    fee_per_contract = fees["fee_per_contract"]

    # Breakeven: gross_margin = fee_per_contract
    return fee_per_contract


def calculate_minimum_contracts_for_profit(
    gross_margin: float,
    poly_price: float,
    kalshi_price: float,
    target_profit: float = 1.00,
    is_polymarket_us: bool = True
) -> int:
    """
    Calculate minimum contracts needed to achieve target profit

    Due to fixed costs (gas), there's a minimum scale needed for profitability.

    Args:
        gross_margin: Gross margin per contract (e.g., 0.02 for 2¢)
        poly_price: Polymarket contract price
        kalshi_price: Kalshi contract price
        target_profit: Target profit in dollars
        is_polymarket_us: Whether using Polymarket US

    Returns:
        Minimum number of contracts needed
    """
    # Binary search for minimum contracts
    low, high = 1, 10000

    while low < high:
        mid = (low + high) // 2
        breakdown = calculate_arbitrage_with_fees(poly_price, kalshi_price, mid, is_polymarket_us)
        net_profit = breakdown.net_margin * mid

        if net_profit >= target_profit:
            high = mid
        else:
            low = mid + 1

    return low


def get_fee_summary(poly_cost: float, kalshi_cost: float, contracts: int = 1) -> str:
    """
    Generate human-readable fee summary for an arbitrage opportunity

    Args:
        poly_cost: Polymarket contract cost
        kalshi_cost: Kalshi contract cost
        contracts: Number of contracts

    Returns:
        Formatted string summary
    """
    breakdown = calculate_arbitrage_with_fees(poly_cost, kalshi_cost, contracts)

    lines = [
        f"=== Fee Analysis ({contracts} contracts) ===",
        f"Gross Margin: ${breakdown.gross_margin:.4f}/contract",
        f"",
        f"Fees:",
        f"  Polymarket Trading: ${breakdown.polymarket_trading_fee:.4f}",
        f"  Polymarket Gas:     ${breakdown.polymarket_gas_fee:.4f}",
        f"  Kalshi Fee:         ${breakdown.kalshi_fee:.4f}",
        f"  Total Fees:         ${breakdown.total_fees:.4f}",
        f"",
        f"Net Margin: ${breakdown.net_margin:.4f}/contract",
        f"Profitable: {'YES' if breakdown.is_profitable else 'NO'}",
    ]

    if breakdown.is_profitable:
        total_profit = breakdown.net_margin * contracts
        lines.append(f"Total Profit: ${total_profit:.2f}")
    else:
        needed = calculate_breakeven_margin(poly_cost, kalshi_cost, contracts)
        lines.append(f"Need {needed*100:.2f}% gross margin to break even")

    return "\n".join(lines)


# Example usage and testing
if __name__ == "__main__":
    print("=== Fee Calculation Examples ===\n")

    # Example 1: Typical arbitrage opportunity
    print("Example 1: Poly DOWN $0.07 + Kalshi YES $0.92 = $0.99 total")
    print("(Gross margin: $0.01)\n")

    for num_contracts in [1, 10, 100, 1000]:
        breakdown = calculate_arbitrage_with_fees(0.07, 0.92, num_contracts)
        print(f"{num_contracts:4d} contracts: Gross=${breakdown.gross_margin:.4f}, "
              f"Fees=${breakdown.total_fees:.4f}, Net=${breakdown.net_margin:.4f}, "
              f"Profitable={breakdown.is_profitable}")

    print("\n" + "="*50 + "\n")

    # Example 2: Better arbitrage opportunity
    print("Example 2: Poly DOWN $0.05 + Kalshi YES $0.90 = $0.95 total")
    print("(Gross margin: $0.05)\n")

    for num_contracts in [1, 10, 100, 1000]:
        breakdown = calculate_arbitrage_with_fees(0.05, 0.90, num_contracts)
        print(f"{num_contracts:4d} contracts: Gross=${breakdown.gross_margin:.4f}, "
              f"Fees=${breakdown.total_fees:.4f}, Net=${breakdown.net_margin:.4f}, "
              f"Profitable={breakdown.is_profitable}")

    print("\n" + "="*50 + "\n")

    # Example 3: Fee breakdown at different Kalshi prices
    print("Kalshi fee per contract at different prices:")
    for price in [0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]:
        fee = calculate_kalshi_fee_per_contract(price)
        print(f"  Price ${price:.2f}: Fee ${fee:.4f} ({fee*100:.2f}¢)")

    print("\n" + "="*50 + "\n")

    # Example 4: Full summary
    print(get_fee_summary(0.07, 0.92, 100))
