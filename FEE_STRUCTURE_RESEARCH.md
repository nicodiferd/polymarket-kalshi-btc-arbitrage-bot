# Polymarket & Kalshi Fee Structure Research

**Research Date:** December 10, 2025
**Purpose:** Comprehensive fee analysis for arbitrage bot implementation
**Project:** Bitcoin 1-Hour Price Arbitrage Detection Bot

---

## Executive Summary

### Key Findings
- **Polymarket US** has the lowest fees at 0.01% (1 basis point) for taker orders only
- **Kalshi** charges variable fees based on contract price, averaging 0.7-2% per trade
- **Minimum Profitable Arbitrage Margin:** 2-3% gross margin needed for 1-2% net profit after fees
- **Fees are charged on entry (trading)** - no additional fees on winning payouts or settlement

### Platform Comparison Table

| Platform | Trading Fee (Taker) | Trading Fee (Maker) | Settlement Fee | Withdrawal Fee (ACH) |
|----------|---------------------|---------------------|----------------|---------------------|
| **Polymarket US** | 0.01% of premium | $0 | $0 | $0 |
| **Polymarket Int'l** | $0 | $0 | $0 | $0 (relayer: $3 or 0.3%) |
| **Kalshi** | 0.07×C×P×(1-P) | 0.0175×C×P×(1-P)* | $0 | $0 |

*Maker fees only apply to specific sports/economic markets (NFL, NBA, NHL, golf, tennis, economic indicators)

---

## 1. Polymarket Fee Structure

### 1.1 Trading Fees

#### Polymarket US (Regulated Platform)
- **Taker Fee:** 0.01% (1 basis point) on total contract premium
- **Maker Fee:** $0 (no maker fees)
- **Formula:** `Taker Fee = Total Contract Premium × 0.0001`
- **Where:** `Total Contract Premium = Number of Contracts × Contract Price`

#### Polymarket International (Global Platform)
- **Trading Fees:** $0 (completely fee-free)
- **Liquidity Provider Fees:** Small fees paid to LPs embedded in spread (not charged separately)

### 1.2 Gas Fees on Polygon Network

**Network:** Polygon PoS (Layer 2 solution)
- **Average Transaction Cost:** $0.0005 - $0.01 per transaction
- **Basic MATIC Transfers:** ~$0.0005 - $0.002
- **Smart Contract Interactions:** ~$0.01 - $0.10 (DeFi, swaps, etc.)
- **Current Gas Price:** ~122 Gwei (as of Dec 2025)

**How Gas Fees Work:**
- Paid in POL (formerly MATIC) tokens
- 1 POL = 1,000,000,000 Gwei
- Composed of: Base fee (burned) + Inclusion fee/tip (paid to validators)
- Fees increase with network congestion

**Practical Impact:**
- Polygon gas fees are 100-1000x cheaper than Ethereum mainnet
- Typical Polymarket trade incurs < $0.01 in gas fees
- Total blockchain fees over time: ~$27,000 for entire Polymarket platform (2024)

### 1.3 Deposit/Withdrawal Fees

#### Polymarket Platform Fees
- **Deposits:** $0 (Polymarket charges nothing)
- **Withdrawals:** $0 (Polymarket charges nothing)

#### Third-Party/Infrastructure Fees
- **Relayer Fee (International):** Higher of:
  - $3 + network fee, OR
  - 0.3% of withdrawal amount
  - Example: $10 gas fee → $3 relayer fee (unless withdrawal > $4,333)
- **Polygon Network Fee:** $0.0005 - $0.01 (standard blockchain gas)

#### Third-Party Exchange Fees
- **Coinbase/MoonPay:** Variable fees (charged by those services, not Polymarket)
- **Crypto.com:** $25 USDC withdrawal fee (when moving FROM Crypto.com)

#### Withdrawal Methods
1. **Manual Withdrawals:** Easiest, standard fees apply
2. **Peer-to-Peer:** Cheapest option (direct user-to-user transfer)
3. **Polygon Withdrawals:** Cheap and fast (~$0.01 total)

### 1.4 Fee Calculation Examples

#### Example 1: Polymarket US - Small Trade
- **Scenario:** Buy 500 contracts at $0.40 each
- **Total Premium:** 500 × $0.40 = $200
- **Taker Fee:** $200 × 0.0001 = $0.02
- **Total Cost:** $200.02

#### Example 2: Polymarket US - Medium Trade
- **Scenario:** Buy 2,000 contracts at $0.50 each
- **Total Premium:** 2,000 × $0.50 = $1,000
- **Taker Fee:** $1,000 × 0.0001 = $0.10
- **Total Cost:** $1,000.10

#### Example 3: Polymarket US - Large Trade
- **Scenario:** Buy 10,000 contracts at $0.65 each
- **Total Premium:** 10,000 × $0.65 = $6,500
- **Taker Fee:** $6,500 × 0.0001 = $0.65
- **Total Cost:** $6,500.65

#### Example 4: Polymarket International
- **Any Trade Size:** $0 trading fees
- **Gas Fees Only:** ~$0.01 per transaction
- **Withdrawal:** $3 relayer fee + ~$0.01 network fee (for typical withdrawal)

---

## 2. Kalshi Fee Structure

### 2.1 Trading Fees Per Contract

#### Taker Fees (Aggressive Orders)
- **Formula:** `round_up(0.07 × C × P × (1-P))`
- **Where:**
  - C = Number of contracts
  - P = Contract price in dollars (e.g., $0.50 = 0.5)
  - round_up = Round to next cent

**Fee Characteristics:**
- **Maximum Fee:** 1.75¢ per contract (at P = $0.50)
- **Minimum Fee:** Approaches $0 (at P ≈ $0.01 or $0.99)
- **Average Effective Fee:** ~0.7-2% of contract value

#### Maker Fees (Resting Orders)
**General Markets:**
- **Formula:** $0 (no maker fees)

**Special Markets (Sports & Economic Indicators):**
- **Formula:** `round_up(0.0175 × C × P × (1-P))`
- **Applies to:** NFL, NBA, NHL games, golf/tennis majors, economic indicators
- **Maximum Fee:** 0.4375¢ per contract (at P = $0.50)

### 2.2 Special Market Fees

#### S&P 500 and NASDAQ-100 Markets
- **Formula:** `round_up(0.035 × C × P × (1-P))`
- **Maximum Fee:** 0.875¢ per contract (at P = $0.50)

### 2.3 Other Fees

#### Settlement Fees
- **Amount:** $0 (no settlement fees)

#### Membership/Account Fees
- **Monthly Fee:** $0
- **Inactivity Fee:** $0
- **Account Cancellation Fee:** $0

#### Deposit Fees
- **ACH Bank Transfer:** $0
- **Wire Transfer:** $0 (Kalshi), varies by bank
- **Debit Card:** 2% of deposit amount

#### Withdrawal Fees
- **ACH Bank Transfer:** $0
- **Wire Transfer:** $2 flat fee
- **Debit Card:** $2 flat fee

#### Withdrawal Limits & Hold Periods
- **Debit Card Limit:** $2,500/day
- **ACH/Wire Limit:** No limit
- **Hold Periods:**
  - Debit deposits: 3 days
  - Same-bank ACH: 7 days
  - Different-bank ACH: 30 days

### 2.4 Fee Calculation Examples

#### Example 1: Taker Order at 50¢ (Maximum Fee)
- **Scenario:** Buy 100 contracts at $0.50 each
- **Calculation:** 0.07 × 100 × 0.5 × (1-0.5) = 0.07 × 100 × 0.25 = 1.75
- **Fee:** $1.75 (1.75¢ per contract)
- **Total Cost:** $50 + $1.75 = $51.75
- **Effective Fee Rate:** 3.5% of contract value

#### Example 2: Taker Order at 75¢
- **Scenario:** Buy 100 contracts at $0.75 each
- **Calculation:** 0.07 × 100 × 0.75 × 0.25 = 1.3125 → $1.32 (rounded up)
- **Fee:** $1.32
- **Total Cost:** $75 + $1.32 = $76.32
- **Effective Fee Rate:** 1.76% of contract value

#### Example 3: Taker Order at 10¢ (Low Probability)
- **Scenario:** Buy 100 contracts at $0.10 each
- **Calculation:** 0.07 × 100 × 0.10 × 0.90 = 0.63 → $0.63
- **Fee:** $0.63
- **Total Cost:** $10 + $0.63 = $10.63
- **Effective Fee Rate:** 6.3% of contract value

#### Example 4: Taker Order at 98¢ (High Probability)
- **Scenario:** Buy 100 contracts at $0.98 each
- **Calculation:** 0.07 × 100 × 0.98 × 0.02 = 0.1372 → $0.14
- **Fee:** $0.14
- **Total Cost:** $98 + $0.14 = $98.14
- **Effective Fee Rate:** 0.14% of contract value

#### Example 5: Maker Order on NFL Market
- **Scenario:** Place resting order for 100 contracts at $0.50 (NFL game)
- **Calculation:** 0.0175 × 100 × 0.5 × 0.5 = 0.4375 → $0.44
- **Fee:** $0.44
- **Total Cost:** $50 + $0.44 = $50.44

#### Example 6: Comparison with Polymarket
- **Same Trade:** 2,000 contracts at $0.50
- **Kalshi Fee:** 0.07 × 2,000 × 0.5 × 0.5 = $35
- **Polymarket US Fee:** $1,000 × 0.0001 = $0.10
- **Difference:** Kalshi is 350x more expensive

### 2.5 Fee Rounding Refund Policy
- Fees are rounded up to the next cent
- If rounding adds >$10 in excess fees per month, Kalshi refunds the excess
- Refunds processed in first week of following month

---

## 3. When Are Fees Charged?

### 3.1 Entry vs. Exit

#### Polymarket
- **Entry (Buy):** Taker fee charged at time of purchase (US platform only)
- **Exit (Sell):** Taker fee charged at time of sale if selling before resolution
- **Settlement:** No fees when market resolves - winning shares automatically pay $1

#### Kalshi
- **Entry (Buy):** Taker/maker fee charged immediately when order executes
- **Exit (Sell):** Taker/maker fee charged when selling position early
- **Settlement:** No fees when market resolves - winning contracts pay $1

### 3.2 Fees on Winning Payouts

#### Polymarket
- **US Platform:** No fees on payouts (already paid on entry)
- **International Platform:**
  - Conflicting information exists
  - Most sources say no fees on payouts
  - One source claims 2% fee on net winnings
  - **Clarification needed for your use case**

#### Kalshi
- **No fees on winning payouts**
- All fees are transaction-based (charged when buying/selling)
- Winning $1 per contract is paid in full

### 3.3 Gas/Network Fees

#### Polymarket
- **Every On-Chain Action:** Depositing, withdrawing, and on-chain settlements incur Polygon gas fees
- **Trading:** May involve gas fees for smart contract interactions (~$0.01)
- **Timing:** Charged when transaction is submitted to blockchain

#### Kalshi
- **No Blockchain Fees:** Centralized platform, no gas fees

---

## 4. Minimum Profitable Arbitrage Margin

### 4.1 Fee Impact on Arbitrage

#### Cost Components for Round-Trip Arbitrage
1. **Entry Fees (Polymarket):** 0.01% on US platform, $0 on international
2. **Entry Fees (Kalshi):** ~0.7-3.5% (depends on contract price)
3. **Exit Fees:** Same as entry if closing before resolution
4. **Gas Fees (Polymarket):** ~$0.01 - $0.02 per transaction
5. **Withdrawal Fees:** $0 (ACH), $2 (wire/debit card)

### 4.2 Minimum Margin Calculations

#### Scenario A: Hold Until Resolution (No Exit)

**Polymarket US + Kalshi (Most Common Case)**
- Position Size: $1,000 per platform ($2,000 total)
- Polymarket Fee: $1,000 × 0.0001 = $0.10
- Polymarket Gas: ~$0.01
- Kalshi Fee (at 50¢): 0.07 × 2,000 × 0.5 × 0.5 = $35
- **Total Fees:** $35.11
- **Minimum Margin for Breakeven:** 3.51% ($35.11 / $1,000)
- **For 1% Net Profit:** Need 4.51% gross margin

**Polymarket International + Kalshi (Lower Fees)**
- Position Size: $1,000 per platform ($2,000 total)
- Polymarket Fee: $0
- Polymarket Gas: ~$0.01
- Kalshi Fee: $35
- **Total Fees:** $35.01
- **Minimum Margin for Breakeven:** 3.50%
- **For 1% Net Profit:** Need 4.50% gross margin

#### Scenario B: Early Exit on One Platform

**Additional Fees for Closing Position:**
- Polymarket US: Additional 0.01% + ~$0.01 gas
- Kalshi: Additional 0.7-3.5% (same formula)
- **Total Round-Trip Fees:** Roughly double the entry fees
- **Minimum Margin for 1% Profit:** 7-9% gross margin

### 4.3 Practical Arbitrage Thresholds

#### Conservative Strategy (Recommended)
- **Minimum Gross Margin:** 3.0%
- **Expected Net Profit:** 0.5-1.0% after fees
- **Risk Buffer:** Accounts for slippage, fee rounding, price movement

#### Aggressive Strategy
- **Minimum Gross Margin:** 2.0%
- **Expected Net Profit:** 0.3-0.7% after fees
- **Risk:** Tight margins, vulnerable to slippage/price changes

#### Reported Real-World Performance
- Presidential election 2024: 1-2.5% arbitrage opportunities (gross margins)
- One trader reported: 1.7% average expected return (net)
- Most profitable trade: 2.1% net yield
- Historical arbitrage: 2.55% gross margin examples

### 4.4 Fee-Optimized Strategies

#### 1. Use Polymarket International When Possible
- Zero trading fees vs. 0.01% on US platform
- Saves 0.01% per trade ($0.10 on $1,000 position)
- Only viable for non-US users

#### 2. Place Maker Orders on Kalshi
- General markets: $0 maker fees vs. taker fees
- Requires patience (order must rest on orderbook)
- Not viable for time-sensitive arbitrage

#### 3. Trade High-Probability Contracts on Kalshi
- Fees decrease as P approaches 0.01 or 0.99
- At P=$0.98: Only 0.14% effective fee vs. 3.5% at P=$0.50
- Strategy: Focus on extreme probability mismatches

#### 4. Batch Withdrawals
- Avoid $2 wire/debit fees by using ACH (free)
- Minimize withdrawal frequency to reduce relayer fees (Polymarket)

---

## 5. Project-Specific Recommendations

### 5.1 Current Bot Architecture Review

**From CLAUDE.md:**
- Backend fetches Polymarket CLOB API + Kalshi Trade API
- Arbitrage logic: `total_cost < $1.00`, margin = `$1.00 - total_cost`
- Frontend polls every 1 second

**Gap Identified:**
- Current logic doesn't account for trading fees in arbitrage calculation
- Displayed margin is gross, not net (after fees)

### 5.2 Required Backend Modifications

#### Module: `api.py` / `arbitrage_bot.py`

**Add Fee Calculation Functions:**

```python
def calculate_polymarket_fee(contracts: int, price: float, platform: str = "us") -> float:
    """
    Calculate Polymarket trading fee

    Args:
        contracts: Number of contracts
        price: Contract price in dollars (0.0-1.0)
        platform: "us" or "international"

    Returns:
        Fee in dollars
    """
    if platform == "international":
        return 0.0

    premium = contracts * price
    fee = premium * 0.0001  # 0.01% = 1 basis point
    return round(fee, 2)  # Round to nearest cent


def calculate_kalshi_fee(contracts: int, price: float, order_type: str = "taker",
                         market_type: str = "general") -> float:
    """
    Calculate Kalshi trading fee

    Args:
        contracts: Number of contracts
        price: Contract price in dollars (0.0-1.0)
        order_type: "taker" or "maker"
        market_type: "general", "sports", or "index"

    Returns:
        Fee in dollars (rounded up to next cent)
    """
    import math

    # Determine multiplier based on order type and market
    if market_type == "index":
        multiplier = 0.035
    elif order_type == "maker" and market_type == "sports":
        multiplier = 0.0175
    elif order_type == "taker":
        multiplier = 0.07
    else:
        return 0.0  # Maker on general markets is free

    fee = multiplier * contracts * price * (1 - price)
    return math.ceil(fee * 100) / 100  # Round up to next cent


def calculate_arbitrage_with_fees(poly_contracts: int, poly_price: float,
                                   kalshi_contracts: int, kalshi_price: float,
                                   poly_platform: str = "us") -> dict:
    """
    Calculate net arbitrage margin after all fees

    Returns:
        {
            "gross_cost": float,
            "poly_fee": float,
            "kalshi_fee": float,
            "gas_estimate": float,
            "total_fees": float,
            "net_cost": float,
            "gross_margin": float,
            "net_margin": float,
            "is_profitable": bool
        }
    """
    # Calculate gross costs
    poly_cost = poly_contracts * poly_price
    kalshi_cost = kalshi_contracts * kalshi_price
    gross_cost = poly_cost + kalshi_cost

    # Calculate fees
    poly_fee = calculate_polymarket_fee(poly_contracts, poly_price, poly_platform)
    kalshi_fee = calculate_kalshi_fee(kalshi_contracts, kalshi_price)
    gas_estimate = 0.01  # $0.01 average Polygon gas

    total_fees = poly_fee + kalshi_fee + gas_estimate
    net_cost = gross_cost + total_fees

    # Margins (assuming $1.00 guaranteed payout)
    gross_margin = 1.0 - gross_cost
    net_margin = 1.0 - net_cost

    return {
        "gross_cost": round(gross_cost, 4),
        "poly_fee": round(poly_fee, 4),
        "kalshi_fee": round(kalshi_fee, 4),
        "gas_estimate": gas_estimate,
        "total_fees": round(total_fees, 4),
        "net_cost": round(net_cost, 4),
        "gross_margin": round(gross_margin * 100, 2),  # As percentage
        "net_margin": round(net_margin * 100, 2),
        "is_profitable": net_margin > 0
    }
```

#### Integration Points

**In `/arbitrage` endpoint response:**
```python
# Current structure (simplified)
{
    "polymarket": {...},
    "kalshi": {...},
    "arbitrage": {
        "poly_greater_kalshi": {
            "margin": 1.5,  # Current: gross margin only
            # ADD:
            "gross_margin": 1.5,
            "fees": {
                "polymarket": 0.10,
                "kalshi": 12.50,
                "gas": 0.01,
                "total": 12.61
            },
            "net_margin": 0.24,  # After fees
            "is_profitable_after_fees": true
        }
    }
}
```

### 5.3 Frontend Display Updates

**File:** `frontend/app/page.tsx`

**Add Fee Breakdown Display:**
- Show both gross and net margins
- Color-code based on net profitability (not gross)
- Add tooltip/expandable section showing fee breakdown
- Update profitability threshold logic

**Visual Indicators:**
- Green: Net margin > 1%
- Yellow: Net margin 0.3-1%
- Red: Net margin < 0.3%

### 5.4 Configuration Parameters

**Add to `backend` (e.g., `config.py`):**

```python
# Fee Configuration
POLYMARKET_PLATFORM = "us"  # "us" or "international"
MIN_NET_MARGIN_THRESHOLD = 0.005  # 0.5% minimum net profit
KALSHI_ORDER_TYPE = "taker"  # Assume taker orders (instant execution)
POLYGON_GAS_ESTIMATE = 0.01  # Conservative estimate
INCLUDE_WITHDRAWAL_FEES = False  # For round-trip calculation, add $2 wire fee
```

### 5.5 Testing Considerations

**Fee Calculation Test Cases:**
1. Polymarket US vs. International fee difference
2. Kalshi fees at P=0.50 (max), P=0.10 (low), P=0.98 (high)
3. Edge case: Gross profit but net loss after fees
4. Rounding behavior (fees round up)

**Integration Tests:**
1. API response includes fee breakdown
2. Frontend correctly displays net vs. gross margin
3. Alert threshold uses net margin, not gross

### 5.6 Future Enhancements

#### Advanced Fee Modeling
1. **Dynamic Gas Estimation:** Query Polygon gas price API in real-time
2. **Kalshi Maker/Taker Detection:** Check if orderbook has sufficient liquidity for maker orders
3. **Withdrawal Cost Amortization:** Calculate per-trade cost if withdrawal frequency known
4. **Historical Fee Tracking:** Log actual fees paid vs. estimated

#### Arbitrage Execution Module
If bot will execute trades (not just detect):
1. Implement retry logic for failed transactions
2. Slippage tolerance (price movement during execution)
3. Transaction batching to reduce gas fees
4. Emergency stop-loss if fees spike

---

## 6. Known Issues & Gotchas

### 6.1 Polymarket International Profit Fee Ambiguity
- **Issue:** One source claims 2% fee on net winnings for international platform
- **Conflicting Info:** Most official sources say zero fees
- **Resolution Needed:** Test small trade or contact Polymarket support
- **Impact:** Could reduce profitability by 2% if true

### 6.2 Kalshi Fee Rounding
- **Issue:** Fees round up to next cent
- **Impact:** Small trades (<100 contracts) have disproportionately high fees
- **Example:** $0.001 fee becomes $0.01 (10x increase)
- **Mitigation:** Trade in larger batches when possible

### 6.3 Market Resolution Discrepancies
- **Historical Case:** 2024 US government shutdown
  - Polymarket: Resolved "Yes" (incorrectly)
  - Kalshi: Resolved "No" (correctly)
- **Risk:** Arbitrage assumes both markets resolve identically
- **Impact:** Total loss instead of guaranteed profit
- **Mitigation:** Only arbitrage markets with identical, objective resolution criteria

### 6.4 Polygon Gas Spikes
- **Issue:** Gas fees can spike 10-100x during network congestion
- **Normal:** $0.01, **Spike:** $0.10 - $1.00
- **Mitigation:** Monitor gas prices, delay non-urgent transactions

### 6.5 Kalshi Withdrawal Hold Periods
- **Issue:** Funds locked for 3-30 days depending on deposit method
- **Impact:** Reduces capital efficiency for high-frequency arbitrage
- **Mitigation:** Maintain float balance, use same-bank ACH (7-day hold)

### 6.6 Liquidity Constraints
- **Not a Fee Issue, But Critical:**
- Orderbook depth may not support large arbitrage positions
- Slippage can erase thin margins
- Always check available liquidity before calculating arbitrage

---

## 7. Competitor Fee Comparison

### Other Prediction Markets

| Platform | Trading Fee | Payout Fee | Withdrawal Fee | Notes |
|----------|-------------|------------|----------------|-------|
| **PredictIt** | ~2% | 5% on profits | 5% | Highest total fees |
| **Robinhood** | $0.01/contract + $0.01 exchange | $0 | $0 | ~$40 for 2k contracts |
| **Betfair** | 5% commission | 5% on winnings | Varies | Sports betting exchange |
| **Manifold** | 0% | 0% | 0% | Play-money, not real $ |

### Traditional Sportsbooks
- **Juice/Vig:** 4-10% built into odds (not transparent fee)
- **Withdrawal Fees:** $0-50 depending on method
- **Deposit Bonuses:** Often have rollover requirements (hidden cost)

**Key Insight:** Polymarket US + Kalshi combination offers the lowest total fee structure in the prediction market space (excluding play-money platforms).

---

## 8. Next Steps

### 8.1 Immediate Actions
1. **Implement Fee Calculation Functions** in backend (see Section 5.2)
2. **Update API Response** to include fee breakdown (gross vs. net margin)
3. **Modify Frontend Display** to show net profitability prominently
4. **Test Fee Calculations** with known examples from official docs

### 8.2 Validation
1. **Manual Verification:** Place small test trade on each platform, verify actual fees match calculations
2. **Polymarket International Clarification:** Resolve 2% payout fee question
3. **Edge Case Testing:** Test fee calculation at P=0.01, P=0.50, P=0.99

### 8.3 Configuration
1. **Add Config File** with fee parameters (platform selection, thresholds)
2. **Environment Variables** for API keys, platform selection
3. **Logging:** Track fee calculations for debugging

### 8.4 Documentation
1. **Update CLAUDE.md** to reference this fee research doc
2. **API Documentation:** Document new fee-related response fields
3. **User Guide:** Explain gross vs. net margin in frontend

---

## 9. References

### Official Documentation
- [Polymarket Trading Fees](https://docs.polymarket.com/polymarket-learn/trading/fees)
- [Polymarket US Fee Schedule](https://www.polymarketexchange.com/fees-hours.html)
- [Polymarket Deposits & Withdrawals](https://legacy-docs.polymarket.com/faq/deposits-and-withdrawals)
- [Kalshi Fee Schedule (PDF)](https://kalshi.com/docs/kalshi-fee-schedule.pdf)
- [Kalshi Fees Help Center](https://help.kalshi.com/trading/fees)
- [Kalshi CFTC Filing](https://www.cftc.gov/sites/default/files/filings/orgrules/22/09/rule091222kexdcm003.pdf)

### Polygon Network
- [PolygonScan Gas Tracker](https://polygonscan.com/gastracker)
- [QuickNode Polygon Gas Tracker](https://www.quicknode.com/gas-tracker/polygon)
- [Blocknative Polygon Gas Estimator](https://www.blocknative.com/gas-estimator/polygon)
- [Polygon Gas Price Chart](https://polygonscan.com/chart/gasprice)

### Fee Analysis & Comparisons
- [Polymarket's U.S. Return Comes With Tiny Fees](https://predictionnews.com/news/polymarkets-u-s-return-comes-with-tiny-fees-putting-rivals-on-notice/)
- [Kalshi's New Fee Structure](https://predictionnews.com/news/what-kalshis-new-fee-structure-means-for-traders/)
- [Polymarket vs Kalshi Comparison](https://www.datawallet.com/crypto/polymarket-vs-kalshi)
- [Kalshi Fee Updates (USiGamingHUB)](https://usigaminghub.com/kalshi-updates-its-trading-fee-structure/)

### Arbitrage Resources
- [Polymarket & Kalshi Calculators](https://defirate.com/prediction-markets/calculators/)
- [Event Contract Arbitrage Calculator](https://www.eventarb.com/)
- [Prediction Market Arbitrage (Monad Blog)](https://blog.monad.xyz/blog/prediction-market-arbitrage)
- [Prediction Market Arbitrage Betting](https://betmetricslab.com/arbitrage-betting/prediction-market-arbitrage/)
- [Maker/Taker Math on Kalshi](https://whirligigbear.substack.com/p/makertaker-math-on-kalshi)

### News & Industry Analysis
- [Polymarket US Sets 0.01% Taker Fee](https://phemex.com/news/article/polymarket-us-introduces-001-taker-fee-on-contracts-32524)
- [How Polymarket Makes Money](https://ideausher.com/blog/how-polymarket-makes-money/)
- [Polymarket Ultimate Guide 2025](https://alphatechfinance.com/tech/polymarket-ultimate-guide-2025/)
- [Kalshi Review 2025 (Fortunly)](https://fortunly.com/reviews/kalshi-review/)
- [Ethereum vs Polygon Transaction Costs](https://homecubes.io/eth-network-transaction-cost-comparing-to-polygon-matic-network/)

---

## Appendix A: Fee Formula Quick Reference

### Polymarket US
```
Taker Fee = (Contracts × Price) × 0.0001
Maker Fee = 0
Gas Fee ≈ $0.01 per transaction
```

### Polymarket International
```
All Trading Fees = 0
Gas Fee ≈ $0.01 per transaction
Relayer Fee = max($3 + gas, 0.3% of withdrawal)
```

### Kalshi (General Markets)
```
Taker Fee = ceil(0.07 × C × P × (1-P))
Maker Fee = 0
```

### Kalshi (Sports Markets)
```
Taker Fee = ceil(0.07 × C × P × (1-P))
Maker Fee = ceil(0.0175 × C × P × (1-P))
```

### Kalshi (Index Markets: S&P 500, NASDAQ-100)
```
Taker Fee = ceil(0.035 × C × P × (1-P))
```

Where:
- C = Number of contracts
- P = Price in dollars (0.0-1.0)
- ceil() = Round up to next cent

---

## Appendix B: Arbitrage Profitability Calculator

### Python Implementation
```python
def is_arbitrage_profitable(poly_price: float, kalshi_price: float,
                            contracts: int = 1000,
                            poly_platform: str = "us") -> dict:
    """
    Quick profitability check for arbitrage opportunity

    Example usage:
        result = is_arbitrage_profitable(poly_price=0.45, kalshi_price=0.58)
        print(f"Net Profit: ${result['net_profit']:.2f}")
    """
    # Strategy: Buy Poly DOWN + Kalshi YES (when Poly > Kalshi)
    # or Buy Poly UP + Kalshi NO (when Poly < Kalshi)

    poly_cost = contracts * poly_price
    kalshi_cost = contracts * kalshi_price
    gross_cost = poly_cost + kalshi_cost

    # Fees
    poly_fee = 0 if poly_platform == "international" else poly_cost * 0.0001
    kalshi_fee = math.ceil(0.07 * contracts * kalshi_price * (1 - kalshi_price) * 100) / 100
    gas = 0.01

    total_fees = poly_fee + kalshi_fee + gas
    net_cost = gross_cost + total_fees

    # Payout is $1 per contract = $1,000 for 1,000 contracts
    payout = contracts * 1.0
    net_profit = payout - net_cost
    net_margin_pct = (net_profit / payout) * 100

    return {
        "gross_cost": gross_cost,
        "total_fees": total_fees,
        "net_cost": net_cost,
        "payout": payout,
        "net_profit": net_profit,
        "net_margin_pct": net_margin_pct,
        "is_profitable": net_profit > 0,
        "roi": (net_profit / net_cost) * 100 if net_cost > 0 else 0
    }
```

---

**Document Version:** 1.0
**Last Updated:** December 10, 2025
**Maintained By:** Research Team
**Next Review:** When fee structures change (monitor official announcements)
